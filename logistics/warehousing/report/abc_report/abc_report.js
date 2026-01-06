// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["ABC Report"] = {
  filters: [
    {fieldname:"from_date", label:"From Date", fieldtype:"Date", reqd:1,
     default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)},
    {fieldname:"to_date", label:"To Date", fieldtype:"Date", reqd:1,
     default: frappe.datetime.get_today()},

    {fieldname:"customer", label:"Customer", fieldtype:"Link", options:"Customer"},

    {
      fieldname:"item", label:"Item", fieldtype:"Link", options:"Warehouse Item",
      get_query: () => {
        const cust = frappe.query_report.get_filter_value("customer");
        return cust ? {filters: {customer: cust}} : {};
      }
    },

    {fieldname:"basis", label:"Classification Basis", fieldtype:"Select",
     options: ["Turns Thresholds", "Cumulative % of Issues"], default: "Turns Thresholds"},

    // For "Turns Thresholds"
    {fieldname:"a_turns_min", label:"A Class: turns ≥", fieldtype:"Float", default: 4},
    {fieldname:"b_turns_min", label:"B Class: turns ≥", fieldtype:"Float", default: 2},

    // For "Cumulative % of Issues"
    {fieldname:"a_cutoff", label:"A Cutoff %", fieldtype:"Float", default: 80},
    {fieldname:"b_cutoff", label:"B Cutoff %", fieldtype:"Float", default: 95}
  ],

  onload: function(report) {
    report.page.add_inner_button(__("Update ABC Classification"), function() {
      const f = report.get_values();
      frappe.confirm(
        __("This will write the suggested ABC class into Warehouse Item. Continue?"),
        () => {
          frappe.call({
            method: "logistics.warehousing.report.abc_report.abc_report.update_abc_classification",
            args: { filters: f },
            freeze: true,
            freeze_message: __("Updating ABC classes…"),
            callback: (r) => {
              if (!r.exc) {
                const n = (r.message && r.message.updated) || 0;
                frappe.msgprint(__("Updated ABC class for {0} items.", [n]));
              }
            }
          });
        }
      );
    });
  }
};
