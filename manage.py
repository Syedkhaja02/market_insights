#!/usr/bin/env python
"""Django’s command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path

import environ  # pip install django-environ


def main() -> None:
    """Run administrative tasks."""
    #
    # 1. Load variables from .env if the file exists
    #
    env = environ.Env()
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        environ.Env.read_env(env_path)

    #
    # 2. Point Django at the settings module
    #
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "market_insights.settings")

    #
    # 3. Hand off to Django’s CLI wrapper
    #
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed and that you "
            "have activated the correct virtual environment."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
