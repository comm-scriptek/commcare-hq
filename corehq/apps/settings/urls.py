from django.conf.urls.defaults import *
from corehq.apps.domain.urls import domain_settings
from corehq.apps.cloudcare.urls import settings_urls as cloudcare_settings
from corehq.apps.commtrack.urls import settings_urls as commtrack_settings
from corehq.apps.facilities.urls import settings_urls as facilities_settings
from corehq.apps.locations.urls import settings_urls as location_settings

urlpatterns = patterns('corehq.apps.settings.views',
    url(r'^$', 'account_settings', name='my_account_settings')
)

domain_specific = patterns('',
    url(r'^$', 'corehq.apps.settings.views.default', name="settings_default"),
    (r'^users/', include('corehq.apps.users.urls')),
    (r'^project/', include(domain_settings)),
    (r'^cloudcare/', include(cloudcare_settings)),
    (r'^commtrack/', include(commtrack_settings)),
    (r'^locations/', include(location_settings)),
    (r'^facilities/', include(facilities_settings)),
    url(r'^api/id_mapping/$', 'corehq.apps.settings.views.project_id_mapping', name="project_id_mapping")

)

users_redirect = patterns('corehq.apps.settings.views',
    (r'^$', 'redirect_users'),
    (r'^(?P<old_url>[\w_\\\/\-]+)/$', 'redirect_users'))

domain_redirect = patterns('corehq.apps.settings.views',
    (r'^$', 'redirect_domain_settings'),
    (r'^(?P<old_url>[\w_\\\/\-]+)/$', 'redirect_domain_settings'))

