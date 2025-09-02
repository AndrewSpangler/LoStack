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


class SablierDefaultsForm(FlaskForm):
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
            ('blackboard', 'Blackboard'),
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


class SablierServiceForm(FlaskForm):
    """Form for creating and editing Sablier services"""
    
    id = HiddenField()
    
    name = StringField(
        'Service Name',
        validators=[
            DataRequired(message="Service name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
            Regexp(
                r'^[a-z0-9-]+$',
                message="Name can only contain lowercase letters, numbers, and hyphens"
            )
        ],
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Unique service name (used in URLs and container names)"
    )

    names = StringField(
        'Service Dependencies',
        validators=[
            Length(min=0, max=400, message="Name must be between 0 and 400 characters"),
            Regexp(
                r'^[a-z0-9-,]*$',
                message="Separate with commas. Names can only contain lowercase letters, numbers, and hyphens."
            )
        ],
        render_kw={
            "placeholder": "service-db,service-redis",
            "class": "form-control"
        },
        description="Dependencies needed by main container to up/down with it."
    )
    
    display_name = StringField(
        'Display Name',
        validators=[
            Optional(),
            Length(max=200, message="Display name cannot exceed 200 characters")
        ],
        render_kw={
            "placeholder": "My Service",
            "class": "form-control"
        },
        description="Human-readable name (optional, will use service name if empty)"
    )
    
    port = StringField(
        'Port',
        validators=[
            DataRequired(message="Port is required"),
            Regexp(
                r'^\d{1,5}$',
                message="Port must be a number between 1 and 65535"
            )
        ],
        render_kw={
            "placeholder": "8080",
            "class": "form-control"
        },
        description="Port the service runs on"
    )
    
    session_duration = StringField(
        'Session Duration',
        validators=[
            DataRequired(message="Session duration is required"),
            Regexp(
                r'^\d+[smh]$',
                message="Duration must be in format like '5m', '30s', or '2h'"
            )
        ],
        render_kw={
            "placeholder": "5m",
            "class": "form-control"
        },
        description="How long to keep the service running after last access"
    )
    
    theme = SelectField(
        'Theme',
        choices=[
            ('ghost', 'Ghost'),
            ('hacker-terminal', 'Hacker Terminal'),
            ('blackboard', 'Blackboard'),
            ('shuffle', 'Shuffle')
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
        description="Theme for the loading page"
    )
    
    refresh_frequency = StringField(
        'Refresh Frequency',
        validators=[
            DataRequired(message="Refresh frequency is required"),
            Regexp(
                r'^\d+[sm]s?$',
                message="Frequency must be in format like '3s', '500ms', or '1s'"
            )
        ],
        render_kw={
            "placeholder": "3s",
            "class": "form-control"
        },
        description="How often to refresh the loading page"
    )
    
    show_details = BooleanField(
        'Show Details',
        render_kw={"class": "form-check-input"},
        description="Show service details on the loading page"
    )
    
    enabled = BooleanField(
        'Enabled',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Include this service in the generated configuration"
    )
    
    submit = SubmitField(
        'Save Service',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_port(self, field):
        """Custom validator for port range"""
        try:
            port_num = int(field.data)
            if not (1 <= port_num <= 65535):
                raise ValidationError("Port must be between 1 and 65535")
        except ValueError:
            raise ValidationError("Port must be a valid number")
    
    def validate_name(self, field):
        """Custom validator to check for service name uniqueness"""
        from .models import SablierService
        from flask import current_app as app
        with app.app_context():
            if field.data:
                # Skip validation if this is an edit (has id) and name hasn't changed
                if self.id.data:
                    existing_service = SablierService.query.get(self.id.data)
                    if existing_service and existing_service.name == field.data:
                        return
                
                # Check for duplicate names
                existing = SablierService.query.filter_by(name=field.data).first()
                if existing:
                    raise ValidationError("A service with this name already exists")


class DeleteServiceForm(FlaskForm):
    """Simple form for service deletion confirmation"""
    
    service_id = HiddenField(validators=[DataRequired()])
    service_name = HiddenField()
    
    confirm = BooleanField(
        'I understand this action cannot be undone',
        validators=[DataRequired(message="You must confirm deletion")],
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Delete Service',
        render_kw={"class": "btn btn-danger"}
    )


class BulkServiceForm(FlaskForm):
    """Form for bulk operations on services"""
    
    action = SelectField(
        'Action',
        choices=[
            ('enable', 'Enable Selected'),
            ('disable', 'Disable Selected'),
            ('delete', 'Delete Selected')
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    selected_services = HiddenField()  # Will contain comma-separated service IDs
    
    confirm = BooleanField(
        'Confirm bulk operation',
        validators=[DataRequired(message="You must confirm bulk operation")],
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Apply Action',
        render_kw={"class": "btn btn-warning"}
    )


# Helper function to populate forms from model instances
def populate_defaults_form(form, defaults=None):
    """Populate the defaults form with current values"""
    if defaults is None:
        from app import app, SablierDefaults
        with app.app_context():
            defaults = SablierDefaults.get_defaults()
    
    form.domain.data = defaults.domain
    form.sablier_url.data = defaults.sablier_url
    form.session_duration.data = defaults.session_duration
    form.theme.data = defaults.theme
    form.refresh_frequency.data = defaults.refresh_frequency
    form.show_details.data = defaults.show_details
    return form


def populate_service_form(form, service=None):
    """Populate the service form with current values"""
    if service:
        form.id.data = service.id
        form.name.data = service.name
        form.display_name.data = service.display_name
        form.port.data = service.port
        form.session_duration.data = service.session_duration
        form.theme.data = service.theme
        form.refresh_frequency.data = service.refresh_frequency
        form.show_details.data = service.show_details
        form.enabled.data = service.enabled
    return form


def validate_duration_format(form, field) -> None:
    """Reusable validator for duration fields"""
    if field.data and not field.data.match(r'^\d+[smh]$'):
        raise ValidationError("Duration must be in format like '5m', '30s', or '2h'")


def validate_frequency_format(form, field) -> None:
    """Reusable validator for frequency fields"""
    if field.data and not field.data.match(r'^\d+[sm]s?$'):
        raise ValidationError("Frequency must be in format like '3s', '500ms', or '1s'")