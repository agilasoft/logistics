// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/* global frappe */
frappe.query_reports["Warehouse Stock Balance"] = {
  filters: [
    { fieldname: "from_date", label: "From Date", fieldtype: "Date", reqd: 1,
      default: frappe.datetime.add_days(frappe.datetime.get_today(), -30) },
    { fieldname: "to_date", label: "To Date", fieldtype: "Date", reqd: 1,
      default: frappe.datetime.get_today() },

    // Customer filter
    { fieldname: "customer", label: "Customer", fieldtype: "Link", options: "Customer",
      on_change() {
        // prevent mismatched selections; clear Item when Customer changes
        frappe.query_report.set_filter_value("item", null);
      }
    },

    // Item is limited by selected Customer
    { fieldname: "item", label: "Item", fieldtype: "Link", options: "Warehouse Item",
      get_query() {
        const customer = frappe.query_report.get_filter_value("customer");
        return customer ? { filters: { customer } } : {};
      }
    },

    { fieldname: "storage_location", label: "Storage Location", fieldtype: "Link", options: "Storage Location" },
    { fieldname: "handling_unit", label: "Handling Unit", fieldtype: "Link", options: "Handling Unit" }
  ]
};
