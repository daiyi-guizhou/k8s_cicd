#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    # Allow env var override for dev/prod settings
    #   DJANGO_SETTINGS_MODULE = k8s_console.settings_dev  → local dev
    #   DJANGO_SETTINGS_MODULE = k8s_console.settings       → K8s pod (default)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "k8s_console.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
