from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe, mark_for_escaping
from corehq import CaseReassignmentInterface
from corehq.apps.dashboard.views import HQDomainDashboardView #todo yes?
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_noop
from corehq.apps.indicators.dispatcher import IndicatorAdminInterfaceDispatcher
from corehq.apps.users.views import DefaultProjectUserSettingsView

from dimagi.utils.couch.database import get_db
from dimagi.utils.decorators.memoized import memoized

from corehq.apps.reports.dispatcher import (ProjectReportDispatcher,
    CustomProjectReportDispatcher)
from corehq.apps.adm.dispatcher import (ADMAdminInterfaceDispatcher,
    ADMSectionDispatcher)
from corehq.apps.data_interfaces.dispatcher import DataInterfaceDispatcher
from hqbilling.dispatcher import BillingInterfaceDispatcher
from corehq.apps.announcements.dispatcher import (
    HQAnnouncementAdminInterfaceDispatcher)


def format_submenu_context(title, url=None, html=None,
                           is_header=False, is_divider=False):
    return {
        'title': title,
        'url': url,
        'html': html,
        'is_header': is_header,
        'is_divider': is_divider,
    }


def format_second_level_context(title, url, menu):
    return {
        'title': title,
        'url': url,
        'is_second_level': True,
        'submenu': menu,
    }


class UITab(object):
    title = None
    view = None
    subtab_classes = None

    dispatcher = None

    def __init__(self, request, domain=None, couch_user=None, project=None):
        if self.subtab_classes:
            self.subtabs = [cls(request, domain=domain, couch_user=couch_user,
                                project=project)
                            for cls in self.subtab_classes]
        else:
            self.subtabs = None

        self.domain = domain
        self.couch_user = couch_user
        self.project = project
       
        # This should not be considered as part of the subclass API unless it
        # is necessary. Try to add new explicit parameters instead.
        self._request = request

    @property
    def dropdown_items(self):
        # todo: add default implementation which looks at sidebar_items and
        # sees which ones have is_dropdown_visible or something like that.
        # Also make it work for tabs with subtabs.
        return []

    @property
    def sidebar_items(self):
        if self.dispatcher:
            context = {
                'request': self._request,
                'domain': self.domain,
            }
            return self.dispatcher.navigation_sections(context)
        else:
            return []
 
    @property
    def is_viewable(self):
        """
        Whether the tab should be displayed.  Subclass implementations can skip
        checking whether domain, couch_user, or project is not None before
        accessing an attribute of them -- this property is accessed in
        real_is_viewable and wrapped in a try block that returns False in the
        case of an AttributeError for any of those variables.

        """
        raise NotImplementedError()

    @property
    @memoized
    def real_is_viewable(self):
        if self.subtabs:
            return any(st.real_is_viewable for st in self.subtabs)
        else:
            try:
                return self.is_viewable
            except AttributeError as e:
                return False
    
    @property
    @memoized
    def url(self):
        if self.domain:
            try:
                return reverse(self.view, args=[self.domain])
            except Exception:
                pass
        
        try:
            return reverse(self.view)
        except Exception:
            return None

    @property
    @memoized
    def is_active(self):
        if self.subtabs and any(st.is_active for st in self.subtabs):
            return True

        if self.url:
            return self._request.get_full_path().startswith(self.url)
        else:
            return False

    @property
    def css_id(self):
        return self.__class__.__name__

    @classmethod
    def get_css_id(cls):
        return cls.__name__


class ProjectReportsTab(UITab):
    title = ugettext_noop("Project Reports")
    view = "corehq.apps.reports.views.default"

    @property
    def is_viewable(self):
        return (self.domain and self.project and not self.project.is_snapshot and
                (self.couch_user.can_view_reports() or
                 self.couch_user.get_viewable_reports()))

    @property
    def is_active(self):
        # HACK. We need a more overarching way to avoid doing things this way
        if 'reports/adm' in self._request.get_full_path():
            return False

        return super(ProjectReportsTab, self).is_active

    @property
    def sidebar_items(self):
        context = {
            'request': self._request,
            'domain': self.domain,
        }
        
        tools = [(_("Tools"), [
            {'title': 'My Saved Reports',
             'url': reverse('saved_reports', args=[self.domain]),
             'icon': 'icon-tasks'}
        ])]

        project_reports = ProjectReportDispatcher.navigation_sections(
            context)
        custom_reports = CustomProjectReportDispatcher.navigation_sections(
            context)

        return tools + project_reports + custom_reports


class ADMReportsTab(UITab):
    title = ugettext_noop("Active Data Management")
    view = "corehq.apps.adm.views.default_adm_report"
    dispatcher = ADMSectionDispatcher

    @property
    def is_viewable(self):
        if not self.project or self.project.commtrack_enabled:
            return False

        adm_enabled_projects = getattr(settings, 'ADM_ENABLED_PROJECTS', [])

        return (not self.project.is_snapshot and
                self.domain in adm_enabled_projects and
                  (self.couch_user.can_view_reports() or
                   self.couch_user.get_viewable_reports()))

    @property
    def is_active(self):
        if not self.domain:
            return False

        project_reports_url = reverse(ReportsTab.view, args=[self.domain])
        return (super(ADMReportsTab, self).is_active and self.domain and
                self._request.get_full_path() != project_reports_url)

class IndicatorAdminTab(UITab):
    title = ugettext_noop("Administer Indicators")
    view = "corehq.apps.indicators.views.default_admin"
    dispatcher = IndicatorAdminInterfaceDispatcher

    @property
    def is_viewable(self):
        indicator_enabled_projects = getattr(settings, 'INDICATOR_ENABLED_PROJECTS', [])
        return self.couch_user.can_edit_data and self.domain in indicator_enabled_projects


class ReportsTab(UITab):
    title = ugettext_noop("Reports")
    view = "corehq.apps.reports.views.default"
    subtab_classes = (ProjectReportsTab, ADMReportsTab, IndicatorAdminTab)


class ProjectInfoTab(UITab):
    title = ugettext_noop("Project Info")
    view = "corehq.apps.appstore.views.project_info"

    @property
    def is_viewable(self):
        return self.project and self.project.is_snapshot


#todo don't forget about manage data in Users
# class ManageDataTab(UITab):
#     title = ugettext_noop("Manage Data")
#     view = "corehq.apps.data_interfaces.views.default"
#     dispatcher = DataInterfaceDispatcher
#
#     @property
#     def is_viewable(self):
#         if self.project.commtrack_enabled:
#             return False
#         return self.domain and self.couch_user.can_edit_data()

        
class ApplicationsTab(UITab):
    title = ugettext_noop("Applications")
    view = "corehq.apps.app_manager.views.default"

    @property
    def dropdown_items(self):
        # todo async refresh submenu when on the applications page and you change the application name
        key = [self.domain]
        apps = get_db().view('app_manager/applications_brief',
            reduce=False,
            startkey=key,
            endkey=key+[{}],
            stale='update_after',
        ).all()
        submenu_context = []
        if not apps:
            return submenu_context

        submenu_context.append(format_submenu_context(_('My Applications'), is_header=True))
        for app in apps:
            app_info = app['value']
            if app_info:
                url = reverse('view_app', args=[self.domain, app_info['_id']])
                app_name = mark_safe("%s" % mark_for_escaping(app_info['name'] or '(Untitled)'))
                submenu_context.append(format_submenu_context(app_name, url=url))

        if self.couch_user.can_edit_apps():
            submenu_context.append(format_submenu_context(None, is_divider=True))
            newapp_options = [
                format_submenu_context(None, html=self._new_app_link(_('Blank Application'))),
                format_submenu_context(None, html=self._new_app_link(_('RemoteApp (Advanced Users Only)'),
                    is_remote=True)),
            ]
            newapp_options.append(format_submenu_context(_('Visit CommCare Exchange to copy existing app...'),
                url=reverse('appstore')))
            submenu_context.append(format_second_level_context(
                _('New Application...'),
                '#',
                newapp_options
            ))
        return submenu_context

    def _new_app_link(self, title, is_remote=False):
        template = "app_manager/partials/new_app_link.html"
        return mark_safe(render_to_string(template, {
            'domain': self.domain,
            'is_remote': is_remote,
            'action_text': title,
        }))

    @property
    def is_viewable(self):
        couch_user = self.couch_user
        return (self.domain and couch_user and
                (couch_user.is_web_user() or couch_user.can_edit_apps()) and
                (couch_user.is_member_of(self.domain) or couch_user.is_superuser))


class CloudcareTab(UITab):
    title = ugettext_noop("CloudCare")
    view = "corehq.apps.cloudcare.views.default"

    @property
    def is_viewable(self):
        return self.domain and self.couch_user.can_edit_data()


class MessagesTab(UITab):
    title = ugettext_noop("Messages")
    view = "corehq.apps.sms.views.default"

    @property
    def is_viewable(self):
        return (self.domain and self.project and not self.project.is_snapshot and
                not self.couch_user.is_commcare_user())

    @property
    def sidebar_items(self):
        return [(_("Messaging"), [
            {'title': _('Message History'),
             'url': reverse('messaging', args=[self.domain])},
            {'title': _('Compose SMS Message'),
             'url': reverse('sms_compose_message', args=[self.domain])}
        ])]


class RemindersTab(UITab):
    title = ugettext_noop("Reminders")
    view = "corehq.apps.reminders.views.default"

    @property
    def is_viewable(self):
        return self.project.commtrack_enabled


class ProjectUsersTab(UITab):
    title = ugettext_noop("Users")
    view = DefaultProjectUserSettingsView.name

    @property
    def dropdown_items(self):
        return []

    @property
    def is_viewable(self):
        return (self.couch_user.can_edit_commcare_users() or
                self.couch_user.can_edit_web_users() or
                self.couch_user.can_edit_data())

    @property
    @memoized
    def is_active(self):
        cloudcare_settings_url = reverse('cloudcare_app_settings', args=[self.domain])
        manage_data_url = reverse('data_interfaces_default', args=[self.domain])
        full_path = self._request.get_full_path()
        return (super(ProjectUsersTab, self).is_active
                or full_path.startswith(cloudcare_settings_url)
                or full_path.startswith(manage_data_url))

    @property
    def sidebar_items(self):
        items = []
 
        if self.couch_user.can_edit_commcare_users():
            def commcare_username(request=None, couch_user=None, **context):
                if (couch_user.user_id != request.couch_user.user_id and
                    couch_user.is_commcare_user()):
                    username = couch_user.username_in_report
                    if couch_user.is_deleted():
                        username += " (%s)" % _("Deleted")
                    return mark_safe(username)
                else:
                    return None

            mobile_users_menu = [
                {'title': _('Mobile Workers'),
                 'url': reverse('commcare_users', args=[self.domain]),
                 'description': _("Create and manage users for CommCare and CloudCare."),
                 'children': [
                     {'title': commcare_username,
                      'urlname': 'commcare_user_account'},
                     {'title': _('New Mobile Worker'),
                      'urlname': 'add_commcare_account'},
                     {'title': _('Bulk Upload'),
                      'urlname': 'upload_commcare_users'},
                     {'title': _('Transfer Mobile Workers'),
                      'urlname': 'user_domain_transfer'},
                     ]},

                {'title': _('Groups'),
                 'url': reverse('all_groups', args=[self.domain]),
                 'description': _("Create and manage reporting and case sharing groups for Mobile Workers."),
                 'children': [
                     {'title': lambda **context: (
                         "%s %s" % (_("Editing"), context['group'].name)),
                      'urlname': 'group_members'},
                     {'title': _('Membership Info'),
                      'urlname': 'group_membership'}
                 ]}
            ]

            if self.couch_user.is_domain_admin():
                mobile_users_menu.append({
                    'title': _('CloudCare Permissions'),
                    'url': reverse('cloudcare_app_settings',
                                    args=[self.domain])
                })

            items.append((_('Application Users'), mobile_users_menu))

        if self.couch_user.can_edit_web_users():
            def web_username(request=None, couch_user=None, **context):
                if (couch_user.user_id != request.couch_user.user_id and
                    not couch_user.is_commcare_user()):
                    username = couch_user.html_username()
                    if couch_user.is_deleted():
                        username += " (%s)" % _("Deleted")
                    return mark_safe(username)
                else:
                    return None

            items.append((_('Project Users'), [
                {'title': _('Web Users & Roles'),
                 'url': reverse('web_users', args=[self.domain]),
                 'description': _("Grant other CommCare HQ users access to your project and manage user roles."),
                 'children': [
                     {'title': _("Invite Web User"),
                      'urlname': 'invite_web_user'},
                     {'title': web_username,
                      'urlname': 'user_account'}
                 ]}
            ]))

        if self.couch_user.can_edit_data():
            from corehq.apps.data_interfaces.dispatcher import DataInterfaceDispatcher
            items.extend(DataInterfaceDispatcher.navigation_sections({
                "request": self._request,
                "domain": self.domain,
            }))

        return items


class ProjectSettingsTab(UITab):
    title = ugettext_noop("Project Settings")
    view = "corehq.apps.domain.views.project_settings"

    @property
    def sidebar_items(self):
        items = []

        # items.append((_('My Account'), [
        #     {'title': _('My Account Settings'),
        #      'url': reverse('my_account', args=[self.domain])},
        #     {'title': _('Change My Password'),
        #      'url': reverse('change_my_password', args=[self.domain])}
        # ]))

        if self.couch_user.can_edit_web_users():
            def forward_name(repeater_type=None, **context):
                if repeater_type == 'FormRepeater':
                    return _("Forward Forms")
                elif repeater_type == 'ShortFormRepeater':
                    return _("Forward Form Stubs")
                elif repeater_type == 'CaseRepeater':
                    return _("Forward Cases")

            administration = [
                {'title': _('Project Settings'),
                 'url': reverse('domain_project_settings',
                     args=[self.domain])},
                {'title': _('CommCare Exchange'),
                 'url': reverse('domain_snapshot_settings',
                     args=[self.domain])},
                {'title': _('Multimedia Sharing'),
                 'url': reverse('domain_manage_multimedia',
                     args=[self.domain])}
            ]

            if self.couch_user.is_superuser:
                administration.append({
                    'title': _('Internal Settings'),
                    'url': reverse('domain_internal_settings',
                        args=[self.domain])
                })

            administration.extend([
                {'title': _('Data Forwarding'),
                 'url': reverse('domain_forwarding', args=[self.domain]),
                 'children': [
                     {'title': forward_name,
                      'urlname': 'add_repeater'}
                 ]}
            ])
            items.append((_('Project Administration'), administration))

        if self.project.commtrack_enabled:
            items.append((_('CommTrack'), [
                {'title': _('Project Settings'),
                 'url': reverse('domain_commtrack_settings',
                     args=[self.domain])},
                {'title': _('Manage Products'),
                 'url': reverse('commtrack_product_list',
                     args=[self.domain])},
                {'title': _('Manage Locations'),
                 'url': reverse('manage_locations', args=[self.domain])}
            ]))

        return items



class AdminReportsTab(UITab):
    title = ugettext_noop("Admin Reports")
    view = "corehq.apps.hqadmin.views.default"

    @property
    def sidebar_items(self):
        # todo: convert these to dispatcher-style like other reports
        return [
            (_('Administrative Reports'), [
                {'title': _('Domain List'),
                 'url': reverse('domain_list')},
                {'title': _('Domain Activity Report'),
                 'url': reverse('domain_activity_report')},
                {'title': _('Message Logs Across All Domains'),
                 'url': reverse('message_log_report')},
                {'title': _('Global Statistics'),
                 'url': reverse('global_report')},
                {'title': _('CommCare Versions'),
                 'url': reverse('commcare_version_report')},
                {'title': _('Submissions & Error Statistics per Domain'),
                 'url': reverse('global_submissions_errors')},
                {'title': _('System Info'),
                 'url': reverse('system_info')},
            ]),
            (_('Administrative Operations'), [
                {'title': _('View/Update Domain Information'),
                 'url': reverse('domain_update')}
            ])
        ]
    
    @property
    def is_viewable(self):
        return self.couch_user and self.couch_user.is_superuser


class GlobalADMConfigTab(UITab):
    title = ugettext_noop("Global ADM Report Configuration")
    view = "corehq.apps.adm.views.default_adm_admin"
    dispatcher = ADMAdminInterfaceDispatcher

    @property
    def is_viewable(self):
        return self.couch_user and self.couch_user.is_superuser


class BillingTab(UITab):
    title = ugettext_noop("Billing")
    view = "billing_default"
    dispatcher = BillingInterfaceDispatcher

    @property
    def is_viewable(self):
        return self.couch_user and self.couch_user.is_superuser


class AnnouncementsTab(UITab):
    title = ugettext_noop("Announcements")
    view = "corehq.apps.announcements.views.default_announcement"
    dispatcher = HQAnnouncementAdminInterfaceDispatcher

    @property
    def is_viewable(self):
        return self.couch_user and self.couch_user.is_superuser


class AdminTab(UITab):
    title = ugettext_noop("Admin")
    view = "corehq.apps.hqadmin.views.default"
    subtab_classes = (
        AdminReportsTab,
        GlobalADMConfigTab,
        BillingTab,
        AnnouncementsTab
    )

    @property
    def dropdown_items(self):
        submenu_context = [
            format_submenu_context(_("Reports"), is_header=True),
            format_submenu_context(_("Admin Reports"), url=reverse("default_admin_report")),
            format_submenu_context(_("System Info"), url=reverse("system_info")),
            format_submenu_context(_("Management"), is_header=True),
            format_submenu_context(mark_for_escaping(_("ADM Reports & Columns")),
                url=reverse("default_adm_admin_interface")),
#            format_submenu_context(mark_for_escaping("HQ Announcements"),
#                url=reverse("default_announcement_admin")),
        ]
        try:
            submenu_context.append(format_submenu_context(mark_for_escaping(_("Billing")),
                url=reverse("billing_default")))
        except Exception:
            pass
        submenu_context.extend([
            format_submenu_context(None, is_divider=True),
            format_submenu_context(_("Django Admin"), url="/admin")
        ])
        return submenu_context

    @property
    def is_viewable(self):
        return self.couch_user and self.couch_user.is_superuser


class ExchangeTab(UITab):
    title = ugettext_noop("Exchange")
    view = "corehq.apps.appstore.views.appstore"

    @property
    def dropdown_items(self):
        submenu_context = None
        if self.domain and self.couch_user.is_domain_admin(self.domain):
            submenu_context = [
                format_submenu_context(_("CommCare Exchange"), url=reverse("appstore")),
                format_submenu_context(_("Publish this project"),
                    url=reverse("domain_snapshot_settings",
                        args=[self.domain]))
            ]
        return submenu_context

    @property
    def is_viewable(self):
        return not self.couch_user.is_commcare_user()


class ManageSurveysTab(UITab):
    title = ugettext_noop("Manage Surveys")
    view = "corehq.apps.reminders.views.sample_list"

    @property
    def is_viewable(self):
        return (self.domain and self.couch_user.can_edit_data() and
                self.project.survey_management_enabled)
