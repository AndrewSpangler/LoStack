import datetime
import logging
import yaml
from flask import current_app
from flask_login import UserMixin
from random import choice as random_choice
from string import ascii_lowercase
from werkzeug.datastructures import ImmutableDict

def _init_db(app):
    db = app.db

    class PERMISSION_ENUM:
        _NAMES = {
            (EVERYBODY := 1) : "everybody",
            (USER := 5)     : "users",
            (ADMIN := 10)   : "admins",
            (OWNER := 15)   : "owners",
            (NOACCESS := 99): "NOACCESS"
        } 
        _LOOKUP = {v:k for k,v in _NAMES.items()}


    class User(UserMixin, db.Model):
        """User object with flask_login UserMixin"""
        __tablename__ = "User"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        # Permission integer, calculated from user groups
        permission_integer = db.Column(db.Integer, default=PERMISSION_ENUM.USER)
        # User primary name
        name = db.Column(db.String(100), unique=True, nullable=False)
        # Date user was added to LoStack db
        date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
        # Selected UI themes
        theme = db.Column(db.String(100), nullable=False, default="default")
        # Selected Editor Theme
        editor_theme = db.Column(db.String(100), nullable=False, default="default")
        
        @property
        def is_admin(self) -> bool:
            return self.permission_integer >= PERMISSION_ENUM.ADMIN


    class SecretKey(db.Model):
        """Table to store Flask and FlaskWTF secret keys"""
        __tablename__ = "SecretKey"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        key = db.Column(db.String(24), nullable=False)


    class LoStackDefaults(db.Model):
        """Default configuration for LoStack package entry"""
        __tablename__ = "LoStackDefaults"
        __bind_key__ = "lostack-db"
        
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


    class PackageEntry(db.Model):
        """Individual installed Package configuration"""
        __tablename__ = "PackageEntry"
        __bind_key__ = "lostack-db"
        id = db.Column(db.Integer, primary_key=True)
        # Package name, must be uniqe for searchability
        name = db.Column(db.String(100), unique=True, nullable=False)
        # List of docker container names to up / down
        service_names = db.Column(db.String(400), nullable=True, default="")
        # What internal port Traefik should connect to
        port = db.Column(db.String(10), nullable=False, default="80")
        # How long the sablier session should last without inactivity
        session_duration = db.Column(db.String(10), nullable=False, default=app.config["SABLIER_DEFAULT_SESSION_DURATION"])
        # What name to show on the sablier loading screen
        display_name = db.Column(db.String(200), nullable=True)
        # Sablier loading theme
        theme = db.Column(db.String(50), nullable=False, default=app.config["SABLIER_DEFAULT_THEME"])
        # How often sablier loading screen retries connections
        refresh_frequency = db.Column(db.String(10), nullable=False, default=app.config["SABLIER_REFRESH_FREQUENCY"])
        # Show container details on Sablier loading screen
        show_details = db.Column(db.Boolean, nullable=False, default=app.config["SABLIER_REFRESH_FREQUENCY"])
        # Not used anymore, kept for future
        automatic = db.Column(db.Boolean, nullable=False, default=False)
        # If in main docker compose
        core_service = db.Column(db.Boolean, nullable=False, default=False)
        # Enables Traefik Route
        enabled = db.Column(db.Boolean, nullable=False, default=True)
        # Enables LoStack forward-auth for role checking
        lostack_middleware_enabled = db.Column(db.Boolean, nullable=False, default=True)
        # Enables AutoStart middleware
        sablier_middleware_enabled = db.Column(db.Boolean, nullable=False, default=True)
        # Groups allowed to access end service
        access_groups = db.Column(db.String(400), nullable=False, default=app.config["ADMIN_GROUP"])
        # If service should be mounted to ${DOMAINNAME} - onle one service should have this 
        mount_to_root = db.Column(db.Boolean, nullable=False, default=False)
        # Enable automatic container update
        lostack_autoupdate_enabled = db.Column(db.Boolean, nullable=False, default=True)
        @property
        def display_name_or_name(self) -> str:
            """Return display_name if set, otherwise use name"""
            return self.display_name or self.name.title()

        @property
        def docker_services(self) -> list[str]:
            return [n.strip() for n in self.service_names.split(",") if n.strip()]
        
        @property
        def allowed_groups(self) -> list[str]:
            return [g.strip() for g in self.access_groups.split(",") if g.strip()]


    def export_sablier_config_to_yaml() -> str:
        """
        Export all enabled Sablier services to Traefik dynamic YAML format
        Returns the YAML string
        """
        defaults = current_app.models.LoStackDefaults.get_defaults()

        # Get all enabled services
        services = current_app.models.PackageEntry.query.filter_by(enabled=True).all()
        
        config = {
            "http": {
                "middlewares": {},
                "services": {},
                "routers": {}
            }
        }
        
        for service in services:
            service_name = service.name
            names = [s.strip() for s in [service_name, *service.service_names.split(",")]]
            names = [s for s in set(names) if s]
            names = ",".join(names).strip(",")

            # Create middleware
            if service.sablier_middleware_enabled:
                sablier_middleware_name = f"{service_name}-autostart"
                config["http"]["middlewares"][sablier_middleware_name] = {
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
            
            # Create Traefik service
            config["http"]["services"][service_name] = {
                "loadBalancer": {
                    "servers": [
                        {"url": f"http://{service_name}:{service.port}/"}
                    ]
                }
            }
            
            router_conf = {
                "rule": f"Host(`{service_name}.{defaults.domain}`)",
                "entryPoints": ["https"],
                "service": service_name,
                "middlewares": []
            }

            if service.mount_to_root:
                router_conf["rule"] = f"Host(`{defaults.domain}`)"

            if service.sablier_middleware_enabled:
                # Create Traefik router
                router_name = f"{service_name}-lostack-autostart"
                router_conf["middlewares"].append(sablier_middleware_name)
            else:
                router_name = f"{service_name}-lostack"
                
            if service.lostack_middleware_enabled:
                router_conf["middlewares"].append("lostack-auth@docker")
            
            config["http"]["routers"][router_name] = router_conf
        
        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    def save_traefik_config(filename="/dynamic.yml") -> bool:
        """
        Export Traefik configuration and save to file
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

    def update_defaults(**kwargs) -> LoStackDefaults:
        """Update default configuration"""
        defaults = LoStackDefaults.get_defaults()
        for key, value in kwargs.items():
            if hasattr(defaults, key):
                setattr(defaults, key, value)
        defaults.date_modified = datetime.datetime.utcnow()
        db.session.commit()
        return defaults

    def get_permission_from_groups(groups:list[str]) -> int:
        """Assigns the highest permission level from group memberships"""
        return max([PERMISSION_ENUM._LOOKUP.get(grp.strip(), 0) for grp in groups], default=0)

    logging.info("Initializing db...")
    db.create_all(bind_key="lostack-db")
    # Check if secret key exists in database, generate one if necessary
    # This key is used to maintain user sessions across application restarts
    # It is also used to reduce the chance of impersonation attacks
    secret_key = SecretKey.query.get(1)
    if secret_key is None:
        key_value = ''.join([random_choice(ascii_lowercase) for _ in range(24)])
        secret_key = SecretKey(id=1, key=str(key_value))
        db.session.add(secret_key)
        db.session.commit()
    key_value = secret_key.key
    app.secret_key = key_value
    # Do the same as described above for flask wtf forms CSRF protection 
    wtf_secret_key = SecretKey.query.get(2)
    if wtf_secret_key is None:
        wtf_key_value = ''.join([random_choice(ascii_lowercase) for _ in range(24)])
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
    app.models = ImmutableDict()
    for obj in (
        User,
        # SecretKey,
        LoStackDefaults,
        PackageEntry,
        PERMISSION_ENUM,            
        export_sablier_config_to_yaml,
        get_permission_from_groups,
        save_traefik_config,
        update_defaults
    ):
        setattr(app.models, obj.__name__, obj)

def init_db(app):
    with app.app_context():
        _init_db(app)