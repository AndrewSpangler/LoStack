import docker
import logging
import os
from .common.label_extractor import LabelExtractor as labext
from .common.compose_file_manager import ComposeFileManager
from .common.depot_manager import DepotManager
from .models import PackageEntry, LoStackDefaults, save_sablier_config_to_file

# Global docker handler
# See init_docker_handler and get_docker_handler at bottom of file
docker_handler = None

class ServiceManager:
    """
    Service and Package Manager
    """
    def __init__(
        self,
        app,
        compose_file:os.PathLike="/docker/docker-compose.yml",
        lostack_file:os.PathLike="/docker/lostack-compose.yml",
    ) -> None:
        self.app = app
        self.compose_file = compose_file
        self.lostack_file = lostack_file
        self.depot_dir = app.config["DEPOT_DIR"]
        self.client = docker.from_env()
        self.api_client = docker.APIClient()
        self.compose_file_handler = ComposeFileManager(self.compose_file, self.refresh)
        self.lostack_file_handler = ComposeFileManager(self.lostack_file, self.refresh)
        self.depot_handler = DepotManager(app)
        self.logger = logging.getLogger(__name__ + ".ServiceManager")
        self.refresh()

    def refresh(self, event=None) -> None:
        try:
            with self.app.app_context():
                # Get all containers with Sablier labels
                sablier_groups = self.get_running_service_groups()
                existing_services = {s.name: s for s in PackageEntry.query.all() if s.automatic}
                
                # Track which services should exist
                should_exist = set()
                
                # Create or update services based on Docker containers
                for group_name, group_data in sablier_groups.items():
                    should_exist.add(group_name)
                    
                    if not group_name in existing_services:
                        core_service = False
                        if self.compose_file_handler.check_if_service_exists(group_name):
                            # If file is a core service
                            core_service = True

                        # Create new service
                        service = self.create_service_from_labels(group_name, group_data, core_service)
                        existing_services[group_name] = service
                
                # Disable services that no longer have containers
                for service_name, service in existing_services.items():
                    if service_name not in should_exist and service.enabled:
                        service.enabled = False
                        self.logger.info(f"Disabled service: {service_name} (no containers found)")
                
                self.app.db.session.commit()
                
                # Update the Traefik configuration file
                from .models import save_sablier_config_to_file
                if save_sablier_config_to_file():
                    self.logger.info("Traefik configuration updated successfully")
                else:
                    self.logger.error("Failed to update Traefik configuration file")
                    
        except Exception as e:
            self.logger.error(f"Error syncing containers: {e}")
            try:
                self.app.db.session.rollback()
            except Exception:
                pass
    
    def create_service_from_labels(
        self,
        group_name:str,
        group_data:dict,
        core_service:bool=False
    ) -> PackageEntry:
        """Create a new PackageEntry from container labels"""
        labels = group_data['labels']
        
        port = labext.get_traefik_port(labels)
        display_name = labext.get_friendly_name(labels, group_name)
        session_duration = labels.get('lostack.duration', None)
        theme = labels.get('lostack.theme', None)
        refresh_frequency = labels.get('lostack.refresh', None)
        show_details = labext.parse_boolean(labels.get('lostack.show_details', 'true'))
        defaults = LoStackDefaults.get_defaults()
        
        service = PackageEntry(
            name=group_name,
            service_names=','.join(group_data['service_names']),
            display_name=display_name,
            port=port,
            session_duration=session_duration or defaults.session_duration,
            theme=theme or defaults.theme,
            refresh_frequency=refresh_frequency or defaults.refresh_frequency,
            show_details=show_details,
            enabled=True,
            automatic=True,
            core_service=core_service
        )
        
        self.app.db.session.add(service)
        self.logger.info(f"Created new service: {group_name}")
        return service
    
    def get_running_services_info(self, service_names:list[str]) -> dict:
        """Gets a list of running services from docker groups using the api client"""
        containers = {}
        for c in self.api_client.containers(all=True):
            name = c["Names"][0].strip("/")
            containers[name] = c
        result = {}
        for n in service_names:
            result[n] = containers.get(n)
        return result
        
    def get_running_service_groups(self) -> dict:
        """Gets a list of running services from docker groups sorted by group"""
        groups = {}
        try:
            containers = self.client.containers.list(all=True)
            groups = {}
            for container in containers:
                labels = labext.normalize_labels(container.labels or {})
                if not labext.parse_boolean(labels.get('sablier.enable', "false")):
                    continue

                group = labels.get('sablier.group')
                if not group:
                    continue
                
                if not group in groups:
                    groups[group] = {
                        'containers': [],
                        'main_container': None,
                        'labels': {},
                        'service_names': []
                    }

                groups[group]['containers'].append(container)
                groups[group]['service_names'].append(container.name)
                if labext.parse_boolean(labels.get('lostack.primary', "false")):
                    groups[group]['main_container'] = container
                    groups[group]['labels'] = labels

        except Exception as e:
            self.logger.error(f"Error getting service groups: {e}")
        return groups


    def get_installed_packages(self) -> list[str]:
        """Gets a list of installed packages by looking at compose file labels."""
        packages = []

        for handler in (
            self.compose_file_handler,
            self.lostack_file_handler
        ):
            for name, service in handler.content.get("services", {}).items():
                if not isinstance(service, dict):
                    continue
                labels = labext.normalize_labels(service.get('labels', []))
                primary = labext.parse_boolean(labext.get_label("lostack.primary"))
                if primary:
                    packages.append(name)
        return packages

    def get_installable_packages(self) -> list[str]:
        """
        Gets a list of installable LoStack packages.
        Excludes currently installed packages.
        """
        packages = self.get_all_depot_packages()
        installed = self.get_installed_packages()
        installable = []
        for p in packages:
            if p in installed:
                continue
            installable.append(p)
        return installable
    
    def add_depot_package(self, package_name:str, result_queue) -> list[str]:
        """
        Adds a depot package to the dynamic compose.
        Returns the list of docker services added.
        """
        result_queue.put_nowait(f"Adding depot package...")
        package_data = self.depot_handler.get_package_data(package_name)
        if not package_data:
            msg = f"DEPOT: Failed to get package data for {package_name}"
            result_queue.put_nowait(msg)
            raise FileNotFoundError(msg)
        result_queue.put_nowait(f"Got package data")
        service_names = list(package_data.get("services", {}).keys())
        try: 
            result_queue.put_nowait(f"Adding services {', '.join(service_names)}")
            self.lostack_file_handler.add_services_from_package_data(package_data)
        except Exception as e:
            result_queue.put_nowait(f"Error adding services to dynamic compose - {e}")
            result_queue.put_nowait(f"Aborting...")
            time.sleep(1) # Ensure result queue gets pushed to user before context ends
            raise e
        
        result_queue.put_nowait(f"Added services: {service_names}")
        return service_names
    
    def remove_depot_package(self, service_db_id:str, result_queue) -> "queue":
        result_queue.put_nowait(f"Removing depot package...")
        with self.app.app_context():
            print(service_db_id)
            service = PackageEntry.query.get_or_404(service_db_id)

            from .actions import docker_compose_stop, docker_remove
            # import here to prevent circular dependency issues

            package_name = service.name
            docker_service_names = service.docker_services
            if service and not docker_service_names:
                """Fix in case of broken db entry"""
                app.db.session.delete(service)
                app.db.session.commit()
                return StreamHandler.message_completion_stream("No services to handle, deleted db entry.")
            
            try:
                result_queue.put_nowait(f"Starting removal of services: {', '.join(docker_service_names)}")
                containers = self.get_running_services_info(docker_service_names)
                running_containers = [
                    name for name, info in containers.items()
                    if info and info.get("State") in ["running", "starting"]
                ]
                if running_containers:
                    result_queue.put_nowait(f"Stopping running containers: {', '.join(running_containers)}")
                    docker_compose_stop(running_containers, result_queue, compose_file=self.lostack_file, complete=False)
                else:
                    result_queue.put_nowait("No running containers found to stop")
            
                existing_containers = [name for name, info in containers.items() if info is not None]
                if existing_containers:
                    result_queue.put_nowait(f"Removing containers: {', '.join(existing_containers)}")
                    docker_remove(existing_containers, result_queue, complete=False)
                else:
                    result_queue.put_nowait("No containers found to remove")

                # Update compose file
                result_queue.put_nowait(f"Updating {self.lostack_file_handler.file}...")
                try:
                    compose_data = self.lostack_file_handler.content.copy()
                    services_to_remove = []

                    for service_name in docker_service_names:
                        if service_name in compose_data.get("services", {}):
                            services_to_remove.append(service_name)
                            del compose_data["services"][service_name]

                    if services_to_remove:
                        self.lostack_file_handler.write(compose_data)
                        result_queue.put_nowait(f"Removed services from LoStack compose file: {', '.join(services_to_remove)}")
                    else:
                        result_queue.put_nowait("No services found in LoStack compose file to remove")
                except Exception as e:
                    result_queue.put_nowait(f"Warning: Could not update LoStack compose file: {str(e)}")

                result_queue.put_nowait("Removing database entries...")

                # Delete db services
                services_to_delete = PackageEntry.query.filter(
                    PackageEntry.service_names.in_(docker_service_names)
                ).all()

                all_services = PackageEntry.query.all()
                for service in all_services:
                    service_docker_names = service.docker_services
                    if any(name in docker_service_names for name in service_docker_names):
                        if service not in services_to_delete:
                            services_to_delete.append(service)
                
                deleted_count = 0
                for service in services_to_delete:
                    self.app.db.session.delete(service)
                    deleted_count += 1
                
                if deleted_count > 0:
                    self.app.db.session.commit()
                    result_queue.put_nowait(f"Removed {deleted_count} database entries")
                else:
                    result_queue.put_nowait("No database entries found to remove")

                # Regenerate Sablier config
                result_queue.put_nowait("Regenerating Traefik configuration...")
                try:
                    if save_sablier_config_to_file():
                        result_queue.put_nowait("Traefik dynamic configuration updated successfully")
                    else:
                        result_queue.put_nowait("Warning: Could not update Traefik dynamic configuration")
                except Exception as e:
                    result_queue.put_nowait(f"Warning: Error updating Traefik dynamic config: {str(e)}")

                result_queue.put_nowait("Package removal completed successfully")
            except Exception as e:
                result_queue.put_nowait(f"Error handling package removal - {e}")
            finally:
                result_queue.put_nowait("__COMPLETE__")
                self.force_sync()
        return result_queue

    def force_sync(self) -> None:
        """Refresh configs"""
        self.refresh()
    
    def stop(self) -> None:
        self.logger.info("Stopping service manager")
        self.compose_file_handler.observer.stop()
        self.lostack_file_handler.observer.stop()
        self.compose_file_handler.observer.join(timeout=5)
        self.lostack_file_handler.observer.join(timeout=5)
        self.logger.info("Service manager stopped")

def init_docker_handler(app) -> ServiceManager:
    """Create global Docker handler"""
    global docker_handler
    if docker_handler:
        raise ValueError("Docker Handler already initialized")
    docker_handler = ServiceManager(app)
    return docker_handler

def get_docker_handler() -> ServiceManager:
    """
    Get global Docker handler
    """
    global docker_handler
    return docker_handler