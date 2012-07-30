var HQReport = function (options) {
    var self = this;
    self.domain = options.domain;
    self.datespan = options.datespan;

    self.filterAccordion = options.filterAccordion || "#reportFilters";
    self.toggleFiltersButton = options.toggleFiltersButton || "#toggle-report-filters";
    self.exportReportButton = options.exportReportButton || "#export-report-excel";
    self.baseSlug = options.baseSlug || 'reports';

    self.toggleFiltersCookie = self.domain+'.hqreport.toggleFilterState';
    self.datespanCookie = self.domain+".hqreport.filterSetting.test.datespan";
    self.globalSavePath = '/a/'+self.domain+'/';

    self.initialLoad = true;

    self.init = function () {
        $(function () {
            checkFilterAccordionToggleState();

            $(self.exportReportButton).click(function () {
                var params = window.location.search.substr(1);
                if (params.length <= 1) {
                    if (self.loadDatespanFromCookie()) {
                        params = "startdate="+self.datespan.startdate+
                            "&enddate="+self.datespan.enddate;
                    }
                }
                window.location.href = window.location.pathname.replace('/'+self.baseSlug+'/',
                    '/'+self.baseSlug+'/export/')+"?"+params;
            });

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
                {path: self.globalSavePath, expires: 1});
            $.cookie(self.datespanCookie+'.enddate', self.datespan.enddate,
                {path: self.globalSavePath, expires: 1});
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
        $(self.filterAccordion).addClass($.cookie(self.toggleFiltersCookie));

        if ($.cookie(self.toggleFiltersCookie) == 'in')
            $(self.toggleFiltersButton).button('hide');
        else
            $(self.toggleFiltersButton).button('show');

        $(self.filterAccordion).on('hidden', function () {
            $.cookie(self.toggleFiltersCookie, '', {path: self.globalSavePath, expires: 1});
            $(self.toggleFiltersButton).button('show');
        });

        $(self.filterAccordion).on('show', function () {
            $.cookie(self.toggleFiltersCookie, 'in', {path: self.globalSavePath, expires: 1});
            $(self.toggleFiltersButton).button('hide');
        })
    };

    $(self.filterAccordion).on('hqreport.filter.datespan.startdate', function(event, value) {
        self.datespan.startdate = value;
    });

    $(self.filterAccordion).on('hqreport.filter.datespan.enddate', function(event, value) {
        self.datespan.enddate = value;
    });


};