# import os
# import subprocess
# import threading
# import time
# from flask import Response
# from .common.runner import RunBase
# from .package_manager import get_docker_handler


# class DockerActionBase:
#     def __init__(self, base_cmd):
#         self.base_cmd = base_cmd
#     def execute(self, services:str|list[str], result_queue, complete=True):
#         if isinstance(services, str):
#             services = [services]
#         result_queue.put_nowait(f"Running {' '.join(self.base_cmd)} on services: {services}")
#         return RunBase([*self.base_cmd, *services], result_queue, complete=complete).run()

# docker_actions = {
#     'start': DockerActionBase(["docker", "container", "start"]),
#     'stop': DockerActionBase(["docker", "container", "stop"]),
#     'remove': DockerActionBase(["docker", "container", "remove"]),
#     'logs': DockerActionBase(["docker", "container", "logs"]),
#     'follow': DockerActionBase(["docker", "container", "logs", "--follow", "--tail", "--150"]),
# }

# def docker_start(services, result_queue, complete=True):
#     return docker_actions['start'].execute(services, result_queue, complete)

# def docker_stop(services, result_queue, complete=True):
#     return docker_actions['stop'].execute(services, result_queue, complete)

# def docker_down(services, result_queue, complete=True):
#     return docker_actions['compose_down'].execute(services, result_queue, complete)

# def docker_remove(services, result_queue, complete=True):
#     docker_stop(services, result_queue, False)  # Stop before removing
#     return docker_actions['remove'].execute(services, result_queue, complete)

# def docker_logs(services, result_queue, complete=True):
#     return docker_actions['logs'].execute(services, result_queue, complete)

# def docker_follow(services, result_queue, complete=True):
#     return docker_actions['follow'].execute(services, result_queue, complete)

# def docker_compose_up(services, result_queue, compose_file="/docker/docker-compose.yml", complete=True):
#     return DockerActionBase(
#         ["docker", "compose", "-f", compose_file, "up", "-d"]
#     ).execute(services, result_queue, complete)

# def docker_compose_stop(services, result_queue, compose_file="/docker/docker-compose.yml", complete=True):
#     return DockerActionBase(
#         ["docker", "compose", "-f", compose_file, "stop"]
#     ).execute(services, result_queue, complete)

# def docker_compose_down(services, result_queue, compose_file="/docker/docker-compose.yml", complete=True):
#     return DockerActionBase(
#         ["docker", "compose", "-f", compose_file, "down"]
#     ).execute(services, result_queue, complete)


    
