var HQReport = function (options) {
    'use strict';
    var self = this;
    self.domain = options.domain;
    self.datespan = options.datespan;
    self.filterSet = options.filterSet || false;
    self.needsFilters = options.needsFilters || false;
    self.filterAccordion = options.filterAccordion || "#reportFilters";
    self.filterSubmitButton = options.filterSubmitButton || $('#paramSelectorForm button[type="submit"]');
    self.toggleFiltersButton = options.toggleFiltersButton || "#toggle-report-filters";
    self.exportReportButton = options.exportReportButton || "#export-report-excel";
    self.emailReportButton = options.emailReportButton || "#email-report";
    self.urlRoot = options.urlRoot;
    self.slug = options.slug;
    self.subReportSlug = options.subReportSlug;
    self.type = options.type;

    self.toggleFiltersCookie = self.domain+'.hqreport.toggleFilterState';
    self.datespanCookie = self.domain+".hqreport.filterSetting.test.datespan";

    self.initialLoad = true;

    self.init = function () {
        $(function () {
            checkFilterAccordionToggleState();

            $(self.exportReportButton).click(button_click_handler("export/"));

            $(self.emailReportButton).click(button_click_handler("email_onceoff/"));

            self.resetFilterState();
            if (self.needsFilters) {
                self.filterSubmitButton.button('reset').addClass('btn-primary');
            }

            function button_click_handler(path) {
                return function (e) {
                    var params = window.location.search.substr(1);
                    var exportURL;
                    e.preventDefault();
                    if (params.length <= 1) {
                        if (self.loadDatespanFromCookie()) {
                            params = "startdate="+self.datespan.startdate+
                                "&enddate="+self.datespan.enddate;
                        }
                    }
                    window.location.href = window.location.pathname.replace(self.urlRoot,
                        self.urlRoot+path)+"?"+params;
                }
            }
        });
    };

    self.handleTabularReportCookies = function (reportDatatable) {
        var defaultRowsCookieName = self.domain+'.hqreport.tabularSetting.defaultRows',
            savedPath = window.location.pathname;
        var defaultRowsCookie = ''+$.cookie(defaultRowsCookieName);
        reportDatatable.defaultRows = parseInt(defaultRowsCookie) || reportDatatable.defaultRows;

        $(reportDatatable.dataTableElem).on('hqreport.tabular.lengthChange', function (event, value) {
            $.cookie(defaultRowsCookieName, value,
                {path: savedPath, expires: 2});
        });
    };

    self.saveDatespanToCookie = function () {
        if (self.datespan) {
            $.cookie(self.datespanCookie+'.startdate', self.datespan.startdate,
                {path: self.urlRoot, expires: 1});
            $.cookie(self.datespanCookie+'.enddate', self.datespan.enddate,
                {path: self.urlRoot, expires: 1});
        }
    };

    self.loadDatespanFromCookie = function () {
        if (self.datespan) {
            var cookie_startdate = $.cookie(self.datespanCookie+'.startdate'),
                cookie_enddate = $.cookie(self.datespanCookie+'.enddate'),
                load_success = false;

            if (cookie_enddate && cookie_startdate) {
                load_success = true;
                self.datespan.startdate = cookie_startdate;
                self.datespan.enddate = cookie_enddate;
            }
        }
        return load_success;
    };

    var checkFilterAccordionToggleState = function () {
        var _setShowFilterCookie = function (show) {
            var showStr = show ? 'in' : '';
            $.cookie(self.toggleFiltersCookie, showStr, {path: self.urlRoot, expires: 1});
        };
        
        if ($.cookie(self.toggleFiltersCookie) === null) {
            // default to showing filters
            _setShowFilterCookie(true);
        }
        $(self.filterAccordion).addClass($.cookie(self.toggleFiltersCookie));
        
        if ($.cookie(self.toggleFiltersCookie) == 'in') {
            $(self.toggleFiltersButton).button('close');
        } else {
            $(self.toggleFiltersButton).button('open');
        }

        $(self.filterAccordion).on('hidden', function (data) {
            if (!(data.target && $(data.target).hasClass('modal'))) {
                _setShowFilterCookie(true);
                $(self.toggleFiltersButton).button('open');
            }
        });

        $(self.filterAccordion).on('show', function () {
            _setShowFilterCookie(true);
            $(self.toggleFiltersButton).button('close');
        });

    };

    $(self.filterAccordion).on('hqreport.filter.datespan.startdate', function(event, value) {
        self.datespan.startdate = value;
    });

    $(self.filterAccordion).on('hqreport.filter.datespan.enddate', function(event, value) {
        self.datespan.enddate = value;
    });

    self.resetFilterState = function () {
        $('#paramSelectorForm fieldset button, #paramSelectorForm fieldset span[data-dropdown="dropdown"]').click(function() {
            $('#paramSelectorForm button[type="submit"]').button('reset').addClass('btn-primary');
        });
        $('#paramSelectorForm fieldset').change(function () {
            $('#paramSelectorForm button[type="submit"]').button('reset').addClass('btn-primary');
        });
    };
};
