from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, 
    HiddenField,
    SelectField, 
    StringField, 
    SubmitField
)
from wtforms.validators import (
    DataRequired, 
    Length, 
    Optional, 
    Regexp, 
    ValidationError
)


SERVICE_NAME_REGEX = r'^[a-z0-9-]+$'
SERVICE_DEPENDENCIES_REGEX = r'^[a-z0-9-,]*$'
REFRESH_FREQUENCY_REGEX = r'^\d+[s]s?$'
PORT_REGEX = r'^\d{1,5}$'
SESSION_DURTION_REGEX =  r'^\d+[smh]$'
ACCESS_GROUPS_REGEX = r'^[a-zA-Z0-9,._\s-]+$'


class PackageEntryForm(FlaskForm):
    """Form for creating and editing LoStack Package entries"""
    
    id = HiddenField()
    
    name = StringField(
        'Container Name',
        validators=[
            DataRequired(message="Container name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
            Regexp(
                SERVICE_NAME_REGEX,
                message="Name can only contain lowercase letters, numbers, and hyphens"
            )
        ],
        render_kw={
            "placeholder": "my-service",
            "class": "form-control"
        },
        description="Unique service name"
    )

    service_names = StringField(
        'Service Names',
        validators=[
            Length(min=0, max=400, message="Name must be between 0 and 400 characters"),
            Regexp(
                SERVICE_DEPENDENCIES_REGEX,
                message="Separate with commas. Names can only contain lowercase letters, numbers, and hyphens."
            )
        ],
        render_kw={
            "placeholder": "service-db,service-redis",
            "class": "form-control"
        },
        description="Startup containers, use commas, no spaces."
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
        description="Custom name shown on loading page (optional)"
    )
    
    port = StringField(
        'Internal Port',
        validators=[
            DataRequired(message="Port is required"),
            Regexp(
                PORT_REGEX,
                message="Invalid port, must be between 1 and 65535"
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
               SESSION_DURTION_REGEX,
                message="Duration must be in format like '5m', '30s', or '2h'"
            )
        ],
        render_kw={
            "placeholder": "5m",
            "class": "form-control"
        },
        description="Idle time until container shutdown (e.g., 45s, 5m, 1h)"
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
        description="Loading page theme"
    )
    
    refresh_frequency = StringField(
        'Refresh Frequency',
        validators=[
            DataRequired(message="Refresh frequency is required"),
            Regexp(
                REFRESH_FREQUENCY_REGEX,
                message="Frequency must be in format like '3s', '500ms', or '1s'"
            )
        ],
        render_kw={
            "placeholder": "3s",
            "class": "form-control"
        },
        description="Loading page refresh interval (e.g., 3s, 10s)"
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

    sablier_middleware_enabled = BooleanField(
        'Auto-Start',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Enable Sablier Auto-Start"
    )

    lostack_middleware_enabled = BooleanField(
        'Access Control',
        default=True,
        render_kw={"class": "form-check-input"},
        description="Enable LoStack group access control"
    )

    access_groups = StringField(
        'Access Groups',
        validators=[
            Length(min=0, max=400, message="Name must be between 0 and 400 characters"),
            Regexp(
                ACCESS_GROUPS_REGEX,
                message="Letters, numbers, underscores, and commas only."
            )
        ],
        render_kw={
            "placeholder": "service-db,service-redis",
            "class": "form-control"
        },
        description="Allowed LDAP Groups. Separate with commas"
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
        with current_app.app_context():
            if field.data:
                # Skip validation if this is an edit (has id) and name hasn't changed
                if self.id.data:
                    existing_service = current_app.models.PackageEntry.query.get(self.id.data)
                    if existing_service and existing_service.name == field.data:
                        return
                
                # Check for duplicate names
                existing = current_app.models.PackageEntry.query.filter_by(name=field.data).first()
                if existing:
                    raise ValidationError("A service with this name already exists")

def populate_package_entry_form(form:FlaskForm, package:"PackageEntry"=None) -> FlaskForm:
    """Populate the package form with current values"""
    if package:
        form.id.data = package.id
        form.name.data = package.name
        form.display_name.data = package.display_name
        form.port.data = package.port
        form.session_duration.data = package.session_duration
        form.theme.data = package.theme
        form.refresh_frequency.data = package.refresh_frequency
        form.show_details.data = package.show_details
        form.enabled.data = package.enabled
        form.lostack_middleware_enabled.data = package.lostack_middleware_enabled
        form.sablier_middleware_enabled.data = package.sablier_middleware_enabled
        form.access_groups.data = package.access_groups
        form.service_names.data = package.service_names
    return form