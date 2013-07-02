#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import sys, os
import importlib

from django.core.management import execute_manager

filedir = os.path.dirname(__file__)

from settingshelper import set_path
set_path()

# This code is redundant (see settings/__init__.py) but I've left it
# in for clarity. settings/__init__.py is only there so that the
# legacy code in the submodules functions correctly.
try:
    # Make sure our settings module is the module specified
    settings = importlib.import_module(os.environ['DJANGO_SETTINGS_MODULE'])
except (ImportError, KeyError):
    import sys
    sys.stderr.write("DJANGO_SETTINGS_MODULE not set or not importable - it should be something like 'settings.production'")
    sys.exit(1)


if __name__ == "__main__":
    # proxy for whether we're running gunicorn with -k gevent
    if "gevent" in sys.argv:
        from restkit.session import set_session; set_session("gevent")
        from gevent.monkey import patch_all; patch_all()
    execute_manager(settings)
