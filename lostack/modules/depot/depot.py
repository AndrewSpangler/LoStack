import os
from ..docker.helpers import write_compose, load_compose, get_primary_sablier_services
from ..docker.compose import add_service

def scan_depot(depot_path:os.PathLike) -> dict:
    packages = {}
    with os.scandir(os.path.join(os.path.abspath(depot_path), "packages")) as it:
        for entry in it:
            if os.path.isfile(entry.path):
                continue
            if os.path.isdir(entry.path):
                package_name = entry.name
                package_compose = os.path.join(os.path.abspath(entry.path), "docker-compose.yml")
                if os.path.isfile(package_compose):
                    packages[package_name] = load_compose(package_compose)
    return packages

def add_depot_package_to_compose(compose_file_path: os.PathLike, lostack_package_path: os.PathLike, result_queue) -> [str]:
    """Adds a depot package to the dynamic compose, returns the list of docker services added (so they can be upped)"""
    result_queue.put_nowait("Loading compose file")
    compose_data = load_compose(compose_file_path)
    result_queue.put_nowait("Compose file loaded")
    result_queue.put_nowait("Loading package file")
    service_data = load_compose(lostack_package_path)
    result_queue.put_nowait("Loaded package file")
    result_queue.put_nowait("Adding package to compose file")
    try:
        add_service(compose_data, service_data)
    except Exception as e:
        result_queue.put_nowait(f"Error adding service to dynamic compose - {e}")
        result_queue.put_nowait(f"Aborting...")
        raise e

    names = list(service_data.get("services", {}).keys())
    result_queue.put_nowait(f"Adding containers: {names}")
    result_queue.put_nowait("Added package to LoStack compose file")
    write_compose(compose_file_path, compose_data)
    result_queue.put_nowait("Wrote updated LoStack compose file")
    return names
# def remove_depot_package_from_compose(compose_file_path: os.PathLike, package_name: str) -> None: