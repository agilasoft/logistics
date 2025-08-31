// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/* global frappe */

// logistics/warehousing/report/batch_expiry_risk/batch_expiry_risk.js
frappe.query_reports["Batch Expiry Risk"] = {
  filters: [
    {fieldname:"as_of", label:"As of Date", fieldtype:"Date", default: frappe.datetime.get_today(), reqd:1},
    {fieldname:"days", label:"Due Soon in (days) ≤", fieldtype:"Int", default: 30, reqd:1},
    {fieldname:"customer", label:"Customer", fieldtype:"Link", options:"Customer"},
    {fieldname:"item", label:"Item", fieldtype:"Link", options:"Warehouse Item",
      get_query: () => {
        const c = frappe.query_report.get_filter_value("customer");
        return c ? {filters: {customer: c}} : {};
      }
    }
  ]
};
