import os
import subprocess
import threading
from ..runners.base import RunBase

def _run_docker(cmd, services, result_queue, complete=True):
    if isinstance(services, str):
        services = [services]
    return RunBase([*cmd, *services], result_queue, complete=complete).run()

def docker_start(services, result_queue, complete=True):
    result_queue.put_nowait(f"Running docker start on services: {services}")
    return _run_docker(["docker", "container", "start"], services, result_queue, complete)

def docker_stop(services, result_queue, complete=True):
    result_queue.put_nowait(f"Running docker stop on services: {services}")
    return _run_docker(["docker", "container", "stop"], services, result_queue, complete)

def docker_down(services, result_queue, complete=True):
    result_queue.put_nowait(f"Running docker down on services: {services}")
    return _run_docker(["docker", "container", "down"], services, result_queue, complete)

def docker_remove(services, result_queue, complete=True):
    result_queue.put_nowait(f"Running docker remove on services: {services}")
    docker_stop(services, result_queue, False)
    return _run_docker(["docker", "container", "remove"], services, result_queue, complete)

def docker_compose_up(services, result_queue, complete=True):
    result_queue.put_nowait(f"Running docker compose up on services: {services}")
    return _run_docker(["docker", "compose", "-f", "/docker/docker-compose.yml", "up", "-d"], services, result_queue, complete)

def docker_compose_stop(services, result_queue, complete=True):
    result_queue.put_nowait(f"Running docker compose stop on services: {services}")
    return _run_docker(["docker", "compose", "-f", "/docker/docker-compose.yml", "stop"], services, result_queue, complete)

def docker_compose_down(services, result_queue, complete=True):
    result_queue.put_nowait(f"Running docker composed down on services: {services}")
    return _run_docker(["docker", "compose", "-f", "/docker/docker-compose.yml", "down"], services, result_queue, complete)

class DockerActor:
    """For multi-step Docker processes"""
    def __init__(self, compose_file:os.PathLike, result_queue):
        self.compose_file = compose_file
        self.queue = result_queue

    def docker_start(self, services:list[str]):
        return docker_start(services, self.queue, complete=False)

    def docker_stop(self, services:list[str]):
        return docker_stop(services, self.queue, complete=False)
    
    def docker_down(self, services:list[str]):
        return docker_down(services, self.queue, complete=False)

    def docker_remove(self, services:list[str]):
        return docker_remove(services, self.queue, complete=False)

    def docker_compose_up(self, services:list[str]):
        return docker_compose_up(services, self.queue, complete=False)

    def docker_compose_stop(self, services:list[str]):
        return docker_compose_stop(services, self.queue, complete=False)

    def docker_compose_down(self, services:list[str]):
        return docker_compose_down(services, self.queue, complete=False)

    def complete_queue(self):
        self.queue.put_nowait("__COMPLETE__")
