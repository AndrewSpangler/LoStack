import os
from flask import Response, current_app as app, g, stream_with_context
from functools import wraps
from .stream_generator import stream_generator
from .docker.actions import (
    docker_start,
    docker_stop,
    docker_down,
    docker_remove,
    docker_compose_up,
    docker_compose_down,
    docker_compose_stop
)
from .depot.actions import depot_package_install
from .git import RepoManager

def _generate(action, target):
    # Generic streaming object for backend tasks that need websocket streaming to UI
    # Handles streaming by talking an action and supplying a target
    # The backend action should be able to act on one or many service / service
    # Or for sablier, one or many group / groups
    stream = stream_generator(action, (target, ))
    def generator():
        for message in stream(): yield message
        from .autodiscover import docker_handler
        docker_handler.force_sync()
    return Response(
        generator(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )

def stream_docker_start(services:str|list[str]) -> Response:
    return _generate(docker_start, services)
 
def stream_docker_stop(services:str|list[str]) -> Response:
    return _generate(docker_stop, services)

def stream_docker_down(services:str|list[str]) -> Response:
    return _generate(docker_down, services)

def stream_docker_remove(services:str|list[str]) -> Response:
    return _generate(docker_remove, services)

def stream_docker_compose_up(services:str|list[str]) -> Response:
    return _generate(docker_compose_up, services)
 
def stream_docker_compose_down(services:str|list[str]) -> Response:
    return _generate(docker_compose_down, services)
  
def stream_docker_compose_stop(services:str|list[str]) -> Response:
    return _generate(docker_compose_stop, services)

def stream_depot_package_install(package_compose_path:os.PathLike) -> Response:
    return _generate(depot_package_install, package_compose_path)

def stream_depot_update() -> Response:
    url = g.store_url
    if app.config.get("DEPO_DEV_MODE"):
        return "__COMPLETE__"
        raise
    
    depot_dir = app.config.get("DEPOT_DIR")
    def _update_store(result_queue=None):
        RepoManager(
            depot_dir,
            repo_url=url,
            branch="main",
            result_queue=result_queue
        ).ensure_repo()
    stream = stream_generator(_update_store, [])
    def _generator():
        for message in stream(): yield message
        
    return Response(
        _generator(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )