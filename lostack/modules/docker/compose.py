"""This module handles editing a compose file, not actually handling compose up / down"""

from .helpers import load_compose, write_compose


def add_service(compose_data: dict, service_data: dict) -> None:
    if "services" not in compose_data:
        compose_data["services"] = {}

    existing = set(compose_data["services"].keys())
    incoming = set(service_data["services"].keys())
    conflict = existing.intersection(incoming)

    if conflict:
        raise KeyError(f"Service(s) already exist in compose: {', '.join(conflict)}")

    for name, config in service_data["services"].items():
        compose_data["services"][name] = config


def get_service_data(compose_data: dict, service: str) -> dict:
    return compose_data.get("services", {}).get(service, {})


def get_services_data(compose_data: dict, service_names: list[str]) -> dict:
    services = compose_data.get("services", {})
    return {name: services[name] for name in service_names if name in services}


def get_service_group_data(compose_data: dict, group: str) -> dict:
    result = {}
    for name, config in compose_data.get("services", {}).items():
        labels = config.get("labels", [])
        for label in labels:
            if label.startswith("sablier.group="):
                _, value = label.split("=", 1)
                if value.strip() == group:
                    result[name] = config
    return result


def update_service(compose_data: dict, service_data: dict) -> None:
    services = compose_data.setdefault("services", {})
    for name, config in service_data.items():
        if name not in services:
            raise KeyError(f"Service '{name}' not found in compose data")
        services[name].update(config)
