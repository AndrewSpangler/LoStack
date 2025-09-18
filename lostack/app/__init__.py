import logging
import logging.config
import os
from flask import Flask, Blueprint, current_app
from app.version import __version__

def _require_config(app, var_name):
    if (value := app.config.get(var_name)) is None:
        logging.error((msg := f"{var_name} environment variable cannot be empty"))
        raise ValueError(msg)
    return value

def setup_config(app: Flask) -> None:
    from app.environment import ENV_DEFAULTS, ENV_PARSING, ENV_NON_REQUIRED
    for k, v in ENV_DEFAULTS.items():
        val = os.environ.get(k, v)
        if (parser := ENV_PARSING.get(k)):
            val = parser(val)
        app.config.update({k:val})
        if k in ENV_NON_REQUIRED:
            continue
        _require_config(app, k)
    # Blueprint can populate this to add to context provider
    app.config["PROVIDED_CONTEXT"] = {}
    trusted_proxies_string = app.config.get("TRUSTED_PROXY_IPS", None)
    if not trusted_proxies_string:
        raise ValueError("TRUSTED_PROXY_IPS var cannot be empty")
    app.config["TRUSTED_PROXY_IPS"] = [i.strip() for i in trusted_proxies_string.split(",")]
    if app.config.get("DEPOT_DEV_MODE"):
        app.config["DEPOT_DIR"] = app.config.get("DEPOT_DIR_DEV")


def setup_logging(app: Flask) -> None:
    from app.extensions.common.label_extractor import LabelExtractor as labext
    logging.basicConfig(
        level=logging.DEBUG
        if labext.parse_boolean(app.config.get("DEBUG"))
        else logging.INFO
    )
    logging.config.dictConfig(app.config["LOG_CONFIG"])

def setup_user_login(app: Flask) -> None:
    def user_loader(user_id:int|str) -> "User":
        """User Loader for Flask-Login"""
        return current_app.models.User.query.get(int(user_id))

    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id):
        return user_loader(user_id)


def setup_context_provider(app: Flask) -> None:
    from flask_login import current_user
    @app.context_processor
    def provide_selection() -> dict[str:any]:
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
            "themes": app.config.get("BOOTSWATCH_THEMES"),
            "editor_themes": app.config.get("CODEMIRROR_THEMES"),
            "selected_theme": selected_theme,
            "selected_editor_theme" : selected_editor_theme,
            "depot_url" : app.config["DEPOT_URL"],
            **app.config.get("PROVIDED_CONTEXT")
        }


def create_app(*args, **kw) -> Flask:
    app = Flask(
        __name__,
        *args,
        static_folder='static', 
        static_url_path='/static',
        **kw
    )

    setup_config(app)
    setup_logging(app)

    if app.config.get("DEBUG"):
        # Early diagnostics spew
        import json, sys, platform
        from flask import flask_version
        logging.info(
            "SYSTEM INFO:\n"
            +json.dumps(
                {
                    "OS": (platform.system(), platform.release(), platform.version()),
                    "Python Version": sys.version,
                    "Flask Version": flask_version,
                },
                indent=2
            )
        )

    from app.extensions import setup_db
    app.db = setup_db(app)

    with app.app_context():
        from app.models import init_db
        init_db(app)

    from app.extensions.docker import DockerManagerStreaming
    app.docker_manager = DockerManagerStreaming(
        (
            "/docker/lostack-compose.yml",
            "/docker/docker-compose.yml"
        )
    )

    from app.extensions.service_manager import init_service_manager

    with app.app_context():
        app.docker_handler = init_service_manager(app)

        app.docker_manager.modified_callback = app.docker_handler.refresh

    setup_user_login(app)

    from app.permissions import setup_permissions
    setup_permissions(app)

    setup_context_provider(app)

    from app.blueprints import register_blueprints
    register_blueprints(app)
    
    return app


if __name__ == '__main__':
    create_app().run(debug=True)