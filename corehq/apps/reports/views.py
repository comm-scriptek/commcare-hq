from datetime import datetime, timedelta
import json
from corehq.apps.reports import util, standard
from corehq.apps.reports.models import FormExportSchema
from corehq.apps.users.decorators import require_permission
from corehq.apps.users.export import export_users
import couchexport
from couchexport.export import UnsupportedExportFormat, export_raw
from couchexport.util import FilterFunction
from couchexport.views import _export_tag_or_bust
import couchforms
from couchforms.models import XFormInstance
from dimagi.utils.couch.loosechange import parse_date
from dimagi.utils.export import WorkBook
from dimagi.utils.web import json_request, render_to_response
from dimagi.utils.couch.database import get_db
from dimagi.utils.modules import to_function
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, Http404, HttpResponseNotFound
from django.core.urlresolvers import reverse
from corehq.apps.domain.decorators import login_and_domain_required, login_or_digest
import couchforms.views as couchforms_views
from django.contrib import messages
from dimagi.utils.parsing import json_format_datetime, string_to_boolean
from django.contrib.auth.decorators import permission_required
from dimagi.utils.decorators.datespan import datespan_in_request
from casexml.apps.case.models import CommCareCase
from casexml.apps.case.export import export_cases_and_referrals
from corehq.apps.reports.display import xmlns_to_name
from couchexport.schema import build_latest_schema
from couchexport.models import ExportSchema, ExportColumn, SavedExportSchema,\
    ExportTable, Format, FakeSavedExportSchema
from couchexport import views as couchexport_views
from couchexport.shortcuts import export_data_shared, export_raw_data,\
    export_response
from django.views.decorators.http import require_POST
from couchforms.filters import instances
from couchdbkit.exceptions import ResourceNotFound
from fields import FilterUsersField
from util import get_all_users_by_domain
from corehq.apps.hqsofabed.models import HQFormData
from StringIO import StringIO

DATE_FORMAT = "%Y-%m-%d"

datespan_default = datespan_in_request(
    from_param="startdate",
    to_param="enddate",
    default_days=7,
)

require_form_export_permission = require_permission('view-report', 'corehq.apps.reports.standard.ExcelExportReport', login_decorator=None)
require_case_export_permission = require_permission('view-report', 'corehq.apps.reports.standard.CaseExportReport', login_decorator=None)
@login_and_domain_required
def default(request, domain, template="reports/report_base.html"):
    context = {
        'domain': domain,
        'slug': None,
        'report': {'name': "Select a Report to View"}
    }
    return render_to_response(request, template, context)

@login_or_digest
@require_form_export_permission
@datespan_default
def export_data(req, domain):
    """
    Download all data for a couchdbkit model
    """
    try:
        export_tag = json.loads(req.GET.get("export_tag", "null") or "null")
    except ValueError:
        return HttpResponseBadRequest()

    group, users = util.get_group_params(domain, **json_request(req.GET))
    include_errors = string_to_boolean(req.GET.get("include_errors", False))

    kwargs = {"format": req.GET.get("format", Format.XLS_2007),
              "previous_export_id": req.GET.get("previous_export", None),
              "filename": export_tag,
              "use_cache": string_to_boolean(req.GET.get("use_cache", "True")),
              "max_column_size": int(req.GET.get("max_column_size", 2000)),
              "separator": req.GET.get("separator", "|")}

    user_filter, _ = FilterUsersField.get_user_filter(req)

    if user_filter:
        users_matching_filter = map(lambda x: x._id, get_all_users_by_domain(domain, filter_users=user_filter))
        def _ufilter(user):
            try:
                return user['form']['meta']['userID'] in users_matching_filter
            except KeyError:
                return False
        filter = _ufilter
    else:
        filter = FilterFunction(util.group_filter, group=group)

    errors_filter = instances if not include_errors else None

    kwargs['filter'] = couchexport.util.intersect_filters(filter, errors_filter)

    if kwargs['format'] == 'raw':
        resp = export_raw_data([domain, export_tag], filename=export_tag)
    else:
        try:
            resp = export_data_shared([domain,export_tag], **kwargs)
        except UnsupportedExportFormat as e:
            return HttpResponseBadRequest(e)
    if resp:
        return resp
    else:
        messages.error(req, "Sorry, there was no data found for the tag '%s'." % export_tag)
        next = req.GET.get("next", "")
        if not next:
            next = reverse('report_dispatcher', args=[domain, standard.ExcelExportReport.slug])
        return HttpResponseRedirect(next)

@require_form_export_permission
@login_and_domain_required
@datespan_default
def export_data_async(request, domain):
    """
    Download all data for a couchdbkit model
    """

    try:
        export_tag = json.loads(request.GET.get("export_tag", "null") or "null")
        export_type = request.GET.get("type", "form")
    except ValueError:
        return HttpResponseBadRequest()

    assert(export_tag[0] == domain)

    filter = util.create_export_filter(request, domain, export_type=export_type)

    return couchexport_views.export_data_async(request, filter=filter, type=export_type)


class CustomExportHelper(object):

    def __init__(self, request, domain, export_id=None):
        self.request = request
        self.domain = domain
        self.export_type = request.GET.get('type', 'form')
        if self.export_type == 'form':
            self.ExportSchemaClass = FormExportSchema
        else:
            self.ExportSchemaClass = SavedExportSchema

        if export_id:
            self.custom_export = self.ExportSchemaClass.get(export_id)
            assert(self.custom_export.doc_type == 'SavedExportSchema')
            assert(self.custom_export.type == self.export_type)
            assert(self.custom_export.index[0] == domain)
        else:
            self.custom_export = self.ExportSchemaClass(type=self.export_type)
            if self.export_type == 'form':
                self.custom_export.app_id = request.GET.get('app_id')

    def update_custom_export(self):
        schema = ExportSchema.get(self.request.POST["schema"])
        self.custom_export.index = schema.index
        self.custom_export.schema_id = self.request.POST["schema"]
        self.custom_export.name = self.request.POST["name"]
        self.custom_export.default_format = self.request.POST["format"] or Format.XLS_2007

        table = self.request.POST["table"]
        cols = self.request.POST['order'].strip().split()
        export_cols = [ExportColumn(index=col, display=self.request.POST["%s_display" % col]) for col in cols]
        export_table = ExportTable(index=table, display=self.request.POST["name"], columns=export_cols)
        self.custom_export.tables = [export_table]
        self.custom_export.order = cols

        table_dict = dict([t.index, t] for t in self.custom_export.tables)
        if table in table_dict:
            table_dict[table].columns = export_cols
        else:
            self.custom_export.tables.append(ExportTable(index=table,
                display=self.custom_export.name,
                columns=export_cols))

        if self.export_type == 'form':
            self.custom_export.include_errors = bool(self.request.POST.get("include-errors"))
            self.custom_export.app_id = self.request.POST.get('app_id')


@login_or_digest
@require_form_export_permission
@datespan_default
def export_default_or_custom_data(request, domain, export_id=None):
    """
    Export data from a saved export schema
    """

    async = request.GET.get('async') == 'true'
    next = request.GET.get("next", "")
    format = request.GET.get("format", "")
    export_type = request.GET.get("type", "form")
    previous_export_id = request.GET.get("previous_export", None)
    filename = request.GET.get("filename", None)

    filter = util.create_export_filter(request, domain, export_type=export_type)

    if export_id:
        export_object = CustomExportHelper(request, domain, export_id).custom_export
    else:
        if not async:
            # this function doesn't support synchronous export without a custom export object
            # if we ever want that (i.e. for HTML Preview) then we just need to give
            # FakeSavedExportSchema a download_data function (called below)
            return HttpResponseBadRequest()
        try:
            export_tag = json.loads(request.GET.get("export_tag", "null") or "null")
        except ValueError:
            return HttpResponseBadRequest()
        assert(export_tag[0] == domain)

        export_object = FakeSavedExportSchema(index=export_tag)


    if async:
        return export_object.export_data_async(filter, filename, previous_export_id, format=format)
    else:
        if not next:
            next = reverse('report_dispatcher', args=[domain, standard.ExcelExportReport.slug])
        resp = export_object.download_data(format, filter=filter)
        if resp:
            return resp
        else:
            messages.error(request, "Sorry, there was no data found for the tag '%s'." % export_object.name)
            return HttpResponseRedirect(next)

@require_form_export_permission
@login_and_domain_required
def custom_export(req, domain):
    """
    Customize an export
    """
    try:
        export_tag = [domain, json.loads(req.GET.get("export_tag", "null") or "null")]
    except ValueError:
        return HttpResponseBadRequest()
    export_type = req.GET.get("type", "form")

    helper = CustomExportHelper(req, domain)

    if req.method == "POST":
        helper.update_custom_export()
        helper.custom_export.save()
        messages.success(req, "Custom export created! You can continue editing here.")
        return HttpResponseRedirect("%s?type=%s" % (reverse("edit_custom_export",
                                            args=[domain, helper.custom_export.get_id]), export_type))

    schema = build_latest_schema(export_tag)
    
    if schema:
        app_id = req.GET.get('app_id')
        saved_export = helper.ExportSchemaClass.default(
            schema=schema,
            name="%s: %s" % (
                xmlns_to_name(domain, export_tag[1], app_id=app_id) if export_type == "form" else export_tag[1],
                datetime.utcnow().strftime("%Y-%m-%d")
            ),
            type=export_type
        )
        
        if export_type == 'form':
            saved_export.app_id = app_id
        return render_to_response(req, "reports/reportdata/customize_export.html",
                                  {"saved_export": saved_export,
                                   "slug": standard.ExcelExportReport.slug, 
                                   "table_config": saved_export.table_configuration[0],
                                   "domain": domain})
    else:
        messages.warning(req, "<strong>No data found for that form "
                      "(%s).</strong> Submit some data before creating an export!" % \
                      xmlns_to_name(domain, export_tag[1]), extra_tags="html")
        return HttpResponseRedirect(reverse('report_dispatcher', args=[domain, standard.ExcelExportReport.slug]))

@require_form_export_permission
@login_and_domain_required
def edit_custom_export(req, domain, export_id):
    """
    Customize an export
    """
    helper = CustomExportHelper(req, domain, export_id)
    if req.method == "POST":
        helper.update_custom_export()
    
    # not yet used, but will be when we support child table export
#    table_index = req.GET.get("table_id", None)
#    if table_index:
#        table_config = saved_export.get_table_configuration(table_index)
#    else:
        helper.custom_export.save()
    table_config = helper.custom_export.table_configuration[0]
    
    slug = standard.ExcelExportReport.slug if helper.export_type == "form" \
            else standard.CaseExportReport.slug
    return render_to_response(req, "reports/reportdata/customize_export.html",
                              {"saved_export": helper.custom_export,
                               "table_config": table_config,
                               "slug": slug,
                               "domain": domain})
@require_form_export_permission
@login_and_domain_required
def export_all_form_metadata(req, domain):
    """
    Export metadata for _all_ forms in a domain.
    """
    format = req.GET.get("format", Format.XLS_2007)
    
    headers = ("domain", "instanceID", "received_on", "type", 
               "timeStart", "timeEnd", "deviceID", "username", 
               "userID", "xmlns", "version")
    def _form_data_to_row(formdata):
        def _key_to_val(formdata, key):
            if key == "type":  return xmlns_to_name(domain, formdata.xmlns)
            else:              return getattr(formdata, key)
        return [_key_to_val(formdata, key) for key in headers]
    
    temp = StringIO()
    data = (_form_data_to_row(f) for f in HQFormData.objects.filter(domain=domain))
    export_raw((("forms", headers),), (("forms", data),), temp)
    return export_response(temp, format, "%s_forms" % domain)
    
@require_form_export_permission
@login_and_domain_required
@require_POST
def delete_custom_export(req, domain, export_id):
    """
    Delete a custom export
    """
    saved_export = SavedExportSchema.get(export_id)
    type = saved_export.type
    saved_export.delete()
    messages.success(req, "Custom export was deleted.")
    if type == "form":
        return HttpResponseRedirect(reverse('report_dispatcher', args=[domain, standard.ExcelExportReport.slug]))
    else:
        return HttpResponseRedirect(reverse('report_dispatcher', args=[domain, standard.CaseExportReport.slug]))

@require_permission('view-reports')
@login_and_domain_required
def case_details(request, domain, case_id):
    timezone = util.get_timezone(request.couch_user.user_id, domain)

    try:
        case = CommCareCase.get(case_id)
        report_name = 'Details for Case "%s"' % case.name
    except ResourceNotFound:
        messages.info(request, "Sorry, we couldn't find that case. If you think this is a mistake plase report an issue.")
        return HttpResponseRedirect(reverse("submit_history_report", args=[domain]))


    form_lookups = dict((form.get_id,
                         "%s: %s" % (form.received_on.date(), xmlns_to_name(domain, form.xmlns))) \
                        for form in [XFormInstance.get(id) for id in case.xform_ids] \
                        if form)
    return render_to_response(request, "reports/reportdata/case_details.html", {
        "domain": domain,
        "case_id": case_id,
        "slug": standard.CaseListReport.slug,
        "form_lookups": form_lookups,
        "report": {
            "name": report_name
        },
        "layout_flush_content": True,
        "timezone": timezone
    })

@login_or_digest
@require_case_export_permission
@login_and_domain_required
def download_cases(request, domain):
    include_closed = json.loads(request.GET.get('include_closed', 'false'))
    format = Format.from_format(request.GET.get('format') or Format.XLS_2007)

    view_name = 'hqcase/all_cases' if include_closed else 'hqcase/open_cases'

    key = [domain, {}, {}]
    cases = CommCareCase.view(view_name, startkey=key, endkey=key + [{}], reduce=False, include_docs=True)
#    group, users = util.get_group_params(domain, **json_request(request.GET))
    group = request.GET.get('group', None)
    user_filter, _ = FilterUsersField.get_user_filter(request)
    users = get_all_users_by_domain(domain, group=group, filter_users=user_filter)
#    if not group:
#        users.extend(CommCareUser.by_domain(domain, is_active=False))

    workbook = WorkBook()
    export_cases_and_referrals(cases, workbook, users=users)
    export_users(users, workbook)
    response = HttpResponse(workbook.format(format.slug))
    response['Content-Type'] = "%s" % format.mimetype
    response['Content-Disposition'] = "attachment; filename={domain}_data.{ext}".format(domain=domain, ext=format.extension)
    return response

@require_permission('view-reports')
@login_and_domain_required
def form_data(request, domain, instance_id):
    timezone = util.get_timezone(request.couch_user.user_id, domain)
    try:
        instance = XFormInstance.get(instance_id)
    except ResourceNotFound:
        raise Http404()
    try:
        assert(domain == instance.domain)
    except AssertionError:
        raise Http404()
    cases = CommCareCase.view("case/by_xform_id", key=instance_id, reduce=False, include_docs=True).all()
    try:
        form_name = instance.get_form["@name"]
    except KeyError:
        form_name = "Untitled Form"
    return render_to_response(request, "reports/reportdata/form_data.html",
                              dict(domain=domain,
                                   instance=instance,
                                   cases=cases,
                                   timezone=timezone,
                                   slug=standard.SubmitHistory.slug,
                                   form_data=dict(name=form_name,
                                                  modified=instance.received_on)))
@require_form_export_permission
@login_and_domain_required
def download_form(request, domain, instance_id):
    instance = XFormInstance.get(instance_id)
    assert(domain == instance.domain)
    return couchforms_views.download_form(request, instance_id)

@require_form_export_permission
@login_and_domain_required
def download_attachment(request, domain, instance_id, attachment):
    instance = XFormInstance.get(instance_id)
    assert(domain == instance.domain)
    return couchforms_views.download_attachment(request, instance_id, attachment)

# Weekly submissions by xmlns

def mk_date_range(start=None, end=None, ago=timedelta(days=7), iso=False):
    if isinstance(end, basestring):
        end = parse_date(end)
    if isinstance(start, basestring):
        start = parse_date(start)
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - ago
    if iso:
        return json_format_datetime(start), json_format_datetime(end)
    else:
        return start, end

@login_and_domain_required
@permission_required("is_superuser")
def emaillist(request, domain):
    """
    Test an email report 
    """
    # circular import
    from corehq.apps.reports.schedule.config import ScheduledReportFactory
    return render_to_response(request, "reports/email/report_list.html", 
                              {"domain": domain,
                               "reports": ScheduledReportFactory.get_reports()})

@login_and_domain_required
@permission_required("is_superuser")
def emailtest(request, domain, report_slug):
    """
    Test an email report 
    """
    # circular import
    from corehq.apps.reports.schedule.config import ScheduledReportFactory
    report = ScheduledReportFactory.get_report(report_slug)
    report.get_response(request.user, domain)
    return HttpResponse(report.get_response(request.user, domain))

@login_and_domain_required
@datespan_default
def report_dispatcher(request, domain, report_slug, return_json=False, map='STANDARD_REPORT_MAP', export=False):
    mapping = getattr(settings, map, None)
    if not mapping:
        return HttpResponseNotFound("Sorry, no standard reports have been configured yet.")
    for key, models in mapping.items():
        for model in models:
            klass = to_function(model)
            if klass.slug == report_slug:
                k = klass(domain, request)
                if not request.couch_user.can_view_report(model):
                     raise Http404
                elif return_json:
                    return k.as_json()
                elif export:
                    return k.as_export()
                else:
                    return k.as_view()
    raise Http404

@login_and_domain_required
@datespan_default
def custom_report_dispatcher(request, domain, report_slug, export=False):
    mapping = getattr(settings, 'CUSTOM_REPORT_MAP', None)
    if not mapping or not domain in mapping:
        return HttpResponseNotFound("Sorry, no custom reports have been configured yet.")
    for model in mapping[domain]:
        klass = to_function(model)
        if klass.slug == report_slug:
            k = klass(domain, request)
            if not request.couch_user.can_view_report(model):
                raise Http404
            elif export:
                return k.as_export()
            else:
                return k.as_view()
    raise Http404
