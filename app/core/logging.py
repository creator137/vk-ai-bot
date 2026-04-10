from __future__ import annotations

import logging.config


def configure_logging(level: str) -> None:
    normalized_level = level.upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": normalized_level,
                }
            },
            "root": {
                "handlers": ["default"],
                "level": normalized_level,
            },
        }
    )

