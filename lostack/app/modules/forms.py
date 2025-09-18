from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, 
    HiddenField,
    IntegerField,
    SelectField, 
    StringField, 
    SubmitField
)
from wtforms.validators import (
    DataRequired, 
    Length, 
    NumberRange,
    Optional, 
    Regexp, 
    ValidationError
)
from wtforms.widgets import TextArea

# REGEX
DOMAIN_REGEX = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
URL_REGEX = r'^https?://.+'
DURATION_REGEX = r'^\d+[smh]$'

class LoStackDefaultsForm(FlaskForm):
    """Form for editing Sablier default configuration"""
    
    domain = StringField(
        'Domain',
        validators=[
            DataRequired(message="Domain is required"),
            Length(min=3, max=255, message="Domain must be between 3 and 255 characters"),
            Regexp(
                DOMAIN_REGEX,
                message="Please enter a valid domain name"
            )
        ],
        render_kw={
            "placeholder": "example.com",
            "class": "form-control"
        },
        description="Base domain for LoStack services"
    )
    
    sablier_url = StringField(
        'Sablier URL',
        validators=[
            DataRequired(message="Sablier URL is required"),
            Length(min=7, max=255, message="URL must be between 7 and 255 characters"),
            Regexp(
                URL_REGEX,
                message="URL must start with http:// or https://"
            )
        ],
        render_kw={
            "placeholder": "http://sablier:10000",
            "class": "form-control"
        },
        description="URL for LoStack service"
    )
    
    session_duration = StringField(
        'Default Session Duration',
        validators=[
            DataRequired(message="Session duration is required"),
            Regexp(
                DURATION_REGEX,
                message="Duration must be in format like '5m', '30s', or '2h'"
            )
        ],
        render_kw={
            "placeholder": "5m",
            "class": "form-control"
        },
        description="Default session duration (e.g., 5m, 30s, 2h)"
    )
    
    theme = SelectField(
        'Default Theme',
        choices=[
            ('ghost', 'Ghost'),
            ('hacker-terminal', 'Hacker Terminal'),
            ('matrix', 'Matrix'),
            ('shuffle', 'Shuffle')
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
        description="Default theme for Sablier loading pages"
    )
    
    refresh_frequency = StringField(
        'Refresh Frequency',
        validators=[
            DataRequired(message="Refresh frequency is required"),
            Regexp(
                DURATION_REGEX,
                message="Frequency must be in format like '3s', '500ms', or '1s'"
            )
        ],
        render_kw={
            "placeholder": "3s",
            "class": "form-control"
        },
        description="How often to refresh the loading page (e.g., 3s, 500ms)"
    )
    
    show_details = BooleanField(
        'Show Details by Default',
        render_kw={"class": "form-check-input"},
        description="Show service details on loading pages by default"
    )
    
    submit = SubmitField(
        'Update Defaults',
        render_kw={"class": "btn btn-primary"}
    )



# Helper function to populate forms from model instances
def populate_defaults_form(form, defaults=None):
    """Populate the defaults form with current values"""
    if defaults is None:
        from app import app, LoStackDefaults
        with app.app_context():
            defaults = LoStackDefaults.get_defaults()
    
    form.domain.data = defaults.domain
    form.sablier_url.data = defaults.sablier_url
    form.session_duration.data = defaults.session_duration
    form.theme.data = defaults.theme
    form.refresh_frequency.data = defaults.refresh_frequency
    form.show_details.data = defaults.show_details
    return form


def populate_user_settings_form(form, user):
    """Populate the user settings form with current values"""
    form.theme.data = user.theme
    form.editor_theme.data = user.editor_theme
    return form


def validate_duration_format(form, field) -> None:
    """Reusable validator for duration fields"""
    if field.data and not field.data.match(r'^\d+[smh]$'):
        raise ValidationError("Duration must be in format like '5m', '30s', or '2h'")


def validate_frequency_format(form, field) -> None:
    """Reusable validator for frequency fields"""
    if field.data and not field.data.match(r'^\d+[sm]s?$'):
        raise ValidationError("Frequency must be in format like '3s', '500ms', or '1s'")