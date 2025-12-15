#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        msg = (
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        )
        raise ImportError(msg) from exc

    # This allows easy placement of apps within the interior seedling directory.
    current_path = Path(__file__).parent
    sys.path.append(str(current_path / "demo"))

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
