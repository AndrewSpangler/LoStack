from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired

from .themes import BOOTSWATCH_THEMES, CODEMIRROR_THEMES

class UserSettingsForm(FlaskForm):
    """Form for editing User Settings"""
    theme = SelectField(
        'Bootswatch Theme',
        choices=[
            (t, t.title(), )
            for t in BOOTSWATCH_THEMES
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
        description="Theme for general LoStack UI"
    )
    editor_theme = SelectField(
        'CodeMirror Theme',
        choices=[
            (t, t.title(), )
            for t in CODEMIRROR_THEMES
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
        description="Theme for CodeMirror text editor"
    )
    
    submit = SubmitField(
        'Update Settings',
        render_kw={"class": "btn btn-primary"}
    )