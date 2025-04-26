import logging

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
            "stream": "ext://sys.stdout"
        },
    },
    "loggers": {
        "services": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO"
    }
} 