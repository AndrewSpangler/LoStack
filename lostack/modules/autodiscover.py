import docker
import logging
import threading
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Set, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .models import SablierService, SablierDefaults, db
from flask import current_app as app # Import after models
from .docker.helpers import (
    normalize_docker_labels,
    get_compose_services,
    get_service_details,
    get_sablier_groups_from_containers,
    get_traefik_port_from_labels,
    get_traefik_router_from_labels,
    get_friendly_name_from_labels,
    get_primary_sablier_services,
    parse_boolean_label
)

docker_handler = None

class ComposeFileWatcher(FileSystemEventHandler):
    """Watches docker-compose.yml for changes"""
    
    def __init__(self, docker_handler, compose_file_path: str):
        self.docker_handler = docker_handler
        self.compose_file_path = Path(compose_file_path).resolve()
        self.logger = logging.getLogger(__name__ + '.ComposeWatcher')
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).resolve() == self.compose_file_path:
            self.logger.info(f"Compose file modified: {event.src_path}")
            try:
                # self.logger.info(f"Updating depot services.")
                self.docker_handler._update_depot_services()
            except Exception as e:
                self.logger.info(f"Error updating depot services {e}")
            self.logger.info(f"Done updating compose services")

class DockerSablierHandler:
    """
    Handles Docker events and automatically updates Sablier configuration
    based on container labels. Also watches docker-compose.yml for primary services.
    """
    
    def __init__(self, app, compose_file_path: str = "/docker/docker-compose.yml"):
        self.app_context = app.app_context
        self.compose_file_path = Path(compose_file_path).resolve()
        self.running = False
        self.logger = logging.getLogger(__name__)
        self._depot_services = []
        
        self.docker_client = docker.from_env()
        self.docker_client.ping()
        self.logger.info("Docker client initialized")

        # Initialize compose watcher
        self.file_watcher = ComposeFileWatcher(self, self.compose_file_path)
        self.file_observer = Observer()
        watch_dir = self.compose_file_path.parent
        self.file_observer.schedule(self.file_watcher, str(watch_dir), recursive=False)
         
        # Load initial primary services
        self._update_depot_services()

        # Start Docker event monitoring thread
        self.event_thread = threading.Thread(
            target=self._monitor_events, 
            daemon=True,
            name="DockerEventHandler"
        )
        self.event_thread.start()
        
        self.file_observer.start()
        self.logger.info("File watcher started")
        threading.Thread(
            target=self._background_sync,
            daemon=True,
            name="InitialSync"
        ).start()
        self.logger.info("Docker handler initialization completed")
    
    def _update_depot_services(self):
        self.logger.info("Updating depot services...")
        new_depot_services = self.get_primary_sablier_services()
        old_services = set(self._depot_services)
        new_services = set(new_depot_services)
        if old_services != new_services:
            self._depot_services = new_depot_services
            added = new_services - old_services
            removed = old_services - new_services
            self.logger.info(f"Primary services updated. Added: {added}, Removed: {removed}")
        else:
            self.logger.debug("Primary services list unchanged")

    def get_primary_sablier_services(self, file=None):
        return get_primary_sablier_services(file or str(self.compose_file_path))
        
    def get_depot_services(self) -> List[str]:
        return self._depot_services.copy()
        
    def get_service_details(self, service_names: list) -> dict:
        return get_service_details(self.compose_file_path, service_names)


    def stop(self):
        self.running = False
        if self.event_thread and self.event_thread.is_alive():
            self.event_thread.join(timeout=5)
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join(timeout=5)
            self.logger.info("File watcher stopped")
        self.logger.info("Docker event handler stopped")
    
    def _monitor_events(self):
        while self.running:
            try:
                events = self.docker_client.events(filters={'type': 'container'}, decode=True)
                for event in events:
                    if not self.running:
                        break
                    action = event.get('Action')
                    if action in ['start', 'stop', 'destroy', 'create']:
                        container_id = event.get('id')
                        self.logger.debug(f"Container {action}: {container_id[:12]}")
                        self._handle_container_event(container_id, action)
            except Exception as e:
                self.logger.error(f"Error monitoring Docker events: {e}")
                if self.running:
                    time.sleep(5)
    
    def _handle_container_event(self, container_id: str, action: str):
        try:
            time.sleep(0.5)
            self._update_depot_services()
        except Exception as e:
            self.logger.error(f"Error handling container event {action} for {container_id[:12]}: {e}")

    def _background_sync(self):
        while True:
            self._sync_all_containers()
            time.sleep(10)
    
    def _sync_all_containers(self):
        """Synchronize all containers with Sablier configuration"""        
        try:
            with self.app_context():
                # Get all containers with Sablier labels
                sablier_groups = self._get_sablier_groups()
                existing_services = {s.name: s for s in SablierService.query.all() if s.automatic}
                
                # Track which services should exist
                should_exist = set()
                
                # Create or update services based on Docker containers
                for group_name, group_data in sablier_groups.items():
                    should_exist.add(group_name)
                    
                    if group_name in existing_services:
                        # Update existing service
                        service = existing_services[group_name]
                        self._update_service_from_labels(service, group_data)
                    else:
                        # Create new service
                        service = self._create_service_from_labels(group_name, group_data)
                        existing_services[group_name] = service
                
                # Disable services that no longer have containers
                for service_name, service in existing_services.items():
                    if service_name not in should_exist and service.enabled:
                        service.enabled = False
                        self.logger.info(f"Disabled service: {service_name} (no containers found)")
                
                db.session.commit()
                
                # Update the Traefik configuration file
                from modules.models import save_sablier_config_to_file
                if save_sablier_config_to_file():
                    self.logger.info("Traefik configuration updated successfully")
                    pass
                else:
                    self.logger.error("Failed to update Traefik configuration file")
                    
        except Exception as e:
            self.logger.error(f"Error syncing containers: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass  # Ignore rollback errors
                
    def _get_sablier_groups(self) -> Dict[str, Dict]:
        """
        Get all containers grouped by sablier.group label
        Returns dict with group_name as key and group data as value
        """
        groups = {}
        try:
            containers = self.docker_client.containers.list(all=True)
            groups = get_sablier_groups_from_containers(containers)
        except Exception as e:
            self.logger.error(f"Error getting Sablier groups: {e}")
        return groups
        
    def _create_service_from_labels(self, group_name: str, group_data: Dict) -> SablierService:
        """Create a new SablierService from container labels"""
        labels = group_data['labels']
        main_container = group_data['main_container']
        
        # Extract configuration from labels
        port = get_traefik_port_from_labels(labels)
        display_name = get_friendly_name_from_labels(labels, group_name)
        session_duration = labels.get('lostack.duration', None)
        theme = labels.get('lostack.theme', None)
        refresh_frequency = labels.get('lostack.refresh', None)
        show_details = parse_boolean_label(labels.get('lostack.details', 'true'))
        
        # Get defaults for any missing values
        defaults = SablierDefaults.get_defaults()
        
        service = SablierService(
            name=group_name,
            names=','.join(group_data['names']),
            display_name=display_name,
            port=port,
            session_duration=session_duration or defaults.session_duration,
            theme=theme or defaults.theme,
            refresh_frequency=refresh_frequency or defaults.refresh_frequency,
            show_details=show_details,
            enabled=True,
            automatic=True
        )
        
        db.session.add(service)
        self.logger.info(f"Created new service: {group_name}")
        return service
    
    def _update_service_from_labels(self, service: SablierService, group_data: Dict):
        """Update existing SablierService from container labels"""
        labels = group_data['labels']
        
        # Update basic info
        service.names = ','.join(group_data['names'])
        service.enabled = True
        
        # Update configuration from labels
        new_port = get_traefik_port_from_labels(labels)
        if new_port != service.port:
            service.port = new_port
        
        new_display_name = get_friendly_name_from_labels(labels, service.name)
        if new_display_name != service.display_name:
            service.display_name = new_display_name
        
        # Update Sablier-specific settings if provided
        if 'lostack.duration' in labels:
            service.session_duration = labels['lostack.duration']
        
        if 'lostack.theme' in labels:
            service.theme = labels['lostack.theme']
        
        if 'lostack.refresh' in labels:
            service.refresh_frequency = labels['lostack.refresh']
        
        if 'lostack.details' in labels:
            service.show_details = parse_boolean_label(labels['lostack.details'])
        
        self.logger.debug(f"Updated service: {service.name}")
        
    def _cleanup_destroyed_container(self, container_id: str):
        """Clean up services when containers are destroyed"""
        self._sync_all_containers()
    
    def force_sync(self):
        self.logger.info("Forcing full container synchronization")
        self._update_depot_services()

def init_docker_handler(app):
    global docker_handler
    docker_handler = DockerSablierHandler(app)
    return docker_handler