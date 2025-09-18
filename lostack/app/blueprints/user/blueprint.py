import fnmatch
import json
import logging
import os
from flask import (
    Flask,
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for
)
from flask_login import current_user

from .themes import BOOTSWATCH_THEMES, CODEMIRROR_THEMES

def register_blueprint(app:Flask) -> Blueprint:
    bp = blueprint = Blueprint(
        'user_settings',
        __name__,
        url_prefix="",
        template_folder=os.path.join(os.path.dirname(__file__), "templates")
    )

    @bp.route("/user_settings", methods=["GET", "POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.USER)
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
                current_app.db.session.commit()
                flash("Your settings have been updated successfully!", "success")
                return redirect(url_for("user_settings.user_settings"))
            except Exception as e:
                current_app.db.session.rollback()
                flash(f"Error updating settings: {str(e)}", "error")

        if not form.is_submitted():
            populate_user_settings_form(form, user)

        return render_template("user_settings.html", form=form)


    app.config["PROVIDED_CONTEXT"].update({
        "BOOTSWATCH_THEMES" : BOOTSWATCH_THEMES,
        "CODEMIRROR_THEMES" : CODEMIRROR_THEMES
    })
    app.register_blueprint(blueprint)
    return Blueprint