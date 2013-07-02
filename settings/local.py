import os
from settings.base import *

####### Database config. This assumes Postgres ####### 

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'scriptek_commcare',
        'USER': 'django',
        'PASSWORD': 'django',
        'HOST': 'localhost',
        'PORT': '5432'
    }
}

### Reporting database
SQL_REPORTING_DATABASE_URL = "postgresql://django:django@localhost:5432/commcarehq_reporting"

####### Couch Config ######
COUCH_HTTPS = False # recommended production value is True if enabling https
COUCH_SERVER_ROOT = '127.0.0.1:5984' #6984 for https couch
COUCH_USERNAME = 'admin'
COUCH_PASSWORD = 'ei0pieRu'
COUCH_DATABASE_NAME = 'scriptek_commcare'

####### # Email setup ########
# email settings: these ones are the custom hq ones
EMAIL_LOGIN = "mct.cchq@gmail.com"
EMAIL_PASSWORD = "J9krv5MP"
EMAIL_SMTP_HOST = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

# Print emails to console so there is no danger of spamming, but you can still get registration URLs
EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'

ADMINS = (('HQ Dev Team', 'commcarehq-dev+www-notifications@dimagi.com'),)
BUG_REPORT_RECIPIENTS = ['commcarehq-support@dimagi.com']
NEW_DOMAIN_RECIPIENTS = ['commcarehq-dev+newdomain@dimagi.com']
EXCHANGE_NOTIFICATION_RECIPIENTS = ['commcarehq-dev+exchange@dimagi.com']

SERVER_EMAIL = 'commcarehq-noreply@dimagi.com' #the physical server emailing - differentiate if needed
DEFAULT_FROM_EMAIL = 'commcarehq-noreply@dimagi.com'
SUPPORT_EMAIL = "commcarehq-support@dimagi.com"
EMAIL_SUBJECT_PREFIX = '[commcarehq] '

####### Log/debug setup ########

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# log directories must exist and be writeable!
DJANGO_LOG_FILE = "/tmp/commcare-hq.django.log"
LOG_FILE = "/tmp/commcare-hq.log"

SEND_BROKEN_LINK_EMAILS = True
CELERY_SEND_TASK_ERROR_EMAILS = True

####### Bitly ########

BITLY_LOGIN = 'mctcchq '
BITLY_APIKEY = 'PM5vrk9J'


####### Jar signing config ########

_ROOT_DIR  = os.path.dirname(os.path.abspath(__file__))
JAR_SIGN = dict(
    jad_tool = os.path.join(_ROOT_DIR, "corehq", "apps", "app_manager", "JadTool.jar"),
    key_store = os.path.join(os.path.dirname(os.path.dirname(_ROOT_DIR)), "DimagiKeyStore"),
    key_alias = "javarosakey",
    store_pass = "*******",
    key_pass = "*******",
)

####### SMS Config ########

# Mach

SMS_GATEWAY_URL = "http://gw1.promessaging.com/sms.php"
SMS_GATEWAY_PARAMS = "id=******&pw=******&dnr=%(phone_number)s&msg=%(message)s&snr=DIMAGI"

# Unicel
UNICEL_CONFIG = {"username": "Dimagi",
                 "password": "******",
                 "sender": "Promo" }

####### Domain sync / de-id ########

DOMAIN_SYNCS = { 
    "domain_name": { 
        "target": "target_db_name",
        "transform": "corehq.apps.domainsync.transforms.deidentify_domain" 
    }
}
DOMAIN_SYNC_APP_NAME_MAP = { "app_name": "new_app_name" }

####### Touchforms config - for CloudCare #######

XFORMS_PLAYER_URL = 'http://127.0.0.1:4444'

# email and password for an admin django user, such as one created with
# ./manage.py bootstrap <project-name> <email> <password>
TOUCHFORMS_API_USER = 'admin@example.com'
TOUCHFORMS_API_PASSWORD = 'password'


####### Misc / HQ-specific Config ########

DEFAULT_PROTOCOL = "http" # or https
OVERRIDE_LOCATION="https://www.commcarehq.org"

#Set your analytics IDs here for GA and pingdom RUM
ANALYTICS_IDS = {
    'GOOGLE_ANALYTICS_ID': '*******',
    'PINGDOM_ID': '*****'
}

AXES_LOCK_OUT_AT_FAILURE = False
LUCENE_ENABLED = True

INSECURE_URL_BASE = "http://submit.commcarehq.org"

PREVIEWER_RE = r'^.*@dimagi\.com$'
GMAPS_API_KEY = '******'
FORMTRANSLATE_TIMEOUT = 5
LOCAL_APPS = (
#    'django_coverage', # Adds `python manage.py test_coverage` (settings below)
#    'debug_toolbar',   # Adds a retractable panel to every page giving profiling & debugging info
#    'couchdebugpanel', # Adds couch info to said toolbar
#    'devserver',       # Adds improved dev server that also prints SQL on the console (for AJAX, etc, when you cannot use debug_toolbar)
#    'django_cpserver', # Another choice for a replacement server
#    'dimagi.utils'
    'scriptek',
)

# list of domains to enable ADM reporting on
ADM_ENABLED_PROJECTS = []

# prod settings
SOIL_DEFAULT_CACHE = "redis"
SOIL_BACKEND = "soil.CachedDownload"

# reports cache
REPORT_CACHE = 'default' # or e.g. 'redis'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'localhost:11211',
    },
    'redis': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': 'localhost:6379',
        'OPTIONS': {},
    },
}

ELASTICSEARCH_HOST = 'localhost' #on both a local and a distributed environment this should be
# localhost
ELASTICSEARCH_PORT = 9200

# our production logstash aggregation
LOGSTASH_DEVICELOG_PORT = 10777
LOGSTASH_COUCHLOG_PORT = 10888
LOGSTASH_AUDITCARE_PORT = 10999
LOGSTASH_HOST = 'localhost'

LOCAL_PILLOWTOPS = []

####### django-coverage config ########

COVERAGE_REPORT_HTML_OUTPUT_DIR='coverage-html'
COVERAGE_MODULE_EXCLUDES= ['tests$', 'settings$', 'urls$', 'locale$',
                           'common.views.test', '^django', 'management', 'migrations',
                           '^south', '^djcelery', '^debug_toolbar', '^rosetta']

####### Selenium tests config ########

SELENIUM_SETUP = {
    # Firefox, Chrome, Ie, or Remote
    'BROWSER': 'Chrome',
    
    # Necessary if using Remote selenium driver
    'REMOTE_URL': None,
    
    # If not using Remote, allows you to open browsers in a hidden virtual X Server
    'USE_XVFB': True,
    'XVFB_DISPLAY_SIZE': (1024, 768),
}

SELENIUM_USERS = {
    # 'WEB_USER' is optional; if not set, some tests that want a web user will
    # try to use ADMIN instead
    'ADMIN': {
        'USERNAME': 'foo@example.com',
        'PASSWORD': 'password',
        'URL': 'http://localhost:8000',
        'PROJECT': 'project_name',
        'IS_SUPERUSER': False
    },

    'WEB_USER': {
        'USERNAME': 'foo@example.com',
        'PASSWORD': 'password',
        'URL': 'http://localhost:8000',
        'PROJECT': 'mike',
        'IS_SUPERUSER': False
    },

    'MOBILE_WORKER': {
        'USERNAME': 'user@project_name.commcarehq.org',
        'PASSWORD': 'password',
        'URL': 'http://localhost:8000'
    }
}

SELENIUM_APP_SETTINGS = {
    'reports': {
        'MAX_PRELOAD_TIME': 20,
        'MAX_LOAD_TIME': 30,
    },
}

INTERNAL_DATA = {
    "business_unit": [],
    "product": ["CommCare", "CommConnect", "CommTrack", "RapidSMS", "Custom"],
    "services": [],
    "account_types": [],
    "initiatives": [],
    "contract_type": [],
    "area": [
        {
        "name": "Health",
        "sub_areas": ["Maternal, Newborn, & Child Health", "Family Planning", "HIV/AIDS"]
        },
        {
        "name": "Other",
        "sub_areas": ["Emergency Response"]
        },
    ],
    "country": ["Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua & Deps", "Argentina", "Armenia",
                "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus",
                "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia Herzegovina", "Botswana", "Brazil",
                "Brunei", "Bulgaria", "Burkina", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde",
                "Central African Rep", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo",
                "Congo {Democratic Rep}", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark",
                "Djibouti", "Dominica", "Dominican Republic", "East Timor", "Ecuador", "Egypt", "El Salvador",
                "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia",
                "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
                "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland {Republic}",
                "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
                "Korea North", "Korea South", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
                "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Macedonia", "Madagascar", "Malawi",
                "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico",
                "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar, {Burma}",
                "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "Norway",
                "Oman", "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland",
                "Portugal", "Qatar", "Romania", "Russian Federation", "Rwanda", "St Kitts & Nevis", "St Lucia",
                "Saint Vincent & the Grenadines", "Samoa", "San Marino", "Sao Tome & Principe", "Saudi Arabia",
                "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia",
                "Solomon Islands", "Somalia", "South Africa", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname",
                "Swaziland", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Togo",
                "Tonga", "Trinidad & Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine",
                "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan", "Vanuatu",
                "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"]
}

# The remainder of this file used to be in the settings.py file rather
# than local settings but local settings were imported in the middle
# of the settings file (pretty daft) so I've moved the rest of the
# file here.


if DEBUG:
    try:
        import luna
        del luna
    except ImportError:
        pass
    else:
        INSTALLED_APPS = INSTALLED_APPS + (
            'luna',
        )

if not DEBUG:
    TEMPLATE_LOADERS = [
        ('django.template.loaders.cached.Loader', TEMPLATE_LOADERS),
    ]

####### South Settings #######
#SKIP_SOUTH_TESTS=True
#SOUTH_TESTS_MIGRATE=False

####### Couch Forms & Couch DB Kit Settings #######
from settingshelper import get_dynamic_db_settings, make_couchdb_tuple

_dynamic_db_settings = get_dynamic_db_settings(COUCH_SERVER_ROOT, COUCH_USERNAME, COUCH_PASSWORD,
                                               COUCH_DATABASE_NAME, INSTALLED_APPS,
                                               use_https=COUCH_HTTPS)

# create local server and database configs
COUCH_SERVER = _dynamic_db_settings["COUCH_SERVER"]
COUCH_DATABASE = _dynamic_db_settings["COUCH_DATABASE"]

# other urls that depend on the server
XFORMS_POST_URL = _dynamic_db_settings["XFORMS_POST_URL"]

COUCHDB_APPS = [
    'adm',
    'announcements',
    'api',
    'app_manager',
    'appstore',
    'orgs',
    'auditcare',
    'builds',
    'case',
    'cleanup',
    'cloudcare',
    'commtrack',
    'couch',
    # This is necessary for abstract classes in dimagi.utils.couch.undo; otherwise breaks tests
    'couchdbkit_aggregate',
    'couchforms',
    'couchexport',
    'hqadmin',
    'domain',
    'facilities',
    'fluff_filter',
    'forms',
    'fixtures',
    'groups',
    'hqcase',
    'hqmedia',
    'importer',
    'indicators',
    'locations',
    'migration',
    'mobile_auth',
    'phone',
    'receiverwrapper',
    'reminders',
    'prescriptions',
    'reports',
    'sms',
    'smsforms',
    'translations',
    'users',
    'utils',  # dimagi-utils
    'formplayer',
    'phonelog',
    'registration',
    'hutch',
    'hqbilling',
    'couchlog',

    # custom reports
    'benin',
    'dca',
    'hsph',
    'mvp',
    'pathfinder',
    'pathindia',
    'pact',
    'psi',
]

COUCHDB_DATABASES = [make_couchdb_tuple(app_label, COUCH_DATABASE) for app_label in COUCHDB_APPS]

COUCHDB_DATABASES += [
    ('bihar', COUCH_DATABASE + '__fluff-bihar'),
    ('fluff', COUCH_DATABASE + '__fluff-bihar'),
]

INSTALLED_APPS = LOCAL_APPS + INSTALLED_APPS

MIDDLEWARE_CLASSES += LOCAL_MIDDLEWARE_CLASSES

# these are the official django settings
# which really we should be using over the custom ones
EMAIL_HOST = EMAIL_SMTP_HOST
EMAIL_PORT = EMAIL_SMTP_PORT
EMAIL_HOST_USER = EMAIL_LOGIN
EMAIL_HOST_PASSWORD = EMAIL_PASSWORD
EMAIL_USE_TLS = True

NO_HTML_EMAIL_MESSAGE = """
This is an email from CommCare HQ. You're seeing this message because your
email client chose to display the plaintext version of an email that CommCare
HQ can only provide in HTML.  Please set your email client to view this email
in HTML or read this email in a client that supports HTML email.

Thanks,
The CommCare HQ Team"""


MESSAGE_TAGS = {
    messages.INFO: 'alert-info',
    messages.DEBUG: '',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-error',
    messages.ERROR: 'alert-error',
}

COMMCARE_USER_TERM = "Mobile Worker"
WEB_USER_TERM = "Web User"

DEFAULT_CURRENCY = "USD"

SMS_HANDLERS = [
    'corehq.apps.sms.api.forwarding_handler',
    'corehq.apps.commtrack.sms.handle',
    'corehq.apps.sms.api.structured_sms_handler',
    'corehq.apps.sms.api.form_session_handler',
    'corehq.apps.sms.api.fallback_handler',
]

# mapping of phone number prefix (including country code) to a registered
# outbound sms backend to use for that set of numbers. the backend can be:
# * the ID of a MobileBackend couch doc ("new-style" backends), or
# * the python path of a backend module ("old-style" backends)
# NOTE: Going forward, do not add backends here, add them in localsettings
if "SMS_BACKENDS" not in globals():
    SMS_BACKENDS = {}

SMS_BACKENDS[''] = 'MOBILE_BACKEND_MACH' # default backend
SMS_BACKENDS['91'] = 'MOBILE_BACKEND_UNICEL' # india
SMS_BACKENDS['999'] = 'MOBILE_BACKEND_TEST' # +999 is an unused country code

SELENIUM_APP_SETTING_DEFAULTS = {
    'cloudcare': {
        # over-generous defaults for now
        'OPEN_FORM_WAIT_TIME': 20,
        'SUBMIT_FORM_WAIT_TIME': 20
    },

    'reports': {
        'MAX_PRELOAD_TIME': 20,
        'MAX_LOAD_TIME': 30,
    },
}

INDICATOR_CONFIG = {
    "mvp-sauri": ['mvp_indicators'],
    "mvp-potou": ['mvp_indicators'],
}

CASE_WRAPPER = 'corehq.apps.hqcase.utils.get_case_wrapper'

PILLOWTOPS = [
                 'corehq.pillows.case.CasePillow',
                 'corehq.pillows.fullcase.FullCasePillow',
                 'corehq.pillows.xform.XFormPillow',
                 'corehq.pillows.fullxform.FullXFormPillow',
                 'corehq.pillows.domain.DomainPillow',
                 'corehq.pillows.user.UserPillow',
                 'corehq.pillows.exchange.ExchangePillow',
                 'corehq.pillows.commtrack.ConsumptionRatePillow',

                 # fluff
                 'bihar.models.CareBiharFluffPillow',
             ] + LOCAL_PILLOWTOPS

#Custom workflow for indexing xform data beyond the standard properties
XFORM_PILLOW_HANDLERS = ['pact.pillowhandler.PactHandler', ]

#Custom fully indexed domains for FullCase index/pillowtop
# Adding a domain will not automatically index that domain's existing cases
ES_CASE_FULL_INDEX_DOMAINS = [
    'pact', 
    'hsph', 
    'care-bihar', 
    'hsph-dev', 
    'hsph-betterbirth-pilot-2',
]

REMOTE_APP_NAMESPACE = "%(domain)s.commcarehq.org"

# mapping of domains to modules for those that aren't identical
# a DOMAIN_MODULE_CONFIG doc present in your couchdb can override individual
# items.
DOMAIN_MODULE_MAP = {
    'a5288-test': 'a5288',
    'a5288-study': 'a5288',
    'care-bihar': 'bihar',
    'dca-malawi': 'dca',
    'eagles-fahu': 'dca',
    'hsph-dev': 'hsph',
    'hsph-betterbirth-pilot-2': 'hsph',
    'mvp-potou': 'mvp',
    'mvp-sauri': 'mvp',
    'mvp-bonsaaso': 'mvp',
    'mvp-ruhiira': 'mvp',
    'mvp-mwandama': 'mvp',
    'mvp-sada': 'mvp',
    'psi-unicef': 'psi',
}
