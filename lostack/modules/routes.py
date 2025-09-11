import os
import yaml
from flask import (
    current_app as app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    abort
)
from flask_login import current_user
from .common.file_handler import FileHandler
from .common.stream_handler import StreamHandler
from .common.label_extractor import LabelExtractor
from .forms import (
    LoStackDefaultsForm, 
    PackageEntryForm,
    UserSettingsForm,
    populate_defaults_form,
    populate_service_form,
    populate_user_settings_form
)
from .models import (
    PERMISSION_ENUM,
    LoStackDefaults,
    PackageEntry,
    User,
    save_sablier_config_to_file
)
from .package_manager import get_docker_handler
from .streams import (
    stream_docker_compose_up,
    stream_docker_compose_stop,
    stream_depot_package_install,
    stream_depot_update,
    stream_remove_package,
    stream_docker_start,
    stream_docker_stop,
    stream_docker_follow,
    stream_docker_down,
    stream_docker_remove,
    stream_docker_logs
)


@app.route("/")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def services():
    """List all installed Packages groups"""
    services = PackageEntry.query.order_by(PackageEntry.name).all()
    all_names = []
    for s in services:
        for n in [_n.strip() for _n in s.service_names.split(",") if _n.strip()]:
            all_names.append(n)
    container_names = all_names

    from .package_manager import docker_handler
    containers = docker_handler.get_running_services_info(container_names)

    return render_template(
        "services.html",
        services=services,
        containers=containers,
    )


@app.route("/containers")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def containers():
    """Docker container management"""
    from .package_manager import get_docker_handler
    docker_handler = get_docker_handler()
    containers = docker_handler.api_client.containers(all=True)

    return render_template(
        "containers.html",
        containers=containers
    )

@app.route("/containers/<id>/<action>")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def containers_action(id, action):
    """Docker container management"""
    actions = {
        "start" : stream_docker_start,
        "stop" : stream_docker_stop,
        "remove" : stream_docker_remove,
        "logs" : stream_docker_logs,
        "follow" : stream_docker_follow,
    }
    act = actions.get(action)
    if not act:
        raise ValueError(f"Invalid container action")

    return act(id)

@app.route('/api/containers')
@app.permission_required(PERMISSION_ENUM.ADMIN)
def api_containers():
    """Docker container management"""
    from .package_manager import get_docker_handler
    docker_handler = get_docker_handler()
    containers = docker_handler.api_client.containers(all=True)
    return jsonify({
        'containers': containers
    })


@app.route("/settings", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def settings():
    """Edit LoStack package default configuration"""
    form = LoStackDefaultsForm()
    defaults = LoStackDefaults.get_defaults()

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
            app.db.session.commit()
            flash("Default configuration updated successfully!", "success")

            if save_sablier_config_to_file():
                flash("Configuration file regenerated successfully!", "info")
            else:
                flash("Warning: Configuration file could not be regenerated!", "warning")

            return redirect(url_for("settings"))
        except Exception as e:
            app.db.session.rollback()
            flash(f"Error updating LoStack defaults: {str(e)}", "error")

    if not form.is_submitted():
        populate_defaults_form(form, defaults)

    return render_template("settings.html", form=form)


@app.route("/user-settings", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.USER)
def user_settings():
    """Edit user settings"""
    form = UserSettingsForm()
    user = current_user

    if request.method == "GET":
        populate_user_settings_form(form, user)

    if form.validate_on_submit():
        try:
            user_obj = User.query.get_or_404(current_user.id)

            user_obj.theme = form.theme.data
            user_obj.editor_theme = form.editor_theme.data

            print("NEW THEMES", user_obj.theme, user_obj.editor_theme)
            app.db.session.commit()
            flash("Your settings have been updated successfully!", "success")
            return redirect(url_for("user_settings"))
        except Exception as e:
            app.db.session.rollback()
            flash(f"Error updating settings: {str(e)}", "error")

    if not form.is_submitted():
        populate_user_settings_form(form, user)

    return render_template("user_settings.html", form=form)


@app.route("/user-settings/preview")
@app.permission_required(PERMISSION_ENUM.USER)
def user_settings_preview():
    """Render live preview for user settings"""
    theme = request.args.get("theme", "default")
    editor_theme = request.args.get("editor_theme", "default")
    print("PREVIEWING WITH THEMES", theme, editor_theme)
    return render_template(
        "user_settings_preview.html",
        override_theme=theme,
        editor_theme=editor_theme
    )


@app.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def service_edit(service_id):
    """Edit an existing Sablier service"""
    service = PackageEntry.query.get_or_404(service_id)
    form = PackageEntryForm()
    
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
            app.db.session.commit()
            flash(f"Service '{service.display_name_or_name}' updated successfully!", "success")
            
            if save_sablier_config_to_file():
                flash("Configuration file updated!", "info")
            
            return redirect(url_for("services"))
        except Exception as e:
            app.db.session.rollback()
            flash(f"Error updating service: {str(e)}", "error")
    
    return render_template("service_form.html", form=form, service=service, action="Edit")


@app.route('/services/<int:service_id>/action/<action>')
@app.permission_required(PERMISSION_ENUM.ADMIN)
def sablier_service_action(service_id, action):
    service = PackageEntry.query.get_or_404(service_id)
    docker_service_names = service.docker_services
    act = {
        "up": stream_docker_compose_up,
        "stop": stream_docker_compose_stop,
        "remove": stream_docker_remove
    }.get(action)
        
    if not act:
        abort(400)

    if action in ["up", "stop"]:
        compose_file = "/docker/docker-compose.yml" if service.core_service else "/docker/lostack-compose.yml"
        return act(docker_service_names, compose_file)
    else:
        return act(docker_service_names)


@app.route("/services/<int:service_id>/toggle", methods=["POST"])
@app.permission_required(PERMISSION_ENUM.ADMIN)
def service_toggle(service_id):
    """AJAX endpoint to toggle service enabled status"""
    service = PackageEntry.query.get_or_404(service_id)
    
    try:
        service.enabled = not service.enabled
        app.db.session.commit()
        
        config_updated = save_sablier_config_to_file()
        
        return jsonify({
            "success": True,
            "enabled": service.enabled,
            "config_updated": config_updated,
            "message": f"Service {'enabled' if service.enabled else 'disabled'} successfully"
        })
    except Exception as e:
        app.db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/depot")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def depot():
    """Show depot page"""
    docker_handler = get_docker_handler()
    all_packages = docker_handler.depot_handler.packages.keys()
    installed_packages = [s.name for s in PackageEntry.query.all()]
    available_packages = [s for s in all_packages if not s in installed_packages]
    depot_data = docker_handler.depot_handler.format_packages_for_depot_page(available_packages)
    # Passes pre-formatted data / arguments to template:
    # Pre-processing litterally halved the size of the template file
    # I wasted so much time writing all that jinja filtering 
    # trying to process the data directly lol
    # {
    #     'packages': processed_packages,
    #     'groups': dict(sorted(group_counts.items())),
    #     'tags': dict(sorted(tag_counts.items())),
    #     'total_count': len(processed_packages)
    # }
    return render_template(
        "depot.html",
        **depot_data,
        depot_repo=app.config.get("DEPOT_URL"),
        depot_branch=app.config.get("DEPOT_BRANCH")
    )


@app.route("/depot/update/stream")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def update_depot():
    return stream_depot_update()


@app.route('/depot/launch/<package>/stream')
@app.permission_required(PERMISSION_ENUM.ADMIN)
def depot_launch(package):
    return stream_depot_package_install(package)
    

@app.route('/depot/remove/<int:service_id>/stream')
@app.permission_required(PERMISSION_ENUM.ADMIN)
def depot_remove(service_id: int):
    service = PackageEntry.query.get_or_404(service_id)
    package_name = service.name
    docker_service_names = service.docker_services
    if service and not docker_service_names:
        app.db.session.delete(service)
        app.db.session.commit()
        return StreamHandler.message_completion_stream("No services to handle, deleted db entry,")
    else:
        return stream_remove_package(service_id)


@app.route("/depot_info")
@app.permission_required(PERMISSION_ENUM.ADMIN)
def depot_info():
    return "OK", 200