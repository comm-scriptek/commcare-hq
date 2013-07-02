import os
import importlib
try:
    # Do a dynamic 'from DJANGO_SETTINGS_MODULE import *'
    settings = importlib.import_module(os.environ['DJANGO_SETTINGS_MODULE'])
    for v in dir(settings):
        if v.startswith("__"): continue
        globals()[v] = getattr(settings, v)
except ImportError, KeyError:
    # default to the production settings if environment variable not set or improperly specified
    from production import *
