import sys
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth.views import password_reset
from django.shortcuts import render_to_response
from django.template import RequestContext

#
# After much reading, I discovered that Django matches URLs derived from the environment
# variable PATH_INFO. This is set by your webserver, so any misconfiguration there will
# mess this up. In Apache, the WSGIScriptAliasMatch pulls off the mount point directory,
# and puts everything that follows it into PATH_INFO. Those (mount-point-less) paths are
# what is matched in urlpatterns.
#

# All of these auth functions have custom templates in registration/, with the default names they expect.
#
# Django docs on password reset are weak. See these links instead:
#
# http://streamhacker.com/2009/09/19/django-ia-auth-password-reset/
# http://www.rkblog.rk.edu.pl/w/p/password-reset-django-10/
# http://blog.montylounge.com/2009/jul/12/django-forgot-password/
#
# Note that the provided password reset function raises SMTP errors if there's any
# problem with the mailserver. Catch that more elegantly with a simple wrapper.

def exception_safe_password_reset(request, *args, **kwargs):
    try:
        return password_reset(request, *args, **kwargs)                
    except None: 
        vals = {'error_msg':'There was a problem with your request',
                'error_details':sys.exc_info(),
                'show_homepage_link': 1 }
        return render_to_response('error.html', vals, context_instance = RequestContext(request))   


# auth templates are normally in 'registration,'but that's too confusing a name, given that this app has
# both user and domain registration. Move them somewhere more descriptive.

def auth_pages_path(page):
    return {'template_name':'login_and_password/' + page}

urlpatterns =\
    patterns('corehq.apps.domain.views',
        (r'^user_registration/', include('corehq.apps.registration.user_registration_backend.urls')),
        url(r'^domain/tos/$', direct_to_template, {'template': 'tos.html'}, name='tos'),
        url(r'^domain/select/$', 'select', name='domain_select'),
        url(r'^domain/categories/$', 'autocomplete_categories', name='autocomplete_categories'),
    ) +\
    patterns('django.contrib.auth.views',
        url(r'^accounts/password_change/$', 'password_change', auth_pages_path('password_change_form.html'), name='password_change'),
        url(r'^accounts/password_change_done/$', 'password_change_done', auth_pages_path('password_change_done.html') ),

        url(r'^accounts/password_reset_email/$', exception_safe_password_reset, auth_pages_path('password_reset_form.html'), name='password_reset_email'),
        url(r'^accounts/password_reset_email/done/$', 'password_reset_done', auth_pages_path('password_reset_done.html') ),

        url(r'^accounts/password_reset_confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'password_reset_confirm', auth_pages_path('password_reset_confirm.html'), name="confirm_password_reset" ),
        url(r'^accounts/password_reset_confirm/done/$', 'password_reset_complete', auth_pages_path('password_reset_complete.html') ) 
    )


domain_specific = patterns('corehq.apps.domain.views',
                           url(r'^info/$', 'snapshot_info', name='domain_snapshot_info'),
)

domain_settings = patterns('corehq.apps.domain.views',
                           url(r'^$', 'project_settings', name="domain_project_settings"),
                           url(r'^forwarding/$', 'domain_forwarding', name='domain_forwarding'),
                           url(r'^forwarding/new/(?P<repeater_type>\w+)/$', 'add_repeater', name='add_repeater'),
                           url(r'^forwarding/test/$', 'test_repeater', name='test_repeater'),
                           url(r'^forwarding/(?P<repeater_id>[\w-]+)/stop/$', 'drop_repeater', name='drop_repeater'),
                           url(r'^copy/$', 'copy_project', name='domain_copy_snapshot'),
                           )