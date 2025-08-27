import datetime
import logging
import yaml
from flask_login import UserMixin
from random import choice as rand_choice
from string import ascii_lowercase
from flask import current_app as app


db = app.db


class PERMISSION_ENUM:
    _NAMES = {
        (EVERYONE := 1) : "everyone",
        (USER := 5)     : "users",
        (ADMIN := 10)   : "admins",
        (OWNER := 15)   : "owners",
        (NOACCESS := 99): "NOACCESS"
    } 
    _LOOKUP = {v:k for k,v in _NAMES.items()}


class User(UserMixin, db.Model):
    """User object with flask_login UserMixin"""
    __tablename__ = "User"
    __bind_key__ = "sablier-app-db"
    id = db.Column(db.Integer, primary_key=True)
    permission_integer = db.Column(db.Integer, default=PERMISSION_ENUM.USER)
    name = db.Column(db.String(100), unique=True, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    @property
    def is_admin(self) -> bool:
        return self.permission_integer >= PERMISSION_ENUM.ADMIN


class SecretKey(db.Model):
    """Table to store FlaskWTF secret key and Flask secret key"""
    __tablename__ = "SecretKey"
    __bind_key__ = "sablier-app-db"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(24), nullable=False)


class SablierDefaults(db.Model):
    """Default configuration for Sablier services"""
    __tablename__ = "SablierDefaults"
    __bind_key__ = "sablier-app-db"
    
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), nullable=False, default=app.config["DOMAIN_NAME"])
    sablier_url = db.Column(db.String(255), nullable=False, default=app.config["SABLIER_URL"])
    session_duration = db.Column(db.String(10), nullable=False, default=app.config["SABLIER_DEFAULT_SESSION_DURATION"])
    theme = db.Column(db.String(50), nullable=False, default=app.config["SABLIER_DEFAULT_THEME"])
    refresh_frequency = db.Column(db.String(10), nullable=False, default=app.config["SABLIER_REFRESH_FREQUENCY"])
    show_details = db.Column(db.Boolean, default=True)

    @classmethod
    def get_defaults(cls):
        """Get the current defaults (create if none exist)"""
        defaults = cls.query.first()
        if not defaults:
            defaults = cls()
            db.session.add(defaults)
            db.session.commit()
        return defaults


class SablierService(db.Model):
    """Individual Sablier service configuration"""
    __tablename__ = "SablierService"
    __bind_key__ = "sablier-app-db"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    names = db.Column(db.String(400), nullable=False, default="80")
    display_name = db.Column(db.String(200), nullable=True)
    port = db.Column(db.String(10), nullable=False, default="80")
    session_duration = db.Column(db.String(10), nullable=False, default=app.config["SABLIER_DEFAULT_SESSION_DURATION"])
    theme = db.Column(db.String(50), nullable=False, default=app.config["SABLIER_DEFAULT_THEME"])
    refresh_frequency = db.Column(db.String(10), nullable=False, default=app.config["SABLIER_REFRESH_FREQUENCY"])
    show_details = db.Column(db.Boolean, nullable=False, default=app.config["SABLIER_REFRESH_FREQUENCY"])
    enabled = db.Column(db.Boolean, default=True)

    @property
    def display_name_or_name(self) -> str:
        """Return display_name if set, otherwise use name"""
        return self.display_name or self.name.title()


def export_sablier_config_to_yaml() -> str:
    """
    Export all enabled Sablier services to Traefik dynamic YAML format
    Returns the YAML string
    """
    defaults = SablierDefaults.get_defaults()
    services = SablierService.query.filter_by(enabled=True).all()
    
    config = {
        "http": {
            "middlewares": {},
            "services": {},
            "routers": {}
        }
    }
    
    for service in services:
        service_name = service.name
        dependency_names = service.names.split(",")
        names = ",".join([s.strip() for s in [service_name, *dependency_names] if len(s)]).strip(",")
        # Create middleware
        middleware_name = f"{service_name}-autostart"
        config["http"]["middlewares"][middleware_name] = {
            "plugin": {
                "sablier": {
                    "sablierUrl": defaults.sablier_url,
                    "names": names,
                    "sessionDuration": service.session_duration,
                    "dynamic": {
                        "displayName": service.display_name_or_name,
                        "showDetails": service.show_details,
                        "theme": service.theme,
                        "refreshFrequency": service.refresh_frequency
                    }
                }
            }
        }
        
        # Create service
        config["http"]["services"][service_name] = {
            "loadBalancer": {
                "servers": [
                    {"url": f"http://{service_name}:{service.port}/"}
                ]
            }
        }
        
        # Create router
        router_name = f"{service_name}-dynamic"
        config["http"]["routers"][router_name] = {
            "rule": f"Host(`{service_name}.{defaults.domain}`)",
            "entryPoints": ["https"],
            "service": service_name,
            "middlewares": [middleware_name]
        }
    
    return yaml.dump(config, default_flow_style=False, sort_keys=False)


def save_sablier_config_to_file(filename="/dynamic.yml") -> bool:
    """
    Export Sablier configuration and save to file
    Returns True if successful, False otherwise
    """
    try:
        yaml_content = export_sablier_config_to_yaml()
        with open(filename, 'w') as f:
            f.write(yaml_content)
        return True
    except Exception as e:
        print(f"Error saving config to {filename}: {e}")
        return False


def create_service(name, port="8080", display_name=None) -> SablierService:
    """Create a new Sablier service using current defaults"""
    defaults = SablierDefaults.get_defaults()
    service = SablierService(
        name=name,
        port=port,
        display_name=display_name,
        session_duration=defaults.session_duration,
        theme=defaults.theme,
        refresh_frequency=defaults.refresh_frequency,
        show_details=defaults.show_details
    )
    db.session.add(service)
    db.session.commit()
    return service


def update_defaults(**kwargs) -> SablierDefaults:
    """Update default configuration"""
    defaults = SablierDefaults.get_defaults()
    for key, value in kwargs.items():
        if hasattr(defaults, key):
            setattr(defaults, key, value)
    defaults.date_modified = datetime.datetime.utcnow()
    db.session.commit()
    return defaults


def get_permission_from_groups(groups:list[str]) -> int:
    """Assigns the highest permission level from group memberships"""
    return max([PERMISSION_ENUM._LOOKUP.get(grp.strip(), 0) for grp in groups], default=0)


def user_loader(user_id:int|str) -> User:
    return User.query.get(int(user_id))


def init_db(app) -> None:
    with app.app_context():
        logging.info("Initializing db...")
        db.create_all(bind_key="sablier-app-db")
        # Check if secret key exists in database, generate one if necessary
        # This key is used to maintain user sessions across application restarts
        # It is also used to reduce the chance of impersonation attacks
        secret_key = SecretKey.query.get(1)
        if secret_key is None:
            key_value = ''.join([rand_choice(ascii_lowercase) for _ in range(24)])
            secret_key = SecretKey(id=1, key=str(key_value))
            db.session.add(secret_key)
            db.session.commit()
        key_value = secret_key.key
        app.secret_key = key_value
        # Do the same as described above for flask wtf forms CSRF protection 
        wtf_secret_key = SecretKey.query.get(2)
        if wtf_secret_key is None:
            wtf_key_value = ''.join([rand_choice(ascii_lowercase) for _ in range(24)])
            wtf_secret_key = SecretKey(id=2, key=wtf_key_value)
            db.session.add(wtf_secret_key)
            db.session.commit()
        wtf_key_value = wtf_secret_key.key
        app.config["WTF_CSRF_SECRET_KEY"] = wtf_key_value
        if not User.query.get(1):
            logging.info("Creating default user with id=1")
            user = User(id=1, name="admin", permission_integer=PERMISSION_ENUM.ADMIN)
            db.session.add(user)
            db.session.commit()
        db.session.commit()