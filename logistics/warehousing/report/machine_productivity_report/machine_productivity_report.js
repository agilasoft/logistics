// apps/logistics/logistics/report/machine_productivity_report/machine_productivity_report.js
/* global frappe */
frappe.query_reports["Machine Productivity Report"] = {
  filters: [
    { fieldname: "from_date", label: "From Date", fieldtype: "Date", default: frappe.datetime.month_start() },
    { fieldname: "to_date", label: "To Date", fieldtype: "Date", default: frappe.datetime.get_today() },
    { fieldname: "company", label: "Company", fieldtype: "Link", options: "Company" },
    { fieldname: "branch", label: "Branch", fieldtype: "Link", options: "Branch" },
    { fieldname: "type", label: "Job Type", fieldtype: "Select",
      options: ["", "Staging In", "Staging Out", "Putaway", "Pick", "Move", "VAS", "Stocktake"].join("\n") },
    { fieldname: "customer", label: "Customer", fieldtype: "Link", options: "Customer" },
    { fieldname: "machine", label: "Machine", fieldtype: "Link", options: "Asset" },
    { fieldname: "operation", label: "Operation", fieldtype: "Link", options: "Warehouse Operation Item" },
    { fieldname: "chart_by", label: "Chart By", fieldtype: "Select", options: ["day","machine"].join("\n"), default: "day" }
  ]
};
