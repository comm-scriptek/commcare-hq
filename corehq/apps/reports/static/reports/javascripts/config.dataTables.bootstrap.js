// datatable configuration.

function HQReportDataTables(options) {
    var self = this;
    self.dataTableElem = (options.dataTableElem) ? options.dataTableElem : '.datatable';
    self.paginationType = (options.paginationType) ? options.paginationType : 'bootstrap';
    self.defaultRows = (options.defaultRows) ? options.defaultRows : 10;
    self.startAtRowNum = (options.startAtRowNum) ? options.startAtRowNum : 0;

    this.render = function () {

        $('[data-datatable-highlight-closest]').each(function () {
           $(this).closest($(this).attr('data-datatable-highlight-closest')).addClass('active');
        });
        $('[data-datatable-tooltip]').each(function () {
            $(this).tooltip({
                placement: $(this).attr('data-datatable-tooltip'),
                title: $(this).attr('data-datatable-tooltip-text')
            });
        });

        var dataTablesDom = "frt<'row-fluid dataTables_control'<'span5'il><'span7'p>>";
        $(self.dataTableElem).each(function(){
            var params = {
                "sDom": dataTablesDom,
                "sPaginationType": self.paginationType,
                "iDisplayLength": self.defaultRows
            },
                sAjaxSource = $(this).data('source'),
                filter = $(this).data('filter') || false,
                aoColumns = [],
                $columns = $(this).find('tr').first().find('th'),
                i;

            if(sAjaxSource) {
                params = {
                    "sDom": dataTablesDom,
                    "sPaginationType": self.paginationType,
                    "iDisplayLength": self.defaultRows,
                    "bServerSide": true,
                    "sAjaxSource": sAjaxSource,
                    "bSort": false,
                    "bFilter": filter,
                    "fnServerParams": function ( aoData ) {
                        aoData.push({ "name" : 'individual', "value": $(this).data('individual')});
                        aoData.push({ "name" : 'group', "value": $(this).data('group')});
                        aoData.push({ "name" : 'case_type', "value": $(this).data('casetype')});
                        ufilter = $(this).data('ufilter');
                        if (ufilter) {
                            for (var i=0;i<ufilter.length;i++) {
                                aoData.push({ "name" : 'ufilter', "value": ufilter[i]});
                            }
                        }

                    }
                };
            }
            for (i = 0; i < $columns.length; i++) {
                var sortType = $($columns[i]).data('sort'),
                    sortDir = $($columns[i]).data('sortdir'),
                    column_params = {};
                if (sortType || sortDir) {
                    if (sortType)
                        column_params["sType"] = sortType;
                    if (sortDir)
                        column_params["asSorting"] = [sortDir];
                    aoColumns.push(column_params);
                } else {
                    aoColumns.push(null);
                }
            }
            params.aoColumns = aoColumns;
            $(this).dataTable(params);

            var $dataTablesFilter = $(".dataTables_filter");
            if($dataTablesFilter) {
                $("#extra-filter-info").append($dataTablesFilter);
                $dataTablesFilter.addClass("form-search");
                var $inputField = $dataTablesFilter.find("input"),
                    $inputLabel = $dataTablesFilter.find("label");

                $dataTablesFilter.append($inputField);
                $inputField.attr("id", "dataTables-filter-box");
                $inputField.addClass("search-query").addClass("input-medium");
                $inputField.attr("placeholder", "Search...");

                $inputLabel.attr("for", "dataTables-filter-box");
                $inputLabel.html($('<i />').addClass("icon-search"));
            }

            var $dataTablesLength = $(".dataTables_length"),
                $dataTablesInfo = $(".dataTables_info");
            if($dataTablesLength && $dataTablesInfo) {
                var $selectField = $dataTablesLength.find("select"),
                    $selectLabel = $dataTablesLength.find("label");

                $dataTablesLength.append($selectField);
                $selectLabel.remove();
                $selectField.children().append(" per page");
                $selectField.addClass("input-medium");
            }
        });
    };
}

$.extend( $.fn.dataTableExt.oStdClasses, {
    "sSortAsc": "header headerSortDown",
    "sSortDesc": "header headerSortUp",
    "sSortable": "header"
} );

// For sorting rows
jQuery.fn.dataTableExt.oSort['title-numeric-asc']  = function(a,b) {
    var x = a.match(/title="*(-?[0-9]+)/)[1];
    var y = b.match(/title="*(-?[0-9]+)/)[1];
    x = parseFloat( x );
    y = parseFloat( y );
    return ((x < y) ? -1 : ((x > y) ?  1 : 0));
};
jQuery.fn.dataTableExt.oSort['title-numeric-desc'] = function(a,b) {
    var x = a.match(/title="*(-?[0-9]+)/)[1];
    var y = b.match(/title="*(-?[0-9]+)/)[1];
    x = parseFloat( x );
    y = parseFloat( y );
    return ((x < y) ?  1 : ((x > y) ? -1 : 0));
};