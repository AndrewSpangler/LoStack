import os
import logging
import threading
import queue
from flask import Response, current_app, abort
from .actions import (
    depot_package_install,
    depot_package_remove,
    docker_start,
    docker_stop,
    docker_down,
    docker_remove,
    docker_logs,
    docker_follow,
    docker_compose_up,
    docker_compose_down,
    docker_compose_stop
)
from .common.stream_handler import StreamHandler
from .package_manager import get_docker_handler

def create_docker_stream(action):
    """Factory function to create docker streaming functions"""
    def stream_func(services):
        return StreamHandler.generic_stream(action, services)
    return stream_func

def create_docker_compose_stream(action):
    """Factory function to create docker streaming functions"""
    def stream_func(services, compose_file):
        return StreamHandler.generic_stream(action, services, compose_file=compose_file)
    return stream_func

# Docker control streams
stream_docker_start : Response = create_docker_stream(docker_start)
stream_docker_stop : Response = create_docker_stream(docker_stop)
stream_docker_down : Response = create_docker_stream(docker_down)
stream_docker_logs : Response = create_docker_stream(docker_logs)
stream_docker_follow : Response = create_docker_stream(docker_follow)
stream_docker_remove : Response = create_docker_stream(docker_remove)
stream_docker_compose_up : Response = create_docker_compose_stream(docker_compose_up)
stream_docker_compose_down : Response = create_docker_compose_stream(docker_compose_down)
stream_docker_compose_stop : Response = create_docker_compose_stream(docker_compose_stop)

def stream_depot_package_install(package_name: os.PathLike) -> Response:
    return StreamHandler.generic_stream(depot_package_install, package_name)

def stream_remove_package(package_db_id: int) -> Response:
    return StreamHandler.generic_stream(depot_package_remove, package_db_id)

def stream_depot_update() -> Response:    
    return get_docker_handler().depot_handler.stream_update_repo()