import os
import sys

def get_server_url(http_method, server_root, username, password):
    if username and password:
        return "%(http_method)s://%(user)s:%(pass)s@%(server)s" % \
            {
                "http_method": http_method,
                "user": username,
             "pass": password, 
             "server": server_root }
    else:
        return "%(http_method)s://%(server)s" % {"http_method": http_method, "server": server_root }

def get_dynamic_db_settings(server_root, username, password, dbname, installed_apps, use_https=False):
    """
    Get dynamic database settings.  Other apps can use this if they want to change
    settings
    """

    http_method = "https" if use_https else "http"
    server_url = get_server_url(http_method, server_root, username, password)
    database = "%(server)s/%(database)s" % {"server": server_url, "database": dbname}
    posturl = "http://%s/%s/_design/couchforms/_update/xform/" % (server_root, dbname)
    return {"COUCH_SERVER":  server_url,
            "COUCH_DATABASE": database,
            "XFORMS_POST_URL": posturl }
            

def get_commit_id():
    # This command is never allowed to fail since it's called in settings
    try:
        import os
        return os.popen("git log --format=%H -1").readlines()[0].strip()
    except Exception:
        return None

def make_couchdb_tuple(app_label, couch_database_url):
    """
    Helper function to generate couchdb tuples for mapping app name to couch database URL.

    In this case, the helper will magically alter the URL for special core libraries.

    Namely, auditcare, and couchlog
    """

    if app_label == 'auditcare' or app_label == 'couchlog':
        return app_label, "%s__%s" % (couch_database_url, app_label)
    else:
        return app_label, couch_database_url

def set_path(site_root=None):
    """
    Set sys path to include all the required submodules.
    """
    if site_root is None:
        # Assume its the current file's directory
        site_root = os.path.dirname(__file__)

    def add_to_path(module_dir):
        addition = os.path.abspath(os.path.join(site_root, module_dir))
        if addition not in sys.path:
            # There are some things in the submodule source that are
            # not in the main modules so the submodules must come at
            # the front of the list to make sure that their modules
            # are found first and in order. This is NOT good.
            sys.path.insert(1, addition)
        
    add_to_path('submodules')

    for d in os.listdir(os.path.join(site_root, 'submodules')):
        if d == "__init__.py" or d == '.' or d == '..':
            continue
        add_to_path(os.path.join('submodules', d))

