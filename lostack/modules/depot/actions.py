import os
from flask import Response
from .depot import add_depot_package_to_compose
from ..docker.actions import _run_docker

def depot_package_install(package_compose_path: os.PathLike, result_queue, complete=True) -> Response:
    result_queue.put_nowait("Adding depot package to lostack compose file.")
    services = add_depot_package_to_compose("/docker/lostack-compose.yml", package_compose_path, result_queue)
    return _run_docker(
        [
            "docker",
            "compose",
            "-f",
            "/docker/lostack-compose.yml",
            "up",
            "-d"
        ],
        services,
        result_queue,
        complete
    )