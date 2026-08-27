#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env from the repository root (one level above backend/).

    ``override=False`` means real OS environment variables (set by a PaaS,
    Docker secrets, or a shell ``export``) always win over the .env file.
    This makes the same codebase work for both local development and
    production deployments without any code change.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return  # python-dotenv is a dev-only dependency; skip silently in prod

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def main() -> None:
    _load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Install backend/requirements/local.txt first."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
