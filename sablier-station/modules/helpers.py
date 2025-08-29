import logging
import platform
import sys
import time
from flask import (
    request,
    __version__ as flask_version
)
from flask_login import current_user
from fnmatch import fnmatch
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError


def get_system_info() -> dict:
    """Collect system / version info"""
    logging.info("Collecting runtime details...")
    return {
        "OS": (platform.system(), platform.release(), platform.version()),
        "Python Version": sys.version,
        "Flask Version": flask_version,
    }


def get_proxy_user_meta(current_user) -> dict:
    """Read proxy-auth metadata from headers"""
    if not current_user.is_authenticated:
        logging.warning("Unauthenticated user")
        return abort(403)
    groups = request.headers.get("Remote-Groups", "")
    if len(groups):
        groups = groups.split(",")
    if len(groups) == 1 and groups[0] == "":
        groups = []
    meta = {
        "user": request.headers.get("Remote-User", ""),
        "groups": groups
    }
    return meta


def wait_for_db(uri, timeout=60, interval=0.5) -> None:
    """Wait for db to become available"""
    engine = create_engine(uri)
    start_time = time.time()
    
    while True:
        try:
            conn = engine.connect()
            conn.close()
            logging.info("Database is ready.")
            return
        except OperationalError:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Database not available after {timeout} seconds.")
            logging.warning(f"Database not ready yet, waiting {interval}s...")
            time.sleep(interval)


def is_trusted_ip(remote_addr: str, trusted_ips: str) -> bool:
    """Checks to see if the host router / proxy is trusted"""
    for ip in trusted_ips.split(","):
        if fnmatch(remote_addr, ip):
            return True
    return False