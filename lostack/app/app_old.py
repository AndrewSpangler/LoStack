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
from flask import Flask, abort, g, request, Response
from flask_login import current_user, login_user
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from modules.browser import init_filebrowser
from modules.helpers import (
    await_db,
    get_system_info,
)
from .modules.common.label_extractor import LabelExtractor as labext
from .modules.themes import BOOTSWATCH_THEMES, CODEMIRROR_THEMES



def create_app(*args, **kw) -> Flask:
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    
    from modules.package_manager import init_docker_handler
    # Initialize Docker event handler
    docker_handler = init_docker_handler(app)
    app.docker_handler = docker_handler
    logging.info("Docker event handler initialized")

    atexit.register(docker_handler.stop)


    @app.route('/health')
    def health() -> Response:
        try:
            return Response("OK", status=200)
        except Exception as e:
            logger.error(f"ERROR: Error in health endpoint: {str(e)}", exc_info=True)
            return Response("Internal Server Error", status=500)

    return app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)