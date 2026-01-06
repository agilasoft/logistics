// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/* global frappe */

frappe.query_reports["Labor Productivity Report"] = {
  filters: [
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      reqd: 0,
      default: frappe.datetime.month_start()
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      reqd: 0,
      default: frappe.datetime.get_today()
    },
    {
      fieldname: "company",
      label: "Company",
      fieldtype: "Link",
      options: "Company"
    },
    {
      fieldname: "branch",
      label: "Branch",
      fieldtype: "Link",
      options: "Branch"
    },
    {
      fieldname: "type",
      label: "Job Type",
      fieldtype: "Select",
      options: ["", "Staging In", "Staging Out", "Putaway", "Pick", "Move", "VAS", "Stocktake"].join("\n")
    },
    {
      fieldname: "customer",
      label: "Customer",
      fieldtype: "Link",
      options: "Customer"
    },
    {
      fieldname: "operation",
      label: "Operation",
      fieldtype: "Link",
      options: "Warehouse Operation Item"
    },
    {
      fieldname: "handling_uom",
      label: "Handling UOM",
      fieldtype: "Link",
      options: "UOM"
    },
    {
      fieldname: "employee",
      label: "Employee",
      fieldtype: "Link",
      options: "Employee"
    },
    {
      fieldname: "min_efficiency",
      label: "Minimum Efficiency (%)",
      fieldtype: "Float",
      description: "Show only rows at or above this efficiency"
    },
    {
      fieldname: "only_variances",
      label: "Only Rows with Variance",
      fieldtype: "Check",
      default: 0
    },
    {
      fieldname: "chart_by",
      label: "Chart By",
      fieldtype: "Select",
      options: ["day", "operation"].join("\n"),
      default: "day"
    }
  ]
};
