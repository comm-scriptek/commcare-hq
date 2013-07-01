import os
import sys
import django.core.handlers.wsgi

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['CUSTOMSETTINGS'] = 'demo'

# first set the root directory on the path 
current_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
parent_dir = '/'.join(current_dir.split('/')[:-1])
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# then set the rest of the path
from settingshelper import set_path
set_path()

application = django.core.handlers.wsgi.WSGIHandler()