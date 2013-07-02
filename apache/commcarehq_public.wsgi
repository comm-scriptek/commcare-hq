import os
import sys
import django.core.handlers.wsgi

# DJANGO_SETTINGS_MODULE must be set in the apache configuration

# first set the root directory on the path 
parent_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if parent_dir not in sys.path:
    # Must go on the front because of nasty stuff in submodules
    sys.path.insert(0,parent_dir)

# then set the rest of the path
from settingshelper import set_path
set_path()

django_application = django.core.handlers.wsgi.WSGIHandler()

# We need to inject the DJANGO_SETTINGS_MODULE environment variable
# set by apache into our application's environment each time apache
# calls it.

def my_application(environ, start_response):
    os.environ['DJANGO_SETTINGS_MODULE'] = environ['DJANGO_SETTINGS_MODULE']
    return django_application(environ, start_response)

application = my_application
