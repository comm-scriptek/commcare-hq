"""
couch models go here
"""
from __future__ import absolute_import

from datetime import datetime
import logging
import re
from corehq.apps.domain.models import Domain
from dimagi.utils.make_uuid import random_hex
from dimagi.utils.modules import to_function

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from couchdbkit.ext.django.schema import *
from couchdbkit.resource import ResourceNotFound
from casexml.apps.case.models import CommCareCase

from casexml.apps.phone.models import User as CaseXMLUser

from corehq.apps.domain.shortcuts import create_user
from corehq.apps.domain.utils import normalize_domain_name
from corehq.apps.reports.models import ReportNotification, HQUserType
from corehq.apps.users.util import normalize_username, user_data_from_registration_form, format_username, raw_username, cc_user_domain
from corehq.apps.users.xml import group_fixture
from corehq.apps.sms.mixin import CommCareMobileContactMixin
from couchforms.models import XFormInstance

from dimagi.utils.couch.database import get_db
from dimagi.utils.couch.undo import DeleteRecord, DELETED_SUFFIX
from dimagi.utils.django.email import send_HTML_email
from dimagi.utils.mixins import UnicodeMixIn
from dimagi.utils.dates import force_to_datetime
from dimagi.utils.django.database import get_unique_value


COUCH_USER_AUTOCREATED_STATUS = 'autocreated'

def _add_to_list(list, obj, default):
    if obj in list:
        list.remove(obj)
    if default:
        ret = [obj]
        ret.extend(list)
        return ret
    else:
        list.append(obj)
    return list


def _get_default(list):
    return list[0] if list else None

class Permissions(object):
    EDIT_WEB_USERS = 'edit-users'
    EDIT_COMMCARE_USERS = 'edit-commcare-users'
    EDIT_DATA = 'edit-data'
    EDIT_APPS = 'edit-apps'

    VIEW_REPORTS = 'view-reports'
    VIEW_REPORT = 'view-report'

    AVAILABLE_PERMISSIONS = [EDIT_DATA, EDIT_WEB_USERS, EDIT_COMMCARE_USERS, EDIT_APPS, VIEW_REPORTS, VIEW_REPORT]

class Roles(object):
    ROLES = (
        ('edit-apps', 'App Editor', set([Permissions.EDIT_APPS])),
        ('field-implementer', 'Field Implementer', set([Permissions.EDIT_COMMCARE_USERS])),
        ('read-only', 'Read Only', set([]))
    )

    @classmethod
    def get_role_labels(cls):
        return tuple([('admin', 'Admin')] + [(key, label) for (key, label, _) in cls.ROLES])

    @classmethod
    def get_role_mapping(cls):
        return dict([(key, perms) for (key, _, perms) in cls.ROLES])

class DomainMembership(DocumentSchema):
    """
    Each user can have multiple accounts on the
    web domain. This is primarily for Dimagi staff.
    """

    domain = StringProperty()
    is_admin = BooleanProperty(default=False)
    permissions = StringListProperty()
    permissions_data = DictProperty()
    last_login = DateTimeProperty()
    date_joined = DateTimeProperty()
    timezone = StringProperty(default=getattr(settings, "TIME_ZONE", "UTC"))

    def has_permission(self, permission, data=None):
        if permission == Permissions.VIEW_REPORT:
            if self.has_permission(Permissions.VIEW_REPORTS):
                return True
            else:
                try:
                    return data in self.permissions_data[permission]
                except (KeyError, AttributeError):
                    return False
        else:
            return permission in self.permissions

    def set_permission(self, permission, value, data=None):
        if self.has_permission(permission, data) == value:
            return

        if value:
            if permission not in self.permissions:
                self.permissions.append(permission)
            if data:
                if not self.permissions_data.has_key(permission):
                    self.permissions_data[permission] = []
                if data not in self.permissions_data[permission]:
                    self.permissions_data[permission].append(data)
        else:
            if data:
                self.permissions_data[permission] = [d for d in self.permissions_data[permission] if d != data]
            else:
                self.permissions = [p for p in self.permissions if p != permission]


    def set_permissions_data(self, permission, data):
        self.permissions_data[permission] = data

    def viewable_reports(self):
        try:
            return self.permissions_data[Permissions.VIEW_REPORT]
        except (KeyError, AttributeError):
            return []
    class Meta:
        app_label = 'users'

class DjangoUserMixin(DocumentSchema):
    username = StringProperty()
    first_name = StringProperty()
    last_name = StringProperty()
    email = StringProperty()
    password = StringProperty()
    is_staff = BooleanProperty()
    is_active = BooleanProperty()
    is_superuser = BooleanProperty()
    last_login = DateTimeProperty()
    date_joined = DateTimeProperty()

    ATTRS = (
        'username',
        'first_name',
        'last_name',
        'email',
        'password',
        'is_staff',
        'is_active',
        'is_superuser',
        'last_login',
        'date_joined',
    )

    def set_password(self, raw_password):
        dummy = User()
        dummy.set_password(raw_password)
        self.password = dummy.password

class CouchUser(Document, DjangoUserMixin, UnicodeMixIn):
    """
    A user (for web and commcare)
    """
    base_doc = 'CouchUser'
    device_ids = ListProperty()
    phone_numbers = ListProperty()
    created_on = DateTimeProperty()
#    For now, 'status' is things like:
#        ('auto_created',     'Automatically created from form submission.'),
#        ('phone_registered', 'Registered from phone'),
#        ('site_edited',     'Manually added or edited from the HQ website.'),
    status = StringProperty()

    _user = None
    _user_checked = False

    class AccountTypeError(Exception):
        pass
    
    class Inconsistent(Exception):
        pass

    class InvalidID(Exception):
        pass

    @property
    def raw_username(self):
        if self.doc_type == "CommCareUser":
            return self.username.split("@")[0]
        else:
            return self.username

    def html_username(self):
        username = self.username
        if '@' in username:
            html = "<span class='user_username'>%s</span><span class='user_domainname'>@%s</span>" % \
                   tuple(username.split('@'))
        else:
            html = "<span class='user_username'>%s</span>" % username
        return html

    @property
    def userID(self):
        return self._id

    user_id = userID

    class Meta:
        app_label = 'users'

    def __unicode__(self):
        return "couch user %s" % self.get_id

    def get_email(self):
        return self.email

    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    formatted_name = full_name

    def set_full_name(self, full_name):
        data = full_name.split()
        self.first_name = data.pop(0)
        self.last_name = ' '.join(data)

    def get_scheduled_reports(self):
        return ReportNotification.view("reports/user_notifications", key=self.user_id, include_docs=True).all()

    def delete(self):
        try:
            user = self.get_django_user()
            user.delete()
        except User.DoesNotExist:
            pass
        super(CouchUser, self).delete() # Call the "real" delete() method.

    def get_django_user(self):
        return User.objects.get(username=self.username)

    def add_phone_number(self, phone_number, default=False, **kwargs):
        """ Don't add phone numbers if they already exist """
        if not isinstance(phone_number, basestring):
            phone_number = str(phone_number)
        self.phone_numbers = _add_to_list(self.phone_numbers, phone_number, default)

    @property
    def default_phone_number(self):
        return _get_default(self.phone_numbers)
    phone_number = default_phone_number

    @property
    def couch_id(self):
        return self._id

    # Couch view wrappers
    @classmethod
    def all(cls):
        return CouchUser.view("users/by_username", include_docs=True)

    @classmethod
    def by_domain(cls, domain, is_active=True):
        flag = "active" if is_active else "inactive"
        if cls.__name__ == "CouchUser":
            key = [flag, domain]
        else:
            key = [flag, domain, cls.__name__]
        return cls.view("users/by_domain",
            reduce=False,
            startkey=key,
            endkey=key + [{}],
            include_docs=True,
        )

    @classmethod
    def phone_users_by_domain(cls, domain):
        return CouchUser.view("users/phone_users_by_domain",
            startkey=[domain],
            endkey=[domain, {}],
            include_docs=True,
        )

    def is_member_of(self, domain_qs):
        try:
            return domain_qs.name in self.get_domains() or self.is_superuser
        except Exception:
            return domain_qs in self.get_domains() or self.is_superuser

    def is_previewer(self):
        try:
            from django.conf.settings import PREVIEWER_RE
        except ImportError:
            return self.is_superuser
        else:
            return self.is_superuser or re.compile(PREVIEWER_RE).match(self.username)

    # for synching
    def sync_from_django_user(self, django_user):
        if not django_user:
            django_user = self.get_django_user()
        for attr in DjangoUserMixin.ATTRS:
            setattr(self, attr, getattr(django_user, attr))

    def sync_to_django_user(self):
        try:
            django_user = self.get_django_user()
        except User.DoesNotExist:
            django_user = User(username=self.username)
        for attr in DjangoUserMixin.ATTRS:
            setattr(django_user, attr, getattr(self, attr))
        django_user.DO_NOT_SAVE_COUCH_USER= True
        return django_user

    def sync_from_old_couch_user(self, old_couch_user):
        login = old_couch_user.default_account.login
        self.sync_from_django_user(login)

        for attr in (
            'device_ids',
            'phone_numbers',
            'created_on',
            'status',
        ):
            setattr(self, attr, getattr(old_couch_user, attr))

    @classmethod
    def from_old_couch_user(cls, old_couch_user, copy_id=True):

        if old_couch_user.account_type == "WebAccount":
            couch_user = WebUser()
        else:
            couch_user = CommCareUser()

        couch_user.sync_from_old_couch_user(old_couch_user)

        if old_couch_user.email:
            couch_user.email = old_couch_user.email

        if copy_id:
            couch_user._id = old_couch_user.default_account.login_id

        return couch_user

    @classmethod
    def wrap_correctly(cls, source):
        if source.get('doc_type') == 'CouchUser' and \
                source.has_key('commcare_accounts') and \
                source.has_key('web_accounts'):
            from . import old_couch_user_models
            user_id = old_couch_user_models.CouchUser.wrap(source).default_account.login_id
            return cls.get_by_user_id(user_id)
        else:
            return {
                'WebUser': WebUser,
                'CommCareUser': CommCareUser,
            }[source['doc_type']].wrap(source)

    @classmethod
    def get_by_username(cls, username):
        result = get_db().view('users/by_username', key=username, include_docs=True).one()
        if result:
            return cls.wrap_correctly(result['doc'])
        else:
            return None

    @classmethod
    def get_by_default_phone(cls, phone_number):
        result = get_db().view('users/by_default_phone', key=phone_number, include_docs=True).one()
        if result:
            return cls.wrap_correctly(result['doc'])
        else:
            return None

    @classmethod
    def get_by_user_id(cls, userID, domain=None):
        try:
            couch_user = cls.wrap_correctly(get_db().get(userID))
        except ResourceNotFound:
            return None
        if couch_user.doc_type != cls.__name__ and cls.__name__ != "CouchUser":
            raise CouchUser.AccountTypeError()
        if domain:
            if hasattr(couch_user, 'domain'):
                if couch_user.domain != domain and not couch_user.is_superuser:
                    return None
            elif hasattr(couch_user, 'domains'):
                if domain not in couch_user.domains and not couch_user.is_superuser:
                    return None
            else:
                raise CouchUser.AccountTypeError("User %s (%s) has neither domain nor domains" % (
                    couch_user.username,
                    couch_user.user_id
                ))
        return couch_user

    @classmethod
    def from_django_user(cls, django_user):
        couch_user = cls.get_by_username(django_user.username)
        return couch_user

    @classmethod
    def create(cls, domain, username, password, email=None, uuid='', date='', **kwargs):
        django_user = create_user(username, password=password, email=email)
        if uuid:
            if not re.match(r'[\w-]+', uuid):
                raise cls.InvalidID('invalid id %r' % uuid)
            couch_user = cls(_id=uuid)
        else:
            couch_user = cls()

        if date:
            couch_user.created_on = force_to_datetime(date)
        else:
            couch_user.created_on = datetime.utcnow()
        couch_user.sync_from_django_user(django_user)
        return couch_user

    def change_username(self, username):
        if username == self.username:
            return
        
        if User.objects.filter(username=username).exists():
            raise self.Inconsistent("User with username %s already exists" % self.username)
        
        django_user = self.get_django_user()
        django_user.DO_NOT_SAVE_COUCH_USER = True
        django_user.username = username
        django_user.save()
        self.username = username
        self.save()


    def save(self, **params):
        # test no username conflict
        by_username = get_db().view('users/by_username', key=self.username).one()
        if by_username and by_username['id'] != self._id:
            raise self.Inconsistent("CouchUser with username %s already exists" % self.username)
        
        super(CouchUser, self).save(**params)
        if not self.base_doc.endswith(DELETED_SUFFIX):
            django_user = self.sync_to_django_user()
            django_user.save()


    @classmethod
    def django_user_post_save_signal(cls, sender, django_user, created, **kwargs):
        if hasattr(django_user, 'DO_NOT_SAVE_COUCH_USER'):
            del django_user.DO_NOT_SAVE_COUCH_USER
        else:
            couch_user = cls.from_django_user(django_user)
            if couch_user:
                couch_user.sync_from_django_user(django_user)
                # avoid triggering cyclical sync
                super(CouchUser, couch_user).save()

    def is_deleted(self):
        return self.base_doc.endswith(DELETED_SUFFIX)

    def get_viewable_reports(self, domain=None, name=True):
        domain = domain or self.current_domain
        try:
            models = self.get_domain_membership(domain).viewable_reports()
            if name:
                return [to_function(m).name for m in models]
            else:
                return models
        except AttributeError:
            return []

    def has_permission(self, domain, permission, data=None):
        """To be overridden by subclasses"""
        return False

    def __getattr__(self, item):
        if item.startswith('can_'):
            perm = getattr(Permissions, item[len('can_'):].upper(), None)
            if perm:
                def fn(data=None, domain=None):
                    # temporary check to make sure I'm not by mistake passing in the domain as the `data`
                    if perm.endswith('s') and data:
                        raise TypeError
                    domain = domain or self.current_domain
                    return self.has_permission(domain, perm, data)
                fn.__name__ = item
                return fn
        return super(CouchUser, self).__getattr__(item)


class CommCareUser(CouchUser, CommCareMobileContactMixin):

    domain = StringProperty()
    registering_device_id = StringProperty()
    user_data = DictProperty()

    def sync_from_old_couch_user(self, old_couch_user):
        super(CommCareUser, self).sync_from_old_couch_user(old_couch_user)
        self.domain                 = normalize_domain_name(old_couch_user.default_account.domain)
        self.registering_device_id  = old_couch_user.default_account.registering_device_id
        self.user_data              = old_couch_user.default_account.user_data

    @classmethod
    def create(cls, domain, username, password, email=None, uuid='', date='', **kwargs):
        """
        used to be a function called `create_hq_user_from_commcare_registration_info`

        """
        commcare_user = super(CommCareUser, cls).create(domain, username, password, email, uuid, date, **kwargs)

        device_id = kwargs.get('device_id', '')
        user_data = kwargs.get('user_data', {})

        # populate the couch user
        commcare_user.domain = domain
        commcare_user.device_ids = [device_id]
        commcare_user.registering_device_id = device_id
        commcare_user.user_data = user_data

        commcare_user.save()

        return commcare_user

    @property
    def filter_flag(self):
        return HQUserType.REGISTERED
    
    @property
    def username_in_report(self):
        return self.raw_username

    @classmethod
    def create_or_update_from_xform(cls, xform):
        # if we have 1,000,000 users with the same name in a domain
        # then we have bigger problems then duplicate user accounts
        MAX_DUPLICATE_USERS = 1000000
        
        def create_or_update_safe(username, password, uuid, date, registering_phone_id, domain, user_data, **kwargs):
            # check for uuid conflicts, if one exists, respond with the already-created user
            conflicting_user = CommCareUser.get_by_user_id(uuid)
            
            # we need to check for username conflicts, other issues
            # and make sure we send the appropriate conflict response to the phone
            try:
                username = normalize_username(username, domain)
            except ValidationError:
                raise Exception("Username (%s) is invalid: valid characters include [a-z], "
                                "[0-9], period, underscore, and single quote" % username)
            
            if conflicting_user:
                # try to update. If there are username conflicts, we have to resolve them
                if conflicting_user.domain != domain:
                    raise Exception("Found a conflicting user in another domain. This is not allowed!")
                
                saved = False
                to_append = 2
                prefix, suffix = username.split("@")
                while not saved and to_append < MAX_DUPLICATE_USERS:
                    try:
                        conflicting_user.change_username(username)
                        conflicting_user.password = password
                        conflicting_user.date = date
                        conflicting_user.device_id = registering_phone_id
                        conflicting_user.user_data = user_data
                        conflicting_user.save()
                        saved = True
                    except CouchUser.Inconsistent:
                        username = "%(pref)s%(count)s@%(suff)s" % {
                                     "pref": prefix, "count": to_append,
                                     "suff": suffix}
                        to_append = to_append + 1
                if not saved:
                    raise Exception("There are over 1,000,000 users with that base name in your domain. REALLY?!? REALLY?!?!")
                return (conflicting_user, False)
                
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                # Desired outcome
                pass
            else:
                # Come up with a suitable username
                prefix, suffix = username.split("@")
                username = get_unique_value(User.objects, "username", prefix, sep="", suffix="@%s" % suffix)
            couch_user = cls.create(domain, username, password,
                uuid=uuid,
                device_id=registering_phone_id,
                date=date,
                user_data=user_data
            )
            return (couch_user, True)

        # will raise TypeError if xform.form doesn't have all the necessary params
        return create_or_update_safe(
            domain=xform.domain,
            user_data=user_data_from_registration_form(xform),
            **dict([(arg, xform.form[arg]) for arg in (
                'username',
                'password',
                'uuid',
                'date',
                'registering_phone_id'
            )])
        )

    def is_commcare_user(self):
        return True

    def is_web_user(self):
        return False

    def get_domains(self):
        return [self.domain]

    def add_commcare_account(self, domain, device_id, user_data=None):
        """
        Adds a commcare account to this.
        """
        if self.domain and self.domain != domain:
            raise self.Inconsistent("Tried to reinitialize commcare account to a different domain")
        self.domain = domain
        self.registering_device_id = device_id
        self.user_data = user_data or {}
        self.add_device_id(device_id=device_id)

    def add_device_id(self, device_id, default=False, **kwargs):
        """ Don't add phone devices if they already exist """
        self.device_ids = _add_to_list(self.device_ids, device_id, default)

    def to_casexml_user(self):
        user = CaseXMLUser(user_id=self.userID,
                           username=self.raw_username,
                           password=self.password,
                           date_joined=self.date_joined,
                           user_data=self.user_data)

        def get_owner_ids():
            return self.get_owner_ids()
        user.get_owner_ids = get_owner_ids
        user._hq_user = self # don't tell anyone that we snuck this here
        return user

    def get_forms(self, deleted=False):
        if deleted:
            view_name = 'users/deleted_forms_by_user'
        else:
            view_name = 'couchforms/by_user'

        return XFormInstance.view(view_name,
            startkey=[self.user_id],
            endkey=[self.user_id, {}],
            reduce=False,
            include_docs=True,
        )

    @property
    def form_count(self):
        result = XFormInstance.view('couchforms/by_user',
            startkey=[self.user_id],
            endkey=[self.user_id, {}],
                group_level=0
        ).one()
        if result:
            return result['value']
        else:
            return 0

    def get_cases(self, deleted=False):
        if deleted:
            view_name = 'users/deleted_cases_by_user'
        else:
            view_name = 'case/by_user'

        return CommCareCase.view(view_name,
            startkey=[self.user_id],
            endkey=[self.user_id, {}],
            reduce=False,
            include_docs=True
        )

    @property
    def case_count(self):
        result = CommCareCase.view('case/by_user',
            startkey=[self.user_id],
            endkey=[self.user_id, {}],
            group_level=0
        ).one()
        if result:
            return result['value']
        else:
            return 0

    def get_owner_ids(self):
        from corehq.apps.groups.models import Group

        owner_ids = [self.user_id]
        owner_ids.extend(Group.by_user(self, wrap=False))
        
        return owner_ids
    
    def retire(self):
        suffix = DELETED_SUFFIX
        deletion_id = random_hex()
        # doc_type remains the same, since the views use base_doc instead
        if not self.base_doc.endswith(suffix):
            self.base_doc += suffix
            self['-deletion_id'] = deletion_id
        for form in self.get_forms():
            form.doc_type += suffix
            form['-deletion_id'] = deletion_id
            form.save()
        for case in self.get_cases():
            case.doc_type += suffix
            case['-deletion_id'] = deletion_id
            case.save()

        try:
            django_user = self.get_django_user()
        except User.DoesNotExist:
            pass
        else:
            django_user.delete()
        self.save()

    def unretire(self):
        def chop_suffix(string, suffix=DELETED_SUFFIX):
            if string.endswith(suffix):
                return string[:-len(suffix)]
            else:
                return string
        self.base_doc = chop_suffix(self.base_doc)
        for form in self.get_forms(deleted=True):
            form.doc_type = chop_suffix(form.doc_type)
            form.save()
        for case in self.get_cases(deleted=True):
            case.doc_type = chop_suffix(case.doc_type)
            case.save()
        self.save()

    def transfer_to_domain(self, domain, app_id):
        username = format_username(raw_username(self.username), domain)
        self.change_username(username)
        self.domain = domain
        for form in self.get_forms():
            form.domain = domain
            form.app_id = app_id
            form.save()
        for case in self.get_cases():
            case.domain = domain
            case.save()
        self.save()

    def get_group_fixture(self):
        from corehq.apps.groups.models import Group
        return group_fixture([group for group in Group.by_user(self) if group.case_sharing], self)

    def get_group_ids(self):
        from corehq.apps.groups.models import Group
        return Group.by_user(self, wrap=False)
    
    def get_time_zone(self):
        try:
            time_zone = self.user_data["time_zone"]
        except Exception as e:
            # Gracefully handle when user_data is None, or does not have a "time_zone" entry
            time_zone = None
        return time_zone
    
    def get_language_code(self):
        try:
            lang = self.user_data["language_code"]
        except Exception as e:
            # Gracefully handle when user_data is None, or does not have a "language_code" entry
            lang = None
        return lang
    
class WebUser(CouchUser):
    domains = StringListProperty()
    domain_memberships = SchemaListProperty(DomainMembership)
    betahack = BooleanProperty(default=False)

    def sync_from_old_couch_user(self, old_couch_user):
        super(WebUser, self).sync_from_old_couch_user(old_couch_user)
        for dm in old_couch_user.web_account.domain_memberships:
            dm.domain = normalize_domain_name(dm.domain)
            self.domain_memberships.append(dm)
            self.domains.append(dm.domain)

    @classmethod
    def create(cls, domain, username, password, email=None, uuid='', date='', **kwargs):
        web_user = super(WebUser, cls).create(domain, username, password, email, uuid, date, **kwargs)
        if domain:
            web_user.add_domain_membership(domain, **kwargs)
        web_user.save()
        return web_user

    def is_commcare_user(self):
        return False

    def is_web_user(self):
        return True
    
    def get_domain_membership(self, domain):
        domain_membership = None
        try:
            for d in self.domain_memberships:
                if d.domain == domain:
                    domain_membership = d
                    if domain not in self.domains:
                        raise self.Inconsistent("Domain '%s' is in domain_memberships but not domains" % domain)
            if not domain_membership and domain in self.domains:
                raise self.Inconsistent("Domain '%s' is in domain but not in domain_memberships" % domain)
        except self.Inconsistent as e:
            logging.warning(e)
            self.domains = [d.domain for d in self.domain_memberships]
        return domain_membership

    def add_domain_membership(self, domain, **kwargs):
        for d in self.domain_memberships:
            if d.domain == domain:
                if domain not in self.domains:
                    raise self.Inconsistent("Domain '%s' is in domain_memberships but not domains" % domain)
                return

        domain_obj = Domain.get_by_name(domain)
        if not domain_obj:
            domain_obj = Domain(is_active=True, name=domain, date_created=datetime.utcnow())
            domain_obj.save()

        if kwargs.get('timezone'):
            domain_membership = DomainMembership(domain=domain, **kwargs)
        else:
            domain_membership = DomainMembership(domain=domain,
                                            timezone=domain_obj.default_timezone,
                                            **kwargs)
        self.domain_memberships.append(domain_membership)
        self.domains.append(domain)

    def delete_domain_membership(self, domain, create_record=False):
        for i, dm in enumerate(self.domain_memberships):
            if dm.domain == domain:
                if create_record:
                    record = RemoveWebUserRecord(
                        domain=domain,
                        user_id=self.user_id,
                        domain_membership=dm,
                    )
                del self.domain_memberships[i]
                break
        for i, domain_name in enumerate(self.domains):
            if domain_name == domain:
                del self.domains[i]
                break
        if create_record:
            record.save()
            return record
    
    def is_domain_admin(self, domain=None):
        if not domain:
            # hack for template
            if hasattr(self, 'current_domain'):
                # this is a hack needed because we can't pass parameters from views
                domain = self.current_domain
            else:
                return False # no domain, no admin
        if self.is_superuser:
            return True
        dm = self.get_domain_membership(domain)
        if dm:
            return dm.is_admin
        else:
            return False

    def get_domains(self):
        domains = [dm.domain for dm in self.domain_memberships]
        if set(domains) == set(self.domains):
            return domains
        else:
            raise self.Inconsistent("domains and domain_memberships out of sync")

    def set_permission(self, domain, permission, value, data=None, save=True):
        assert(permission in Permissions.AVAILABLE_PERMISSIONS)
        if self.has_permission(domain, permission) == value:
            return
        dm = self.get_domain_membership(domain)
        dm.set_permission(permission, value, data=data)
        if save:
            self.save()

    def set_permissions_data(self, domain, permission, data):
        dm = self.get_domain_membership(domain)
        dm.set_permissions_data(permission, data)

    def reset_permissions(self, domain, permissions, permissions_data=None, save=True):
        dm = self.get_domain_membership(domain)
        dm.permissions = permissions
        dm.permissions_data = permissions_data or {}
        if save:
            self.save()

    def has_permission(self, domain, permission, data=None):
        # is_admin is the same as having all the permissions set
        if self.is_superuser:
            return True
        elif self.is_domain_admin(domain):
            return True

        dm = self.get_domain_membership(domain)
        if dm:
            return dm.has_permission(permission, data)
        else:
            return False


    def get_role(self, domain=None):
        """
        Expose a simplified role-based understanding of permissions
        which maps to actual underlying permissions

        """
        if domain is None:
            # default to current_domain for django templates
            domain = self.current_domain

        if self.is_member_of(domain):
            if self.is_domain_admin(domain):
                role = 'admin'
            else:
                permissions = set(self.get_domain_membership(domain).permissions)
                role_mapping = Roles.get_role_mapping()
                for role in role_mapping:
                    if permissions == role_mapping[role]:
                        break
                else:
                    role = None
        else:
            role = None

        return role

    def set_role(self, domain, role):
        """
        A simplified role-based way to set permissions

        """
        dm = self.get_domain_membership(domain)
        dm.is_admin = False
        if role == "admin":
            dm.is_admin = True
        else:
            dm.permissions = list(Roles.get_role_mapping()[role])


    def role_label(self, domain=None):
        if not domain:
            try:
                domain = self.current_domain
            except (AttributeError, KeyError):
                return None

        return dict(Roles.get_role_labels()).get(self.get_role(domain), "Unknown Role")

class FakeUser(WebUser):
    """
    Prevent actually saving user types that don't exist in the database
    """
    def save(self, **kwargs):
        raise NotImplementedError("You aren't allowed to do that!")
        
    
class PublicUser(FakeUser):
    """
    Public users have read-only access to certain domains
    """
    
    def __init__(self, domain, **kwargs):
        super(PublicUser, self).__init__(**kwargs)
        self.domain = domain
        self.domains = [domain]
        self.domain_memberships = [DomainMembership(domain=domain, is_admin=False)]
    
    def get_role(self, domain=None):
        assert(domain == self.domain)
        return "read-only"

class InvalidUser(FakeUser):
    """
    Public users have read-only access to certain domains
    """
    
    def is_member_of(self, domain_qs):
        return False
    
#
# Django  models go here
#
class Invitation(Document):
    """
    When we invite someone to a domain it gets stored here.
    """
    domain = StringProperty()
    email = StringProperty()
#    is_domain_admin = BooleanProperty()
    invited_by = StringProperty()
    invited_on = DateTimeProperty()
    is_accepted = BooleanProperty(default=False)

    role = StringProperty()

    _inviter = None
    def get_inviter(self):
        if self._inviter is None:
            self._inviter = CouchUser.get_by_user_id(self.invited_by)
            if self._inviter.user_id != self.invited_by:
                self.invited_by = self._inviter.user_id
                self.save()
        return self._inviter

    def send_activation_email(self):

        url = "http://%s%s" % (Site.objects.get_current().domain,
                               reverse("accept_invitation", args=[self.domain, self.get_id]))
        params = {"domain": self.domain, "url": url, "inviter": self.get_inviter().formatted_name}
        text_content = render_to_string("domain/email/domain_invite.txt", params)
        html_content = render_to_string("domain/email/domain_invite.html", params)
        subject = 'Invitation from %s to join CommCareHQ' % self.get_inviter().formatted_name
        send_HTML_email(subject, self.email, text_content, html_content)

class RemoveWebUserRecord(DeleteRecord):
    user_id = StringProperty()
    domain_membership = SchemaProperty(DomainMembership)

    def undo(self):
        user = WebUser.get_by_user_id(self.user_id)
        user.add_domain_membership(**self.domain_membership._doc)
        user.save()

from .signals import *
