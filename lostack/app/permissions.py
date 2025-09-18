import logging
from fnmatch import fnmatch
from flask import Flask, abort, g, request, Response
from flask_login import current_user, login_user
from functools import wraps

def is_trusted_ip(remote_addr: str, trusted_ips: list[str]) -> bool:
    """Checks to see if the host router / proxy is trusted"""
    for ip in trusted_ips:
        if fnmatch(remote_addr, ip):
            return True
    return False

def setup_permissions(app:Flask) -> None:
    # THIS FUNCTION HANDLES ACCESS TO THE APP ITSELF
    # FOR THE FORWARD-AUTH MIDDLEWARE SEE ./blueprints/access
    def permission_required(required_permission):
        """
        SSO / Authelia Integration
        This decorator function is used to limit access to Flask endpoints 
        based on users' groups as supplied by the reverse-proxy.
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
                permission = app.models.get_permission_from_groups(group_list)

                # Get or create user 
                user = app.models.User.query.filter_by(name=username).first()
                
                if user is None:
                    # Create new user
                    user = app.models.User(name=username, permission_integer=permission)
                    app.db.session.add(user)
                    app.db.session.commit()
                    logging.info("Created new user: %s with permission %s", username, permission)
                elif user.permission_integer != permission:
                    # Update existing user's permissions if changed
                    user.permission_integer = permission
                    app.db.session.commit()
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
                g.user = username
                g.groups = group_list
                g.permission = permission
                return func(*args, **kwargs)
                
            return wrapper
        return decorator

    # For use in blueprints etc
    app.permission_required = permission_required