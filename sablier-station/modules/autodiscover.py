import docker
import logging
import threading
import time
from typing import Dict, List, Set, Optional

from .models import SablierService, SablierDefaults, db
from flask import current_app as app # Import after models

class DockerSablierHandler:
    """
    Handles Docker events and automatically updates Sablier configuration
    based on container labels
    """
    
    def __init__(self, app_context=None):
        self.app_context = app_context
        self.docker_client = None
        self.event_thread = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        self._init_docker_client()
    
    def _init_docker_client(self):
        """Initialize Docker client with error handling"""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            self.logger.info("Docker client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
    
    def start(self):
        """Start the Docker event monitoring thread"""
        if not self.docker_client:
            self.logger.error("Cannot start: Docker client not initialized")
            return False
        
        if self.running:
            self.logger.warning("Docker event handler already running")
            return True
        
        self.running = True
        self.event_thread = threading.Thread(
            target=self._monitor_events, 
            daemon=True,
            name="DockerEventHandler"
        )
        self.event_thread.start()
        self.logger.info("Docker event handler started")
        
        # Perform initial sync
        self._sync_all_containers()
        return True
    
    def stop(self):
        """Stop the Docker event monitoring"""
        self.running = False
        if self.event_thread and self.event_thread.is_alive():
            self.event_thread.join(timeout=5)
        self.logger.info("Docker event handler stopped")
    
    def _monitor_events(self):
        """Monitor Docker events for container changes"""
        while self.running:
            try:
                events = self.docker_client.events(
                    filters={'type': 'container'},
                    decode=True
                )
                
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
                    time.sleep(5)  # Brief pause before retrying
    
    def _handle_container_event(self, container_id: str, action: str):
        """Handle individual container events"""
        try:
            # Small delay to ensure container state is stable
            time.sleep(0.5)
            
            if action == 'destroy':
                # For destroyed containers, we need to clean up based on ID
                self._cleanup_destroyed_container(container_id)
            else:
                # For other actions, sync all containers to ensure consistency
                self._sync_all_containers()
                
        except Exception as e:
            self.logger.error(f"Error handling container event {action} for {container_id[:12]}: {e}")
    
    def _sync_all_containers(self):
        """Synchronize all containers with Sablier configuration"""
        if not self.app_context:
            self.logger.error("No app context available for database operations")
            return
        
        with self.app_context():
            try:
                # Get all containers with Sablier labels
                sablier_groups = self._get_sablier_groups()
                
                # Get existing services from database
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
                else:
                    self.logger.error("Failed to update Traefik configuration file")
                    
            except Exception as e:
                self.logger.error(f"Error syncing containers: {e}")
                db.session.rollback()
    
    def _get_sablier_groups(self) -> Dict[str, Dict]:
        """
        Get all containers grouped by sablier.group label
        Returns dict with group_name as key and group data as value
        """
        groups = {}
        
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                labels = container.labels or {}
                
                # Skip containers without Sablier enabled
                if not self._is_sablier_enabled(labels):
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
                if self._has_traefik_router(labels) and not groups[group_name]['main_container']:
                    groups[group_name]['main_container'] = container
                    groups[group_name]['labels'] = labels
                
                # If no main container set yet, use first container
                if not groups[group_name]['main_container']:
                    groups[group_name]['main_container'] = container
                    groups[group_name]['labels'] = labels
        
        except Exception as e:
            self.logger.error(f"Error getting Sablier groups: {e}")
        
        return groups
    
    def _is_sablier_enabled(self, labels: Dict[str, str]) -> bool:
        """Check if container has Sablier enabled"""
        return labels.get('sablier.enable', '').lower() == 'true'
    
    def _has_traefik_router(self, labels: Dict[str, str]) -> bool:
        """Check if container has Traefik router configuration"""
        for key in labels:
            if key.startswith('traefik.http.routers.') and key.endswith('.rule'):
                return True
        return False
    
    def _create_service_from_labels(self, group_name: str, group_data: Dict) -> SablierService:
        """Create a new SablierService from container labels"""
        labels = group_data['labels']
        main_container = group_data['main_container']
        
        # Extract configuration from labels
        port = self._extract_port_from_labels(labels)
        display_name = self._extract_display_name(labels, group_name)
        session_duration = labels.get('sablier-station.duration', None)
        theme = labels.get('sablier-station.theme', None)
        refresh_frequency = labels.get('sablier-station.refresh', None)
        show_details = self._parse_boolean(labels.get('sablier-station.details', 'true'))
        
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
        new_port = self._extract_port_from_labels(labels)
        if new_port != service.port:
            service.port = new_port
        
        new_display_name = self._extract_display_name(labels, service.name)
        if new_display_name != service.display_name:
            service.display_name = new_display_name
        
        # Update Sablier-specific settings if provided
        if 'sablier-station.duration' in labels:
            service.session_duration = labels['sablier-station.duration']
        
        if 'sablier-station.theme' in labels:
            service.theme = labels['sablier-station.theme']
        
        if 'sablier-station.refresh' in labels:
            service.refresh_frequency = labels['sablier-station.refresh']
        
        if 'sablier-station.details' in labels:
            service.show_details = self._parse_boolean(labels['sablier-station.details'])
        
        self.logger.debug(f"Updated service: {service.name}")
    
    def _extract_port_from_labels(self, labels: Dict[str, str]) -> str:
        """Extract port from Traefik labels or return default"""
        # Look for Traefik loadbalancer port
        for key, value in labels.items():
            if key.endswith('.loadbalancer.server.port'):
                return value
        return "80"
    
    def _extract_display_name(self, labels: Dict[str, str], fallback: str) -> Optional[str]:
        """Extract display name from labels"""
        # Try homepage name first, then sablier-station name, then fallback
        return (labels.get('homepage.name') or 
                labels.get('sablier-station.name') or 
                fallback.title())
    
    def _parse_boolean(self, value: str) -> bool:
        """Parse string boolean value"""
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _cleanup_destroyed_container(self, container_id: str):
        """Clean up services when containers are destroyed"""
        # Since we can't get labels from destroyed containers,
        # we'll do a full sync to handle cleanup
        self._sync_all_containers()
    
    def force_sync(self):
        """Force a full synchronization (useful for manual triggers)"""
        self.logger.info("Forcing full container synchronization")
        self._sync_all_containers()


# Global instance
docker_handler = None


def init_docker_handler(app):
    """Initialize the Docker handler with Flask app context"""
    global docker_handler
    
    if docker_handler is None:
        docker_handler = DockerSablierHandler(app.app_context)
        
        # Start monitoring if Docker is available
        if docker_handler.start():
            app.logger.info("Docker event handler initialized and started")
        else:
            app.logger.warning("Docker event handler failed to start")
    
    return docker_handler


def get_docker_handler():
    """Get the global Docker handler instance"""
    return docker_handler