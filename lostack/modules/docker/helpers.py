import os
import yaml
from pathlib import Path
from typing import List, Dict
from ..helpers import load_yaml

def load_compose(compose_file_path: os.PathLike) -> dict:
    return load_yaml(Path(compose_file_path))


def write_compose(compose_file_path: os.PathLike, compose_data:dict) -> None:
    yaml_content = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)
    with open(compose_file_path, 'w') as f:
        f.write(yaml_content)
    return 

def get_compose_services(compose_file_path: os.PathLike) -> dict:
    return load_yaml(Path(compose_file_path), ["services"])['services']

def save_sablier_config_to_file(filename="/dynamic.yml") -> bool:
    """
    Export LoStack configuration and save to file
    Returns True if successful, False otherwise
    """
    try:
        yaml_content = export_sablier_config_to_yaml()
        with open(filename, 'w') as f:
            f.write(yaml_content)
        return True
    except Exception as e:
        print(f"Error saving config to {filename}: {e}")
        return False


def get_primary_sablier_services(compose_file_path: os.PathLike) -> List[str]:
    services = get_compose_services(compose_file_path)
    primary_services = []
    for serv_name, serv in services.items():
        if not isinstance(serv, dict):
            continue
        labels = normalize_docker_labels(serv.get('labels', []))
        if labels.get("lostack.primary", "").lower() == "true":
            primary_services.append(serv_name)
    return primary_services


def normalize_docker_labels(labels:List[str]|Dict[str, str]) -> dict:
    """
    Normalize labels to dict format before using other helpers
    """
    if isinstance(labels, list):
        normalized = {}
        for label in labels:
            if isinstance(label, str) and '=' in label:
                key, value = label.split('=', 1)
                normalized[key.strip()] = value.strip()
        return normalized
    elif isinstance(labels, dict):
        return {k: str(v) for k, v in labels.items()}
    return {}

def get_traefik_router_from_labels(labels:Dict[str, str]) -> str|None:
    """
    Gets the traefik router rule from labels if one exists
    """
    for key in labels:
        if key.startswith('traefik.http.routers.') and key.endswith('.rule'):
            return labels[key]

def get_traefik_port_from_labels(labels:Dict[str, str], default:int = None) -> str|None:
    """
    Gets the traefik port server rule from labels if one exists
    """
    for key in labels:
        if key.endswith('.loadbalancer.server.port'):
            return labels[key]
    return str(default)

def get_friendly_name_from_labels(labels:Dict[str, str], fallback:str = None) -> str|None:
    """
    Try to find a friendly name from labels
    """
    return (
        labels.get('homepage.name')
        or labels.get('lostack.name')
        or fallback.title()
    )


def _assert_content(val:str) -> None:
    """
    Makes sure a label is valid
    """
    if val is None:
        raise ValueError("Val is empty")
    if not isinstance(val, str):
        raise TypeError(f"Expected string type, got {type(val)}")
    if not len(val):
        return ValueError("Empty String")

def parse_boolean_label(val:str) -> bool:
    """
    Parse a Docker label value to Python bool
    """
    _assert_content(val)
    if val.lower() in ('true', "1", "yes", "on", "enable", "enabled"):
        return True
    if val.lower() in ('false', "0", "no", "off", "disable", "disabled"):
        return False
    raise ValueError(f"Could not parse value {val}")


def parse_int_label(val:str) -> int:
    """
    Parse a Docker label to an int
    """
    _assert_content(val)
    return int(val)


def get_sablier_groups_from_containers(containers:list) -> dict:
    groups = {}
    
    for container in containers:
        labels = container.labels or {}
        
        if not labels.get('sablier.enable', '').lower() == 'true':
            continue
        
        # Get group name (default to container name if no group specified)
        group_name = labels.get('sablier.group', container.name)
        
        if group_name not in groups:
            groups[group_name] = {
                'containers': [],
                'main_container': None,
                'labels': {},
                'names': []
            }
        
        # Add container to group
        groups[group_name]['containers'].append(container)
        groups[group_name]['names'].append(container.name)
        
        # Determine main container (one with Traefik router or first one)
        if labels.get('lostack.primary', "").lower() == "true":
            groups[group_name]['main_container'] = container
            groups[group_name]['labels'] = labels
                
    return groups


def get_service_details(compose_file_path, service_names:list, result:dict={}) -> dict:
    compose_services = get_compose_services(compose_file_path)       

    for primary_name in service_names:
        if primary_name not in compose_services:
            continue

        primary_config = compose_services[primary_name]
        primary_labels = normalize_docker_labels(primary_config.get('labels', {}))
        primary_group = primary_labels.get('sablier.group', primary_name)

        result[primary_name] = primary_config.copy()
        result[primary_name]['dependencies'] = {}

        for service_name, service_config in compose_services.items():
            if service_name == primary_name or service_name in service_names:
                continue
            service_labels = normalize_docker_labels(service_config.get('labels', {}))
            service_group = service_labels.get('sablier.group', service_name)

            if service_group == primary_group:
                result[primary_name]['dependencies'][service_name] = service_config.copy()

    return result