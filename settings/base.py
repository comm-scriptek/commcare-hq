#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from collections import defaultdict

import sys, os
from django.contrib import messages

# odd celery fix
import djcelery;

djcelery.setup_loader()

CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

try:
    UNIT_TESTING = 'test' == sys.argv[1]
except IndexError:
    UNIT_TESTING = False

ADMINS = ()
MANAGERS = ADMINS

# default to the system's timezone settings
TIME_ZONE = "UTC"


# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

LANGUAGES = (
    ('en', 'English'),
    ('fr', 'French'),
    # ('hin', 'Hindi'),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Django i18n searches for translation files (django.po) within this dir
# and then in the locale/ directories of installed apps
LOCALE_PATHS = ()

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

FILEPATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
# media for user uploaded media.  in general this won't be used at all.
MEDIA_ROOT = os.path.join(FILEPATH, 'mediafiles')
STATIC_ROOT = os.path.join(FILEPATH, 'staticfiles')

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder"
)

STATICFILES_DIRS = (
    ('formdesigner', os.path.join(FILEPATH, 'submodules', 'formdesigner')),
)

DJANGO_LOG_FILE = "%s/%s" % (FILEPATH, "commcarehq.django.log")

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.Loader',
    #     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'corehq.middleware.OpenRosaMiddleware',
    'corehq.apps.users.middleware.UsersMiddleware',
    'casexml.apps.phone.middleware.SyncTokenMiddleware',
    'auditcare.middleware.AuditMiddleware',
]

ROOT_URLCONF = "urls"

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.static',
    "corehq.util.context_processors.current_url_name",
    'corehq.util.context_processors.domain',
    "corehq.util.context_processors.base_template", # sticks the base template inside all responses
    "corehq.util.context_processors.analytics_js",
    "corehq.util.context_processors.raven",
]

TEMPLATE_DIRS = [
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
]

DEFAULT_APPS = (
    'corehq.apps.userhack', # this has to be above auth
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages', # don't need this for messages and it's causing some error
    'django.contrib.staticfiles',
    'south',
    'djcelery', # pip install django-celery
    'djtables', # pip install djtables
    #'ghettoq',     # pip install ghettoq
    'djkombu', # pip install django-kombu
    'couchdbkit.ext.django',
    'crispy_forms',
    'django.contrib.markup',
    'gunicorn',
    'raven.contrib.django.raven_compat',
)

CRISPY_TEMPLATE_PACK = 'bootstrap'

HQ_APPS = (
    'django_digest',
    'rosetta',
    'auditcare',
    'djangocouch',
    'djangocouchuser',
    'hqscripts',
    'casexml.apps.case',
    'casexml.apps.phone',
    'corehq.apps.cleanup',
    'corehq.apps.cloudcare',
    'corehq.apps.appstore',
    'corehq.apps.domain',
    'corehq.apps.domainsync',
    'corehq.apps.hqadmin',
    'corehq.apps.hqcase',
    'corehq.apps.hqcouchlog',
    'corehq.apps.hqwebapp',
    'corehq.apps.hqmedia',
    'corehq.apps.locations',
    'corehq.apps.commtrack',
    'couchforms',
    'couchexport',
    'couchlog',
    'dimagi.utils',
    'formtranslate',
    'receiver',
    'langcodes',
    'corehq.apps.adm',
    'corehq.apps.announcements',
    'corehq.apps.crud',
    'corehq.apps.receiverwrapper',
    'corehq.apps.migration',
    'corehq.apps.app_manager',
    'corehq.apps.orgs',
    'corehq.apps.facilities',
    'corehq.apps.fixtures',
    'corehq.apps.importer',
    'corehq.apps.reminders',
    'corehq.apps.prescriptions',
    'corehq.apps.translations',
    'corehq.apps.users',
    'corehq.apps.settings',
    'corehq.apps.ota',
    'corehq.apps.groups',
    'corehq.apps.mobile_auth',
    'corehq.apps.sms',
    'corehq.apps.smsforms',
    'corehq.apps.ivr',
    'corehq.apps.tropo',
    'corehq.apps.kookoo',
    'corehq.apps.sislog',
    'corehq.apps.yo',
    'corehq.apps.registration',
    'corehq.apps.unicel',
    'corehq.apps.reports',
    'corehq.apps.data_interfaces',
    'corehq.apps.builds',
    'corehq.apps.orgs',
    'corehq.apps.api',
    'corehq.apps.indicators',
    'corehq.couchapps',
    'fluff',
    'fluff.fluff_filter',
    'sofabed.forms',
    'soil',
    'corehq.apps.hqsofabed',
    'touchforms.formplayer',
    'hqbilling',
    'phonelog',
    'hutch',
    'loadtest',
    'pillowtop',
    'hqstyle',

    # custom reports
    'a5288',
    'benin',
    'bihar',
    'dca',
    'hsph',
    'mvp',
    'mvp_apps',
    'pathfinder',
    'pathindia',
    'pact',
    'psi',
)

TEST_APPS = ()

INSTALLED_APPS = DEFAULT_APPS + HQ_APPS


# after login, django redirects to this URL
# rather than the default 'accounts/profile'
LOGIN_REDIRECT_URL = '/'


# Default reporting database should be overridden in localsettings.
SQL_REPORTING_DATABASE_URL = "sqlite:////tmp/commcare_reporting_test.db"

REPORT_CACHE = 'default' # or e.g. 'redis'

####### Domain settings  #######

DOMAIN_MAX_REGISTRATION_REQUESTS_PER_DAY = 99
DOMAIN_SELECT_URL = "/domain/select/"
LOGIN_URL = "/accounts/login/"
# If a user tries to access domain admin pages but isn't a domain
# administrator, here's where he/she is redirected
DOMAIN_NOT_ADMIN_REDIRECT_PAGE_NAME = "homepage"

# domain syncs
# e.g.
#               { sourcedomain1: { "domain": targetdomain1,
#                      "transform": path.to.transformfunction1 },
#                 sourcedomain2: {...} }
DOMAIN_SYNCS = {}
# if you want to deidentify app names, put a dictionary in your settings
# of source names to deidentified names
DOMAIN_SYNC_APP_NAME_MAP = {}
DOMAIN_SYNC_DATABASE_NAME = "commcarehq-public"


####### Release Manager App settings  #######
RELEASE_FILE_PATH = os.path.join("data", "builds")

## soil heartbead config ##
SOIL_HEARTBEAT_CACHE_KEY = "django-soil-heartbeat"


####### Shared/Global/UI Settings ######

# restyle some templates
BASE_TEMPLATE = "hqwebapp/base.html"
LOGIN_TEMPLATE = "login_and_password/login.html"
LOGGEDOUT_TEMPLATE = "loggedout.html"

# email settings: these ones are the custom hq ones
EMAIL_LOGIN = "user@domain.com"
EMAIL_PASSWORD = "changeme"
EMAIL_SMTP_HOST = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

# put email addresses here to have them receive bug reports
BUG_REPORT_RECIPIENTS = ()
EXCHANGE_NOTIFICATION_RECIPIENTS = []

SERVER_EMAIL = 'commcarehq-noreply@dimagi.com' #the physical server emailing - differentiate if needed
DEFAULT_FROM_EMAIL = 'commcarehq-noreply@dimagi.com'
SUPPORT_EMAIL = "commcarehq-support@dimagi.com"
EMAIL_SUBJECT_PREFIX = '[commcarehq] '

PAGINATOR_OBJECTS_PER_PAGE = 15
PAGINATOR_MAX_PAGE_LINKS = 5

# OpenRosa Standards
OPENROSA_VERSION = "1.0"

# OTA restore fixture generators
FIXTURE_GENERATORS = [
    "corehq.apps.users.fixturegenerators.user_groups",
    "corehq.apps.fixtures.fixturegenerators.item_lists",
]

GET_URL_BASE = 'dimagi.utils.web.get_url_base'

SMS_GATEWAY_URL = "http://localhost:8001/"
SMS_GATEWAY_PARAMS = "user=my_username&password=my_password&id=%(phone_number)s&text=%(message)s"

# celery
BROKER_URL = 'django://' #default django db based

SKIP_SOUTH_TESTS = True
#AUTH_PROFILE_MODULE = 'users.HqUserProfile'
TEST_RUNNER = 'testrunner.HqTestSuiteRunner'
HQ_ACCOUNT_ROOT = "commcarehq.org" # this is what gets appended to @domain after your accounts

XFORMS_PLAYER_URL = "http://localhost:4444/"  # touchform's setting

####### Couchlog config ######

COUCHLOG_BLUEPRINT_HOME = "%s%s" % (STATIC_URL, "hqwebapp/stylesheets/blueprint/")
COUCHLOG_DATATABLES_LOC = "%s%s" % (
    STATIC_URL, "hqwebapp/js/lib/datatables-1.9/js/jquery.dataTables.min.js")

# These allow HQ to override what shows up in couchlog (add a domain column)
COUCHLOG_TABLE_CONFIG = {"id_column": 0,
                         "archived_column": 1,
                         "date_column": 2,
                         "message_column": 4,
                         "actions_column": 8,
                         "email_column": 9,
                         "no_cols": 10}
COUCHLOG_DISPLAY_COLS = ["id", "archived?", "date", "exception type",
                         "message", "domain", "user", "url", "actions", "report"]
COUCHLOG_RECORD_WRAPPER = "corehq.apps.hqcouchlog.wrapper"
COUCHLOG_DATABASE_NAME = "commcarehq-couchlog"

# couchlog/case search
LUCENE_ENABLED = False

# sofabed
FORMDATA_MODEL = 'hqsofabed.HQFormData'



# unicel sms config
UNICEL_CONFIG = {"username": "Dimagi",
                 "password": "changeme",
                 "sender": "Promo"}

# mach sms config
MACH_CONFIG = {"username": "Dimagi",
               "password": "changeme",
               "service_profile": "changeme"}

#auditcare parameters
AUDIT_MODEL_SAVE = [
    'corehq.apps.app_manager.Application',
    'corehq.apps.app_manager.RemoteApp',
]
AUDIT_VIEWS = [
    'corehq.apps.domain.views.registration_request',
    'corehq.apps.domain.views.registration_confirm',
    'corehq.apps.domain.views.password_change',
    'corehq.apps.domain.views.password_change_done',
    'corehq.apps.reports.views.submit_history',
    'corehq.apps.reports.views.active_cases',
    'corehq.apps.reports.views.submit_history',
    'corehq.apps.reports.views.default',
    'corehq.apps.reports.views.submission_log',
    'corehq.apps.reports.views.form_data',
    'corehq.apps.reports.views.export_data',
    'corehq.apps.reports.views.excel_report_data',
    'corehq.apps.reports.views.daily_submissions',
]

# Don't use google analytics unless overridden in localsettings
ANALYTICS_IDS = {
    'GOOGLE_ANALYTICS_ID': '',
    'PINGDOM_ID': ''
}

# for touchforms maps
GMAPS_API_KEY = "changeme"

# for touchforms authentication
TOUCHFORMS_API_USER = "changeme"
TOUCHFORMS_API_PASSWORD = "changeme"

# import local settings if we find them
LOCAL_APPS = ()
LOCAL_MIDDLEWARE_CLASSES = ()
LOCAL_PILLOWTOPS = []

# our production logstash aggregation
LOGSTASH_DEVICELOG_PORT = 10777
LOGSTASH_COUCHLOG_PORT = 10888
LOGSTASH_AUDITCARE_PORT = 10999
LOGSTASH_HOST = 'localhost'

#on both a single instance or distributed setup this should assume to be localhost
ELASTICSEARCH_HOST = 'localhost'
ELASTICSEARCH_PORT = 9200

#for production this ought to be set to true on your configured couch instance
COUCH_HTTPS = False

# this should be overridden in localsettings
INTERNAL_DATA = defaultdict(list)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(asctime)s %(levelname)s %(message)s'
        },

        'pillowtop': {
            'format': '%(asctime)s %(levelname)s %(module)s %(message)s'
        },
    },
    'handlers': {
        'pillowtop': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'pillowtop'
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': DJANGO_LOG_FILE
        },
        'couchlog': {
            'level': 'WARNING',
            'class': 'couchlog.handlers.CouchHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file', 'couchlog', 'sentry'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'notify': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'celery.task': {
            'handlers': ['console', 'file', 'couchlog'],
            'level': 'INFO',
            'propagate': True
        },
        'pillowtop': {
            'handlers': ['pillowtop'],
            'level': 'ERROR',
            'propagate': False,
        }
    }
}

COUCH_STALE_QUERY='update_after'  # 'ok' for cloudant


MESSAGE_LOG_OPTIONS = {
    "abbreviated_phone_number_domains": ["mustmgh", "mgh-cgh-uganda"],
}

IVR_OUTBOUND_RETRIES = 3
IVR_OUTBOUND_RETRY_INTERVAL = 10


DEFAULT_CURRENCY = "USD"
