"""
access.py - Andrew Spangler
Group-based endpoint access controller for LoStack
Compatible with Traefik+Authelia and possibly other auth systems
"""

import fnmatch
import json
import logging
import os
from flask import (
    Flask,
    Blueprint,
    request,
    Response,
    current_app as app
)
from functools import wraps

def get_proxy_user_meta(
    req, conf:dict
) -> dict:
    meta = {
        k : req.headers.get(v, "")
        for k,v in conf.items()
    }
    if "groups" in meta:
        groups = meta.get("groups")
        if len(groups):
            groups = groups.split(",")
        if len(groups) == 1 and groups[0] == "":
            groups = []
        meta["groups"] = groups
    return meta

def register_blueprint(app:Flask) -> Blueprint:
    bp = blueprint = Blueprint('auth', __name__, url_prefix="/auth")
    with app.app_context():
        ADMIN_GROUP = app.config.get("ADMIN_GROUP")
        GROUPS_HEADER = app.config.get("GROUPS_HEADER")
        TRUSTED_PROXY_IPS = app.config.get("TRUSTED_PROXY_IPS")
        USERNAME_HEADER = app.config.get("USERNAME_HEADER")
        FORWARDED_FOR_HEADER = app.config.get("FORWARDED_FOR_HEADER")
        FORWARDED_HOST_HEADER = app.config.get("FORWARDED_HOST_HEADER")
        FORWARDED_METHOD_HEADER = app.config.get("FORWARDED_METHOD_HEADER")
        FORWARDED_URI_HEADER = app.config.get("FORWARDED_URI_HEADER")
        DOMAIN_NAME = app.config.get("DOMAIN_NAME")

    logger = logging.getLogger(__name__ + f'.ACCESS')

    logger.info(f"""
\nStarting Auth blueprint with configuration
\tUsername header: {USERNAME_HEADER}
\tGroups header: {GROUPS_HEADER}
\tAdmin group: {ADMIN_GROUP}
\tTrusted proxies: {TRUSTED_PROXY_IPS}
\tForwarded FOR header: {FORWARDED_FOR_HEADER}
\tForwarded HOST header: {FORWARDED_HOST_HEADER}
\tForwarded METHOD header: {FORWARDED_METHOD_HEADER}
\tForwarded URI header: {FORWARDED_URI_HEADER}
\tDomain Name: {DOMAIN_NAME}
""")

    def check_access(f):
        """Decorator to check a user's access to an endpoint"""
        @wraps(f)
        def wrapped(*args, **kwargs) -> Response:
            try:
                remote_addr = request.environ.get('REMOTE_ADDR')
                meta = get_proxy_user_meta(
                    request,
                    {
                        "user" : USERNAME_HEADER,
                        "groups" : GROUPS_HEADER,
                        "forwarded_for" : FORWARDED_FOR_HEADER,
                        "forwarded_host" : FORWARDED_HOST_HEADER,
                        "forwarded_method" : FORWARDED_METHOD_HEADER,
                        "forwarded_uri" : FORWARDED_URI_HEADER
                    }
                )
                username = meta["user"]
                user_groups = meta["groups"]
                forwarded_for = meta["forwarded_for"]
                forwarded_host = meta["forwarded_host"]
                forwarded_method = meta["forwarded_method"]
                forwarded_uri = meta["forwarded_uri"]

                if app.config.get("debug"):
                    logger.debug(f"DEBUG: From {remote_addr} for {forwarded_for} "
                    f"with headers: {json.dumps(dict(request.headers), indent=2)}")        

                if not username:
                    logger.error(f"ERROR: Missing username header: {USERNAME_HEADER}")
                    return Response("Unauthorized", status=401)
                
                if not user_groups:
                    logger.error(f"ERROR: Missing groups header: {GROUPS_HEADER} for user: {username}")
                    return Response("Unauthorized", status=401)
                
                service_name = forwarded_host.split(".")[0]
                service = app.models.PackageEntry.query.filter_by(name=service_name).first()

                if not service:
                    logger.warning(f"WARNING: No service found for {service_name}")

                if ADMIN_GROUP in user_groups:
                    # Allow admins
                    return f(*args, **kwargs)

                if not service:
                    logger.warning(f"DENY (SERVICE NOT FOUND): {username}@{remote_addr}[{forwarded_for}] "
                        f"-> {forwarded_method}@{forwarded_host}{forwarded_uri}")
                    return Response("Forbidden", status=403)
                else:
                    allowed_groups = service.allowed_groups

                if not any((g in allowed_groups for g in user_groups)):
                    if not ADMIN_GROUP in user_groups:
                        logger.warning(f"DENY: {username}@{remote_addr}[{forwarded_for}] "
                            f"-> {forwarded_method}@{forwarded_host}{forwarded_uri}")
                        return Response("Forbidden", status=403)
                
                logger.info(f"ALLOW: {username}@{remote_addr} [{forwarded_for}] "
                    f"-> {forwarded_method} {forwarded_host}{forwarded_uri}")
                
                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"ERROR: Error in access check: {str(e)}", exc_info=True)
                return Response("Internal Server Error", status=500)
        
        return wrapped

    @bp.route('/', methods=['GET','POST','PUT','DELETE','PATCH','OPTIONS'])
    @app.permission_required(app.models.PERMISSION_ENUM.EVERYBODY)# Everyone can access check_access 
    @check_access # check_access limits by proxy group
    def auth() -> Response:
        try:
            username = request.headers.get(USERNAME_HEADER)
            # Return with added headers
            return Response("OK", status=200, headers={"X-Auth-User": username})
        except Exception as e:
            logger.error(f"ERROR: Error in auth endpoint: {str(e)}", exc_info=True)
            return Response("Internal Server Error", status=500)

    app.register_blueprint(bp)
    return bp