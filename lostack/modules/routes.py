import os
import logging
import queue
import subprocess
import threading
import yaml
from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    Response,
    url_for
)
from .forms import (
    BulkServiceForm,
    SablierDefaultsForm, 
    SablierServiceForm, 
    populate_defaults_form,
    populate_service_form
)
from .models import (
    PERMISSION_ENUM,
    SablierDefaults,
    SablierService,
    save_sablier_config_to_file
)
from .streams import (
    stream_docker_start,
    stream_docker_stop,
    stream_docker_down,
    stream_docker_remove,
    stream_docker_compose_up,
    stream_docker_compose_down,
    stream_docker_compose_stop,
    stream_depot_package_install,
    stream_depot_update
)
from .depot.depot import scan_depot
from .docker.client import get_services_info
from flask import current_app as app
db = app.db

@app.route("/")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def services():
    """List all Sablier services"""
    services = SablierService.query.order_by(SablierService.name).all()
    # docker_containers = ...
    all_names = []
    for s in services:
        for n in [_n.strip() for _n in s.names.split(",") if _n.strip()]:
            all_names.append(n)
    container_names = all_names
    # print(container_names)
    containers = get_services_info(container_names)

    # import json
    # print(json.dumps(containers, indent=2))

    bulk_form = BulkServiceForm() # Not fully implemented yet - future bulk ops
    return render_template(
        "services.html",
        services=services,
        containers=containers,
        bulk_form=bulk_form
    )


@app.route("/settings", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def settings():
    """Edit Sablier default configuration"""
    form = SablierDefaultsForm()
    defaults = SablierDefaults.get_defaults()

    if request.method == "GET":
        populate_defaults_form(form, defaults)

    if form.validate_on_submit():
        defaults.domain = form.domain.data
        defaults.sablier_url = form.sablier_url.data
        defaults.session_duration = form.session_duration.data
        defaults.theme = form.theme.data
        defaults.refresh_frequency = form.refresh_frequency.data
        defaults.show_details = form.show_details.data

        try:
            db.session.commit()
            flash("Default configuration updated successfully!", "success")

            if save_sablier_config_to_file():
                flash("Configuration file regenerated successfully!", "info")
            else:
                flash("Warning: Configuration file could not be regenerated!", "warning")

            return redirect(url_for("defaults"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating defaults: {str(e)}", "error")

    if not form.is_submitted():
        populate_defaults_form(form, defaults)

    return render_template("defaults.html", form=form)


@app.route("/new", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def service_new():
    """Create a new Sablier service"""
    form = SablierServiceForm()
    
    if request.method == "GET":
        defaults = SablierDefaults.get_defaults()
        form.session_duration.data = defaults.session_duration
        form.theme.data = defaults.theme
        form.refresh_frequency.data = defaults.refresh_frequency
        form.show_details.data = defaults.show_details
        form.port.data = "80"
    
    if form.validate_on_submit():
        service = SablierService(
            name=form.name.data,
            names=form.names.data,
            display_name=form.display_name.data or None,
            port=form.port.data,
            session_duration=form.session_duration.data,
            theme=form.theme.data,
            refresh_frequency=form.refresh_frequency.data,
            show_details=form.show_details.data,
            enabled=form.enabled.data
        )
        
        try:
            db.session.add(service)
            db.session.commit()
            flash(f"Service '{service.display_name_or_name}' created successfully!", "success")
            
            if save_sablier_config_to_file():
                flash("Configuration file updated!", "info")
            
            return redirect(url_for("services"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating service: {str(e)}", "error")
    
    return render_template("service_form.html", form=form, action="Create")


@app.route("/import", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def service_import():
    """Import services from YAML configuration"""
    if request.method == "POST":
        if 'config_file' not in request.files:
            flash("No file selected!", "error")
            return redirect(url_for("service_import"))
        
        file = request.files['config_file']
        if file.filename == '':
            flash("No file selected!", "error")
            return redirect(url_for("service_import"))
        
        if not file.filename.lower().endswith(('.yml', '.yaml')):
            flash("Please upload a YAML file (.yml or .yaml)", "error")
            return redirect(url_for("service_import"))
        
        try:
            yaml_content = file.read().decode('utf-8')
            config_data = yaml.safe_load(yaml_content)
            
            if 'services' not in config_data:
                flash("Invalid configuration format. Expected 'services' section.", "error")
                return redirect(url_for("service_import"))
            
            defaults = SablierDefaults.get_defaults()
            imported_count = 0
            skipped_count = 0
            errors = []
            
            for service_name, service_config in config_data['services'].items():
                # Check if service already exists
                existing_service = SablierService.query.filter_by(name=service_name).first()
                if existing_service:
                    skipped_count += 1
                    continue
                
                try:
                    url = service_config.get('url', '')
                    port = "80"
                    if ':' in url and url.count(':') >= 2:
                        port_part = url.split(':')[-1].rstrip('/')
                        if port_part.isdigit():
                            port = port_part
                    
                    service = SablierService(
                        name=service_name,
                        names=service_config.get('names', ''),
                        display_name=service_config.get('displayName', service_name.title()),
                        port=port,
                        session_duration=service_config.get('sessionDuration', defaults.session_duration),
                        theme=service_config.get('theme', defaults.theme),
                        refresh_frequency=service_config.get('refreshFrequency', defaults.refresh_frequency),
                        show_details=service_config.get('showDetails', defaults.show_details),
                        enabled=True
                    )
                    
                    db.session.add(service)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Error importing {service_name}: {str(e)}")
            
            if imported_count > 0:
                try:
                    db.session.commit()
                    flash(f"Successfully imported {imported_count} services!", "success")
                    
                    if skipped_count > 0:
                        flash(f"Skipped {skipped_count} services (already exist)", "warning")
                    
                    if save_sablier_config_to_file():
                        flash("Configuration file updated!", "info")
                    
                    if errors:
                        for error in errors:
                            flash(error, "warning")
                    
                    return redirect(url_for("services"))
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error saving imported services: {str(e)}", "error")
            else:
                if skipped_count > 0:
                    flash(f"All {skipped_count} services already exist, nothing to import.", "info")
                else:
                    flash("No services found to import.", "warning")
                
                if errors:
                    for error in errors:
                        flash(error, "error")
        
        except yaml.YAMLError as e:
            flash(f"Invalid YAML format: {str(e)}", "error")
        except Exception as e:
            flash(f"Error processing file: {str(e)}", "error")
    
    return render_template("import.html")


@app.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def service_edit(service_id):
    """Edit an existing Sablier service"""
    service = SablierService.query.get_or_404(service_id)
    form = SablierServiceForm()
    
    if request.method == "GET":
        populate_service_form(form, service)
    
    if form.validate_on_submit():
        service.name = form.name.data
        service.display_name = form.display_name.data or None
        service.port = form.port.data
        service.session_duration = form.session_duration.data
        service.theme = form.theme.data
        service.refresh_frequency = form.refresh_frequency.data
        service.show_details = form.show_details.data
        service.enabled = form.enabled.data
        
        try:
            db.session.commit()
            flash(f"Service '{service.display_name_or_name}' updated successfully!", "success")
            
            if save_sablier_config_to_file():
                flash("Configuration file updated!", "info")
            
            return redirect(url_for("services"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating service: {str(e)}", "error")
    
    return render_template("service_form.html", form=form, service=service, action="Edit")


@app.route("/services/<int:service_id>/delete", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def service_delete(service_id):
    """Delete a Sablier service"""
    service = SablierService.query.get_or_404(service_id)

    service_name = service.display_name_or_name
    
    try:
        db.session.delete(service)
        db.session.commit()
        flash(f"Service '{service_name}' deleted successfully!", "success")
        
        if save_sablier_config_to_file():
            flash("Configuration file updated!", "info")
        
        return redirect(url_for("services"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting service: {str(e)}", "error")

    return redirect(url_for("services"))


@app.route("/services/<int:service_id>/toggle", methods=["POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def service_toggle(service_id):
    """AJAX endpoint to toggle service enabled status"""
    service = SablierService.query.get_or_404(service_id)
    
    try:
        service.enabled = not service.enabled
        db.session.commit()
        
        config_updated = save_sablier_config_to_file()
        
        return jsonify({
            "success": True,
            "enabled": service.enabled,
            "config_updated": config_updated,
            "message": f"Service {'enabled' if service.enabled else 'disabled'} successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/services/<int:service_id>/action/<action>')
def sablier_service_action(service_id, action):
    service = SablierService.query.get_or_404(service_id)
    docker_service_names = service.docker_services
    act = {
        "up" : stream_docker_compose_up,
        "stop" : stream_docker_compose_stop,
        "remove" : stream_docker_remove
    }.get(action)
        
    if not act:
        abort(400)

    return act(docker_service_names)


@app.route("/depot")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def depot():
    """Gets depot sablier services that haven't been registered yet"""

    depot_dir = app.config.get("DEPOT_DIR")
    
    depot_services = scan_depot(depot_dir)
    available_services = depot_services.keys()
    
    existing_services = [s.name for s in SablierService.query.all()]
    available_services = [s for s in available_services if not s in existing_services]

    from .docker.helpers import get_service_details
    packages = {}
    for s in available_services:
        package_path = os.path.join(depot_dir, "packages", s, "docker-compose.yml")
        get_service_details(package_path, available_services, packages)

    return render_template("depot.html", packages=packages)

@app.route("/depot/update/stream")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def update_depot():
    return stream_depot_update()


@app.route('/depot/launch/<package>/stream')
def depot_launch(package):
    depot_dir = app.config.get("DEPOT_DIR")
    package_path = os.path.join(depot_dir, "packages", package, "docker-compose.yml")
    return stream_depot_package_install(package_path)
    


# @app.route('/depot/action/<package>/<action>/')
# def depot_launch_stream(package, action):
#     actions = {
#         "up" : stream_docker_compose_up,
#     }
#     callback = actions.get(action)
#     if not callback:
#         abort(400)

#     return callback(package)
    
   

@app.route("/depot_info")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def depot_info():
    return "OK", 200


@app.route("/templater")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def templater():
    """Make Compose templates easier"""
    return render_template("templater.html")