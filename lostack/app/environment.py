from app.extensions.common.label_extractor import LabelExtractor as labext 


LOG_CONFIG = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s \
            %(name)s %(threadName)s in %(module)s: %(message)s",
        }
    },
    "handlers": {
        "wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "default",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "loggers": {
        "__main__": {
            "level": "INFO",
            "handlers": ["wsgi", "console"],
            "propagate": False,
        },
        "werkzeug": {
            "level": "INFO",
            "handlers": ["wsgi", "console"],
            "propagate": False,
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["wsgi", "console"]
    }
}

ENV_DEFAULTS = {
    "AUTHOR" : "Andrew Spangler",
    "APPLICATION_NAME" : "LoStack Admin",
    "APPLICATION_DESCRIPTION" : "Welcome to LoStack",
    "APPLICATION_DETAILS" : "Easily configure Traefik, GetHomePage, \
    and Sablier and install prebuilt services with a few clicks.",
    "DEPOT_URL" : "https://github.com/AndrewSpangler/LoStack-Depot.git",
    "DEPOT_BRANCH"                  : "main",
    "DEPOT_DIR"                     : "/appdata/LoStack-Depot",
    "DEPOT_DIR_DEV"                 : "/docker/LoStack-Depot",
    "DEPOT_DEV_MODE"                : "false",
    "TRUSTED_PROXY_IPS"             : "172.*",
    "DOMAIN_NAME"                   : "lostack.internal",
    "SABLIER_URL"                   : "http://sablier:10000",
    "SABLIER_DEFAULT_SESSION_DURATION": "5m",
    "SABLIER_DEFAULT_THEME"         : "ghost",
    "SABLIER_REFRESH_FREQUENCY"     : "3s",
    "DB_HOST"                       : "", # Required External
    "DB_PORT"                       : "", # Required External
    "DB_USER"                       : "", # Required External
    "DB_PASSWORD"                   : "", # Required External
    "DB_NAME"                       : "", # Required External
    "SQLALCHEMY_POOL_SIZE"          : 24,
    "SQLALCHEMY_MAX_OVERFLOW"       : 5,
    "SQLALCHEMY_POOL_RECYCLE"       : 3600,
    "SQLALCHEMY_TRACK_MODIFICATIONS": "false",
    "DEBUG"                         : "false",
    "TIMEZONE"                      : "US/Pacific",
    "LOG_CONFIG"                    : LOG_CONFIG,
    "ADMIN_GROUP"                   : "admins",
    "GROUPS_HEADER"                 : "Remote-Groups",
    "USERNAME_HEADER"               : "Remote-User",
    "FORWARDED_FOR_HEADER"          : "X-Forwarded-For",
    "FORWARDED_HOST_HEADER"         : "X-Forwarded-Host",
    "FORWARDED_METHOD_HEADER"       : "X-Forwarded-Method",
    "FORWARDED_URI_HEADER"          : "X-Forwarded-Uri"
}

ENV_PARSING = {
    "DEPOT_DEV_MODE" : labext.parse_boolean,
    "SQLALCHEMY_POOL_SIZE" : int,
    "SQLALCHEMY_MAX_OVERFLOW" : int,
    "SQLALCHEMY_POOL_RECYCLE" : int,
    "SQLALCHEMY_TRACK_MODIFICATIONS" : labext.parse_boolean,
    "DEBUG" : labext.parse_boolean
}

ENV_NON_REQUIRED  = [
    "AUTHOR", "APPLICATION_NAME", "APPLICATION_DETAILS"
]