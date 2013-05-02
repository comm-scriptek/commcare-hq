import re
from django import forms
from django.contrib.auth.models import User

import django_tables as tables
from django.core.validators import validate_email
from django.forms.fields import ChoiceField, CharField, BooleanField
from django.utils.encoding import smart_str

from corehq.apps.domain.middleware import _SESSION_KEY_SELECTED_DOMAIN
from corehq.apps.domain.models import Domain

########################################################################################################
#
# From http://www.peterbe.com/plog/automatically-strip-whitespace-in-django-forms
#
# I'll put this in each app, so they can be standalone, but it should really go in some centralized 
# part of the distro. 
#
# Need to remember to call:
#
# super(_BaseForm, self).clean() in any derived class that overrides clean()
from corehq.apps.domain.utils import new_domain_re
from corehq.apps.users.models import WebUser
from dimagi.utils.timezones.fields import TimeZoneField
from dimagi.utils.timezones.forms import TimeZoneChoiceField
from corehq.apps.users.util import format_username

class _BaseForm(object):
    def clean(self):
        for field in self.cleaned_data:
            if isinstance(self.cleaned_data[field], basestring):
                self.cleaned_data[field] = self.cleaned_data[field].strip()
        return self.cleaned_data

########################################################################################################

class DomainModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name

########################################################################################################

class DomainBoundModelChoiceField(forms.ModelChoiceField):
    """A model choice field for an object that is restricted by domain"""
    
    _domain = None
    
    def _get_domain(self):
        return self._domain
    
    def _set_domain(self, domain):
        _domain = domain
        self.queryset = self.queryset.model.objects.filter(domain_membership__domain=domain)
    
    domain = property(_get_domain, _set_domain)

    
########################################################################################################

class DomainSelectionForm(forms.Form):
    domain_list = DomainModelChoiceField(queryset=[], empty_label=None, label="Project List")

    def __init__(self, domain_list=None, *args, **kwargs):
        super(DomainSelectionForm, self).__init__(*args, **kwargs)
        # Here's how we set the runtime filtering of the domains to be displayed in the
        # selector box
        if domain_list is not None:
            self.fields['domain_list'].queryset = domain_list

    def save( self, 
              request, 
              selected_domain_key = _SESSION_KEY_SELECTED_DOMAIN ):            
        d = Domain(id = self.cleaned_data['domain_list'].id,
                   name = self.cleaned_data['domain_list'].name )
        request.session[selected_domain_key] = d
        request.user.selected_domain = d                                                          
        return True

########################################################################################################

class DomainGlobalSettingsForm(forms.Form):
    default_timezone = TimeZoneChoiceField(label="Default Timezone", initial="UTC")
    case_sharing = ChoiceField(label='Case Sharing', choices=(('false', 'Off'), ('true', 'On')))
    
    def clean_default_timezone(self):
        data = self.cleaned_data['default_timezone']
        timezone_field = TimeZoneField()
        timezone_field.run_validators(data)
        return smart_str(data)

    def save(self, request, domain):
        try:
            global_tz = self.cleaned_data['default_timezone']
            domain.default_timezone = global_tz
            users = WebUser.by_domain(domain.name)
            for user in users.all():
                dm = user.get_domain_membership(domain.name)
                if not dm.override_global_tz:
                    dm.timezone = global_tz
                    user.save()
            domain.case_sharing = self.cleaned_data['case_sharing'] == 'true'
            domain.save()
            return True
        except Exception:
            return False

class DomainMetadataForm(DomainGlobalSettingsForm):
    is_shared = BooleanField(label='Publicly Available', help_text="""
By checking this box, you are sharing this project with our other clients. This project's contents will be put in the
public domain.
""", required=False)
    city = CharField(label="City", required=False)
    country = CharField(label="Country", required=False)
    region = CharField(label="Region", required=False,
                       help_text="e.g. US, LAC, SA, Sub-Saharan Africa, Southeast Asia, etc.") 
    project_type = CharField(label="Project Category", required=False,
                             help_text="e.g. MCH, HIV, etc.") 
    customer_type = ChoiceField(label='Customer Type', 
                                choices=(('basic', 'Basic'), ('plus', 'Plus'), ('full', 'Full')))
    is_test = ChoiceField(label='Test Project', choices=(('false', 'Real'), ('true', 'Test')))
    description = CharField(label="Description", required=False, widget=forms.Textarea)

    def save(self, request, domain):
        res = DomainGlobalSettingsForm.save(self, request, domain)
        if not res:
            return False
        try:
            domain.city = self.cleaned_data['city']
            domain.country = self.cleaned_data['country']
            domain.region = self.cleaned_data['region']
            domain.project_type = self.cleaned_data['project_type']
            domain.customer_type = self.cleaned_data['customer_type']
            domain.is_test = self.cleaned_data['is_test'] == 'true'
            domain.is_shared = self.cleaned_data['is_shared']
            domain.description = self.cleaned_data['description']
            domain.save()
            return True
        except Exception:
            return False

########################################################################################################

min_pwd = 4
max_pwd = 20
pwd_pattern = re.compile( r"([-\w]){"  + str(min_pwd) + ',' + str(max_pwd) + '}' )

def clean_password(txt):
    if len(txt) < min_pwd:
        raise forms.ValidationError('Password is too short; must be at least %s characters' % min_pwd )
    if len(txt) > max_pwd:
        raise forms.ValidationError('Password is too long; must be less than %s characters' % max_pwd )
    if not pwd_pattern.match(txt):
        raise forms.ValidationError('Password may only contain letters, numbers, hyphens, and underscores')
    return txt

########################################################################################################

class UpdateSelfForm(_BaseForm, forms.Form):
    first_name  =  forms.CharField(label='First name', max_length=User._meta.get_field('first_name').max_length)
    last_name   =  forms.CharField(label='Last (family) name', max_length=User._meta.get_field('last_name').max_length)
    email       =  forms.EmailField(label ='Email address', max_length=User._meta.get_field('email').max_length)

########################################################################################################                                   

class UpdateSelfTable(tables.Table):
    property = tables.Column(verbose_name="Property")
    old_val= tables.Column(verbose_name="Old value")
    new_val= tables.Column(verbose_name="New value")