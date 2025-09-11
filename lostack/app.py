print(disclaimer := """
Disclaimer: This software is provided "as is" and without warranties of 
any kind, whether express or implied, including, but not limited to, the 
implied warranties of merchantability, fitness for a particular purpose, 
and non-infringement. The use of this software is entirely at your own 
risk, and the owner, developer, or provider of this software shall not be
liable for any direct, indirect, incidental, special, or consequential 
damages arising from the use or inability to use this software or any of 
its functionalities. This software is not intended to be used in any 
life-saving, mission-critical, or other applications where failure of the
software could lead to death, personal injury, or severe physical or 
environmental damage. By using this software, you acknowledge that you 
have read this disclaimer and agree to its terms and conditions.
""".strip())

import atexit
import os
import sys
import json
import time
import logging
import logging.config
import yaml
from flask import Flask, abort, g, request
from flask_login import LoginManager, current_user, login_user
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from modules.browser import init_filebrowser
from modules.helpers import (
    get_system_info,
    get_proxy_user_meta,
    wait_for_db,
    is_trusted_ip
)
from modules.themes import BOOTSWATCH_THEMES, CODEMIRROR_THEMES

app = Flask(__name__, static_folder='static', static_url_path='/static')

ENV_DEFAULTS = {
    "APPLICATION_NAME" : "LoStack Admin",
    "APPLICATION_DESCRIPTION" : "Welcome to LoStack Station",
    "APPLICATION_DETAILS" : "Easily configure Traefik, GetHomePage, and Sablier and install prebuild services with a few clicks.",
    "DEPOT_URL" : "https://github.com/AndrewSpangler/LoStack-Depot.git",
    "DEPOT_BRANCH" : "main",
    "DEPOT_DIR" : "/appdata/LoStack-Depot",
    "DEPOT_DIR_DEV" : "/docker/LoStack-Depot",
    "DEPOT_DEV_MODE": False,
    "DOMAIN_NAME" : "lostack.internal",
    "SABLIER_URL" : "http://sablier:10000",
    "SABLIER_DEFAULT_SESSION_DURATION": "5m",
    "SABLIER_DEFAULT_THEME" : "ghost",
    "SABLIER_REFRESH_FREQUENCY": "3s",
    "TRUSTED_PROXY_IPS" : "192.168.*,10.0.0.*,172.*",
    "DB_HOST" : "",
    "DB_PORT" : "",
    "DB_USER" : "",
    "DB_PASSWORD" : "",
    "DB_NAME" : "",
    "LOG_CONFIG" : (
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s %(name)s %(threadName)s in %(module)s: %(message)s",
                }
            },
            "handlers": {
                "wsgi": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://flask.logging.wsgi_errors_stream",
                    "formatter": "default",
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["wsgi"]
            },
        }
    ),
    "SQLALCHEMY_POOL_SIZE" : 24,
    "SQLALCHEMY_MAX_OVERFLOW" : 5,
    "SQLALCHEMY_POOL_RECYCLE" : 3600,
    "SQLALCHEMY_TRACK_MODIFICATIONS" : False,
    "DEBUG" : False,
    "FOOTER_TEXT" : "Admin Panel",
    "TIMEZONE" : "US/Pacific"
}

for k, v in ENV_DEFAULTS.items():
    app.config.update({k:os.environ.get(k, v)})

if app.config.get("DEPOT_DEV_MODE"):
    app.config["DEPOT_DIR"] = app.config.get("DEPOT_DIR_DEV")

logging.basicConfig(level=logging.DEBUG)
logging.config.dictConfig(app.config["LOG_CONFIG"])
logging.info("SYSTEM INFO:\n"+json.dumps(get_system_info(), indent=2))

# Init database / Traefik config file handling
db_name = app.config.get("DB_NAME")
db_host = app.config.get("DB_HOST")
db_port = app.config.get("DB_PORT")
db_user = app.config.get("DB_USER")
db_pass = app.config.get("DB_PASSWORD")

# Wait for then connect to db
redacted_connection_string = f"mysql+pymysql://{db_user}:****@{db_host}:{db_port}/{db_name}"
logging.info("DB Config: " + redacted_connection_string)
connection_string = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
app.config["SQLALCHEMY_BINDS"] = {"lostack-db" : connection_string} 
wait_for_db(app.config["SQLALCHEMY_BINDS"]["lostack-db"])
app.db = db = SQLAlchemy(app)

# Set up db
with app.app_context():
    # DB Tables and Functions
    from modules.models import (
        User,
        get_permission_from_groups,
        user_loader,
        init_db
    )
    init_db(app)

# Set up logins (Auth handled by reverse-proxy)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    """Function for the login manager to grab user object from db"""
    return user_loader(user_id)


def permission_required(required_permission):
    """
    SSO / Authelia Integration
    This decorator function is used to limit access to Flask endpoints 
    based on users' groups as supplied by the reverse-proxy
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate proxy trust
            remote_addr = request.remote_addr
            logging.info("Request from: %s", remote_addr)
            
            if not is_trusted_ip(remote_addr, app.config["TRUSTED_PROXY_IPS"]):
                logging.warning("Untrusted proxy: %s", remote_addr)
                abort(403)

            # Extract user info from headers
            username = request.headers.get("Remote-User", "").strip()
            if not username:
                logging.warning("No Remote-User header provided")
                abort(403)
                
            groups = request.headers.get("Remote-Groups", "")
            group_list = [grp.strip() for grp in groups.split(",") if grp.strip()]
            permission = get_permission_from_groups(group_list)

            # Get or create user 
            user = User.query.filter_by(name=username).first()
            
            if user is None:
                # Create new user
                user = User(name=username, permission_integer=permission)
                db.session.add(user)
                db.session.commit()
                logging.info("Created new user: %s with permission %s", username, permission)
            elif user.permission_integer != permission:
                # Update existing user's permissions if changed
                user.permission_integer = permission
                db.session.commit()
                logging.info("Updated permission for user %s: %s", username, permission)

            # Ensure user is logged in
            if not current_user.is_authenticated:
                login_user(user)

            # Check permission level
            if permission < required_permission:
                logging.warning(
                    "[403] User '%s' (permission %s) attempted to access endpoint "
                    "requiring permission %s", 
                    username, permission, required_permission
                )
                abort(403)
            g.store_url = app.config["DEPOT_URL"]
            g.user = username
            g.groups = group_list
            g.permission = permission
            return func(*args, **kwargs)
            
        return wrapper
    return decorator

app.permission_required = permission_required


@app.context_processor
def provide_selection() -> dict:
    """
    Context processor which runs before any template is rendered
    Provides access to these values in all templates
    """
    selected_theme = "default"
    if hasattr(current_user, 'theme'):
        selected_theme = current_user.theme or "default"
    
    selected_editor_theme = "default"
    if hasattr(current_user, 'editor_theme'):
        selected_editor_theme = current_user.editor_theme or "default"

    return {
        "themes": BOOTSWATCH_THEMES,
        "editor_themes": CODEMIRROR_THEMES,
        "selected_theme": selected_theme,
        "selected_editor_theme" : selected_editor_theme,
    }

init_filebrowser(app)

from modules.package_manager import init_docker_handler

# Initialize Docker event handler
docker_handler = None
docker_handler = init_docker_handler(app)
app.docker_handler = docker_handler
logging.info("Docker event handler initialized")
# Load routes
with app.app_context():
    import modules.routes

atexit.register(docker_handler.stop)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)