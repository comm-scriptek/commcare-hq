from datetime import datetime, timedelta
import pytz
from corehq.apps import reports
from corehq.apps.reports.display import xmlns_to_name
from couchdbkit.ext.django.schema import *
from couchexport.models import SavedExportSchema, GroupExportConfiguration
from couchexport.util import FilterFunction
import couchforms
from dimagi.utils.couch.database import get_db
from dimagi.utils.mixins import UnicodeMixIn
import settings

class HQUserType(object):
    REGISTERED = 0
    DEMO_USER = 1
    ADMIN = 2
    UNKNOWN = 3
    human_readable = [settings.COMMCARE_USER_TERM,
                      "demo_user",
                      "admin",
                      "Unknown Users"]
    toggle_defaults = [True, False, False, False]

    @classmethod
    def use_defaults(cls, show_all=False):
        defaults = cls.toggle_defaults
        if show_all:
            defaults = [True]*4
        return [HQUserToggle(i, defaults[i]) for i in range(len(cls.human_readable))]

    @classmethod
    def use_filter(cls, ufilter):
        return [HQUserToggle(i, unicode(i) in ufilter) for i in range(len(cls.human_readable))]

class HQToggle(object):
    type = None
    show = False
    name = None
    
    def __init__(self, type, show, name):
        self.type = type
        self.name = name
        self.show = show

class HQUserToggle(HQToggle):
    
    def __init__(self, type, show):
        name = HQUserType.human_readable[type]
        super(HQUserToggle, self).__init__(type, show, name)


class TempCommCareUser(object):
    filter_flag = HQUserType.UNKNOWN

    def __init__(self, domain, username, uuid):
        self.domain = domain
        self.username = username
        self._id = uuid
        self.date_joined = datetime.utcnow()
        self.is_active = False
        self.user_data = {}

        if username == HQUserType.human_readable[HQUserType.DEMO_USER]:
            self.filter_flag = HQUserType.DEMO_USER
        elif username == HQUserType.human_readable[HQUserType.ADMIN]:
            self.filter_flag = HQUserType.ADMIN

    @property
    def get_id(self):
        return self._id
    
    @property
    def user_id(self):
        return self._id

    @property
    def userID(self):
        return self._id

    @property
    def username_in_report(self):
        if self.filter_flag == HQUserType.UNKNOWN:
            final = '%s <strong>[unregistered]</strong>' % self.username
        elif self.filter_flag == HQUserType.DEMO_USER:
            final = '<strong>%s</strong>' % self.username
        else:
            final = '<strong>%s</strong> (%s)' % (self.username, self.user_id)
        return final

    @property
    def raw_username(self):
        return self.username

class ReportNotification(Document, UnicodeMixIn):
    domain = StringProperty()
    user_ids = StringListProperty()
    report_slug = StringProperty()
    
    def __unicode__(self):
        return "Notify: %s user(s): %s, report: %s" % \
                (self.doc_type, ",".join(self.user_ids), self.report_slug)
    
class DailyReportNotification(ReportNotification):
    hours = IntegerProperty()
    
    
class WeeklyReportNotification(ReportNotification):
    hours = IntegerProperty()
    day_of_week = IntegerProperty()

class FormExportSchema(SavedExportSchema):
    doc_type = 'SavedExportSchema'
    app_id = StringProperty()
    include_errors = BooleanProperty(default=True)

    @classmethod
    def wrap(cls, data):
        self = super(FormExportSchema, cls).wrap(data)
        if self.filter_function == 'couchforms.filters.instances':
            # grandfather in old custom exports
            self.include_errors = False
            self.filter_function = None
        return self

    @property
    def filter(self):
        f = FilterFunction()

        if self.app_id is not None:
            f.add(reports.util.app_export_filter, app_id=self.app_id)
        if not self.include_errors:
            f.add(couchforms.filters.instances)
        return f

    @property
    def domain(self):
        return self.index[0]

    @property
    def xmlns(self):
        return self.index[1]

    @property
    def formname(self):
        return xmlns_to_name(self.domain, self.xmlns, app_id=self.app_id)
    
class HQGroupExportConfiguration(GroupExportConfiguration):
    """
    HQ's version of a group export, tagged with a domain
    """
    domain = StringProperty()
    
    @classmethod
    def by_domain(cls, domain):
        return cls.view("groupexport/by_domain", key=domain, 
                        reduce=False, include_docs=True).all()

class CaseActivityReportCache(Document):
    domain = StringProperty()
    timezone = StringProperty()
    last_updated = DateTimeProperty()
    active_cases = DictProperty()
    inactive_cases = DictProperty()
    landmark_data = DictProperty()

    _couch_view = "reports/case_activity"
    _default_case_key = "__DEFAULT__"

    _case_list = None
    @property
    def case_list(self):
        if not self._case_list:
            key = ["type", self.domain]
            data = get_db().view(self._couch_view,
                group=True,
                group_level=3,
                startkey=key,
                endkey=key+[{}]
            ).all()
            self._case_list = [None] + [item.get('key',[])[-1] for item in data]
        return self._case_list

    _now = None
    @property
    def now(self):
        if not self._now:
            self._now = datetime.now(tz=pytz.timezone(self.timezone))
            self._now = self._now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return self._now

    _milestone = None
    @property
    def milestone(self):
        if not self._milestone:
            self._milestone = self._now - timedelta(days=121)
        return self._milestone

    def _get_user_id_counts(self, data):
        result = dict()
        for item in data:
            count = item.get('value', 0)
            user_id = item.get('key',[])[-1]
            if not user_id in result:
                result[user_id] = count
            else:
                result[user_id] += count
        return result

    def _generate_landmark(self, landmark, case_type=None):
        """
            Generates a dict with counts per owner_id of the # cases modified or closed in
            the last <landmark> days.
        """
        prefix = [] if case_type is None else ["type"]
        key = [" ".join(prefix), self.domain]
        if case_type is not None:
            key.append(case_type)
        past = self.now - timedelta(days=landmark+1)
        data = get_db().view(self._couch_view,
            group=True,
            startkey=key+[past.isoformat()],
            endkey=key+[self.now.isoformat(), {}]
        ).all()
        return self._get_user_id_counts(data)

    def _generate_open_key(self, case_type):
        prefix = ["status"]
        key = [self.domain, "open"]
        if case_type is not None:
            prefix.append("type")
            key.append(case_type)
        return [" ".join(prefix)] + key

    def _generate_case_status(self, milestone=120, case_type=None, active=True):
        """
            inactive: Generates a dict with counts per owner_id of the number of cases that are open,
            but haven't been modified in the last 120 days.
            active: Generates a dict with counts per owner_id of the number of cases that are open
            and have been modified in the last 120 days.
        """
        prefix = ["status"]
        key = [self.domain, "open"]
        if case_type is not None:
            prefix.append("type")
            key.append(case_type)
        key = self._generate_open_key(case_type)
        milestone = self.now - timedelta(days=milestone+1) + (timedelta(microseconds=1) if active else timedelta(seconds=0))
        data = get_db().view(self._couch_view,
            group=True,
            startkey=key+([milestone.isoformat()] if active else []),
            endkey=key+([self.now.isoformat()] if active else [milestone.isoformat()])
        ).all()
        return self._get_user_id_counts(data)

    def case_key(self, case_type):
        return case_type if case_type is not None else self._default_case_key

    def day_key(self, days):
        return "%s_days" % days

    def update_landmarks(self, landmarks=None):
        landmarks = landmarks if landmarks else [30, 60, 90]
        for case_type in self.case_list:
            case_key = self.case_key(case_type)
            if not case_key in self.landmark_data:
                self.landmark_data[case_key] = dict()
            for landmark in landmarks:
                self.landmark_data[case_key][self.day_key(landmark)] = self._generate_landmark(landmark, case_type)

    def update_status(self, milestone=120):
        for case_type in self.case_list:
            case_key = self.case_key(case_type)
            if case_key not in self.active_cases:
                self.active_cases[case_key] = dict()
            if case_key not in self.inactive_cases:
                self.inactive_cases[case_key] = dict()

            self.active_cases[case_key][self.day_key(milestone)] = self._generate_case_status(milestone, case_type)
            self.inactive_cases[case_key][self.day_key(milestone)] = self._generate_case_status(milestone, case_type, active=False)

    @classmethod
    def get_by_domain(cls, domain, include_docs=True):
        return cls.view('reports/case_activity_cache',
            reduce=False,
            include_docs=include_docs,
            key=domain
        )

    @classmethod
    def build_report(cls, domain):
        report = cls.get_by_domain(domain.name).first()
        if not report:
            report = cls(domain=domain.name)
        report.timezone = domain.default_timezone
        report.update_landmarks()
        report.update_status()
        report.last_updated = datetime.utcnow()
        report.save()
        return report


