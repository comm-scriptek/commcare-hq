from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpRequest
import json
from corehq.apps.reports.schedule.parsers import ReportParser
from django.template.loader import render_to_string
from corehq.apps.reports.views import report_dispatcher, custom_report_dispatcher

class SpoofRequest(HttpRequest):
    def __init__(self, couch_user, domain):
        super(SpoofRequest, self).__init__()
        self.user = couch_user.get_django_user()
        self.couch_user = couch_user
        self.domain = domain
        self.couch_user.current_domain = domain


class ReportSchedule(object):
    """
    A basic report schedule, fully customizable, but requiring you to
    understand exactly what to pass to the view at runtime.
    """
    
    def __init__(self, view_func, view_args=None, title="unspecified", auth=None):
        self._view_func = view_func
        if view_args is not None:
            self._view_args = view_args
        else: 
            self._view_args = {}
        self._title = title
        self.auth = auth if auth else (lambda request: True)
    
    @property
    def title(self):
        return self._title

    def view(self, request, domain):
        return self._view_func(request, **self._view_args)

    def get_report_data(self, content):
        parser = ReportParser(content)
        return parser.get_html()

    def get_response(self, user, domain):
        request = SpoofRequest(user, domain)
        response = self.view(request, domain)
        DNS_name = "http://"+Site.objects.get(id = settings.SITE_ID).domain
        return render_to_string("reports/report_email.html", { "report_body": self.get_report_data(response.content),
                                                               "domain": domain,
                                                               "couch_user": user.userID,
                                                               "DNS_name": DNS_name })

class BasicReportSchedule(ReportSchedule):
    """
    These are compatibile with the daily_submission views
    """
    
    def __init__(self, report):
        self._report = report
        self.auth = lambda request: request.couch_user.can_view_report(request.couch_user.current_domain, self._report.__module__ + "." + self._report.__name__)

    @property
    def title(self):
        return self._report.name

    def get_report_data(self, content):
        report_data = json.loads(content)
        return report_data.get('report', '')

    def view(self, request, domain):
        return report_dispatcher(request, domain, self._report.slug, async=True, static_only=True)

class CustomReportSchedule(BasicReportSchedule):
    def view(self, request, domain):
        return custom_report_dispatcher(request, domain, self._report.slug, async=True)

    def get_report_data(self, content):
        report_data = json.loads(content)
        parser = ReportParser(report_data.get('report', ''))
        return parser.get_html()


