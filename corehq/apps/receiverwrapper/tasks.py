from celery.log import get_task_logger
from celery.schedules import crontab
from celery.decorators import periodic_task
from celery.task import task
from datetime import datetime, timedelta
from corehq.apps.receiverwrapper.models import RepeatRecord, FormRepeater
from couchdbkit.exceptions import ResourceConflict
from couchforms.models import XFormInstance
from couchdbkit.resource import ResourceNotFound
from dimagi.utils.parsing import json_format_datetime, ISO_MIN

logging = get_task_logger()

@periodic_task(run_every=timedelta(minutes=1))
def check_repeaters():
    now = datetime.utcnow()

    repeat_records = RepeatRecord.all(due_before=now)

    for repeat_record in repeat_records:
        repeat_record.fire()
        try:
            repeat_record.save()
        except ResourceConflict:
            logging.error("ResourceConflict with repeat_record %s: %s" % (repeat_record.get_id, repeat_record.to_json()))
            raise

@periodic_task(run_every=timedelta(minutes=1))
def check_inline_form_repeaters(post_fn=None):
    """old-style FormRepeater grandfathered in"""
    now = datetime.utcnow()
    forms = XFormInstance.view('receiverwrapper/forms_with_pending_repeats',
        startkey="",
        endkey=json_format_datetime(now),
        include_docs=True,
    )

    for form in forms:
        if hasattr(form, 'repeats'):
            for repeat_record in form.repeats:
                record = dict(repeat_record)
                url = record.pop('url')
                record = RepeatRecord.wrap(record)
                record.payload_id = form.get_id

                record._repeater = FormRepeater(url=url)
                record.fire(post_fn=post_fn)
                record = record.to_json()
                record['url'] = url
                repeat_record.update(record)
            form.save()