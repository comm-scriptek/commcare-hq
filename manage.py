#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from django.core.management import execute_manager
import sys, os

filedir = os.path.dirname(__file__)

from settingshelper import set_path
set_path()

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    # proxy for whether we're running gunicorn with -k gevent
    if "gevent" in sys.argv:
        from restkit.session import set_session; set_session("gevent")
        from gevent.monkey import patch_all; patch_all()
    execute_manager(settings)
