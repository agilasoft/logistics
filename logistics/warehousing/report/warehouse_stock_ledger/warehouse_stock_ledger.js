// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Copyright (c) 2025
// Script Report: Warehouse Stock Ledger

frappe.query_reports["Warehouse Stock Ledger"] = {
  filters: [
    {
      fieldname: "date_from",
      label: "Date From",
      fieldtype: "Date",
    },
    {
      fieldname: "date_to",
      label: "Date To",
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "customer",
      label: "Customer",
      fieldtype: "Link",
      options: "Customer",
      onchange: () => {
        // clear item when customer changes to avoid stale value
        frappe.query_report.set_filter_value("item", "");
      },
    },
    {
      fieldname: "item",
      label: "Item",
      fieldtype: "Link",
      options: "Warehouse Item",
      get_query: () => {
        const customer = frappe.query_report.get_filter_value("customer");
        return customer ? { filters: { customer: customer } } : {};
      },
    },
    {
      fieldname: "storage_location",
      label: "Storage Location",
      fieldtype: "Link",
      options: "Storage Location",
    },
    {
      fieldname: "handling_unit",
      label: "Handling Unit",
      fieldtype: "Link",
      options: "Handling Unit",
    },
    {
      fieldname: "serial_no",
      label: "Serial No",
      fieldtype: "Link",
      options: "Warehouse Serial",
    },
    {
      fieldname: "batch_no",
      label: "Batch No",
      fieldtype: "Link",
      options: "Warehouse Batch",
    },
    {
      fieldname: "warehouse_job",
      label: "Warehouse Job",
      fieldtype: "Link",
      options: "Warehouse Job",
    },
  ],
};

