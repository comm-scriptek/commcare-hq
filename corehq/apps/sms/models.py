#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from couchdbkit.ext.django.schema import *

from datetime import datetime
from django.db import models
from corehq.apps.users.models import CouchUser, CommCareUser
from casexml.apps.case.models import CommCareCase
from dimagi.utils.mixins import UnicodeMixIn
from dimagi.utils.parsing import json_format_datetime
from casexml.apps.case.signals import case_post_save
from .mixin import CommCareMobileContactMixin

INCOMING = "I"
OUTGOING = "O"

DIRECTION_CHOICES = (
    (INCOMING, "Incoming"),
    (OUTGOING, "Outgoing"))

MISSED_EXPECTED_CALLBACK = "CALLBACK_MISSED"

EVENT_TYPE_CHOICES = [MISSED_EXPECTED_CALLBACK]

class MessageLog(Document, UnicodeMixIn):
    base_doc                    = "MessageLog"
    couch_recipient_doc_type    = StringProperty() # "CommCareCase" or "CouchUser"
    couch_recipient             = StringProperty()
    phone_number                = StringProperty()
    direction                   = StringProperty()
    date                        = DateTimeProperty()
    domain                      = StringProperty()

    def __unicode__(self):
        to_from = (self.direction == INCOMING) and "from" or "to"
        return "Message %s %s" % (to_from, self.phone_number)

    def delete(self):
        super(MessageLog, self).delete() # Call the "real" delete() method.

    @property
    def username(self):
        name = self.phone_number
        if self.couch_recipient:
            try:
                if self.couch_recipient_doc_type == "CommCareCase":
                    name = CommCareCase.get(self.couch_recipient).name
                else:
                    # Must be a user
                    name = CouchUser.get_by_user_id(self.couch_recipient).username
            except Exception as e:
                pass
        return name

    @classmethod
    def by_domain_asc(cls, domain):
        if cls.__name__ == "MessageLog":
            raise NotImplementedError("Log queries not yet implemented for base class")
        return cls.view("sms/by_domain",
                    reduce=False,
                    startkey=[domain, cls.__name__],
                    endkey=[domain, cls.__name__] + [{}],
                    include_docs=True,
                    descending=False)

    @classmethod
    def by_domain_dsc(cls, domain):
        if cls.__name__ == "MessageLog":
            raise NotImplementedError("Log queries not yet implemented for base class")
        return cls.view("sms/by_domain",
                    reduce=False,
                    startkey=[domain, cls.__name__] + [{}],
                    endkey=[domain, cls.__name__],
                    include_docs=True,
                    descending=True)

    @classmethod
    def count_by_domain(cls, domain, start_date = None, end_date = {}):
        if cls.__name__ == "MessageLog":
            raise NotImplementedError("Log queries not yet implemented for base class")
        if not end_date:
            end_date = {}
        reduced = cls.view("sms/by_domain",
                            startkey=[domain, cls.__name__] + [start_date],
                            endkey=[domain, cls.__name__] + [end_date],
                            reduce=True).all()
        if reduced:
            return reduced[0]['value']
        return 0

    @classmethod
    def count_incoming_by_domain(cls, domain, start_date = None, end_date = {}):
        if cls.__name__ == "MessageLog":
            raise NotImplementedError("Log queries not yet implemented for base class")
        if not end_date:
            end_date = {}
        reduced = cls.view("sms/direction_by_domain",
                            startkey=[domain, cls.__name__, "I"] + [start_date],
                            endkey=[domain, cls.__name__, "I"] + [end_date],
                            reduce=True).all()
        if reduced:
            return reduced[0]['value']
        return 0

    @classmethod
    def count_outgoing_by_domain(cls, domain, start_date = None, end_date = {}):
        if cls.__name__ == "MessageLog":
            raise NotImplementedError("Log queries not yet implemented for base class")
        if not end_date:
            end_date = {}
        reduced = cls.view("sms/direction_by_domain",
                            startkey=[domain, cls.__name__, "O"] + [start_date],
                            endkey=[domain, cls.__name__, "O"] + [end_date],
                            reduce=True).all()
        if reduced:
            return reduced[0]['value']
        return 0

class SMSLog(MessageLog):
    text = StringProperty()
    
    def __unicode__(self):

        # crop the text (to avoid exploding the admin)
        if len(self.text) < 60: str = self.text
        else: str = "%s..." % (self.text[0:57])

        to_from = (self.direction == INCOMING) and "from" or "to"
        return "%s (%s %s)" % (str, to_from, self.phone_number)

class CallLog(MessageLog):
    
    def __unicode__(self):
        to_from = (self.direction == INCOMING) and "from" or "to"
        return "Call %s %s" % (to_from, self.phone_number)

    @classmethod
    def inbound_call_exists(cls, verified_number, after_timestamp):
        """
        Checks to see if an inbound call exists for the given number after the given timestamp.
        
        verified_number The VerifiedNumber entry for which to check the existence of a call.
        after_timestamp The datetime after which to check for the existence of a call.
        
        return          True if a call exists in the CallLog, False if not.
        """
        if verified_number is None or after_timestamp is None:
            return False
        start_timestamp = json_format_datetime(after_timestamp)
        end_timestamp = json_format_datetime(datetime.utcnow())
        reduced = cls.view("sms/by_phone_number_direction_date",
                    startkey=["CallLog", verified_number.phone_number, INCOMING] + [start_timestamp],
                    endkey=["CallLog", verified_number.phone_number, INCOMING] + [end_timestamp],
                    reduce=True).all()
        if reduced:
            return (reduced[0]['value'] > 0)
        else:
            return False

class EventLog(Document):
    domain                      = StringProperty()
    date                        = DateTimeProperty()
    couch_recipient_doc_type    = StringProperty()
    couch_recipient             = StringProperty()
    event_type                  = StringProperty(choices=EVENT_TYPE_CHOICES)


class MessageLogOld(models.Model):
    couch_recipient    = models.TextField()
    phone_number       = models.TextField()
    direction          = models.CharField(max_length=1, choices=DIRECTION_CHOICES)
    date               = models.DateTimeField()
    text               = models.TextField()
    # hm, this data is duplicate w/ couch, but will make the query much more
    # efficient to store here rather than doing a couch query for each couch user
    domain             = models.TextField()

    class Meta(): 
        db_table = "sms_messagelog"
         
    def __unicode__(self):

        # crop the text (to avoid exploding the admin)
        if len(self.text) < 60: str = self.text
        else: str = "%s..." % (self.text[0:57])

        to_from = (self.direction == INCOMING) and "from" or "to"
        return "%s (%s %s)" % (str, to_from, self.phone_number)
    
    @property
    def username(self):
        if self.couch_recipient:
            return CouchUser.get_by_user_id(self.couch_recipient).username
        return self.phone_number


class CommConnectCase(CommCareCase, CommCareMobileContactMixin):
    
    def case_changed(self):
        contact_phone_number = self.get_case_property("contact_phone_number")
        contact_phone_number_is_verified = self.get_case_property("contact_phone_number_is_verified")
        contact_backend_id = self.get_case_property("contact_backend_id")
        if(contact_phone_number is not None and contact_phone_number_is_verified):
            try:
                self.save_verified_number(self.domain, contact_phone_number, True, contact_backend_id)
            except:
                #TODO: Handle exception
                pass
        else:
            #TODO: Start phone verification workflow
            pass
    
    def get_time_zone(self):
        return self.get_case_property("time_zone")

    def get_language_code(self):
        return self.get_case_property("language_code")
    
    class Meta:
        app_label = "sms" # This is necessary otherwise syncdb will confuse the sms app with casexml


def case_changed_receiver(sender, case, **kwargs):
    c = CommConnectCase.get(case._id)
    c.case_changed()


case_post_save.connect(case_changed_receiver, CommCareCase)




