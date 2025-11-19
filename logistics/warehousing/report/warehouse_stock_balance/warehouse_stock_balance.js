// Copyright (c) 2025, www.agilasoft.com
// For license information, please see license.txt

/* global frappe */
frappe.query_reports["Warehouse Stock Balance"] = {
  filters: [
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },

    // Customer filter
    {
      fieldname: "customer",
      label: "Customer",
      fieldtype: "Link",
      options: "Customer",
      on_change() {
        // prevent mismatched selections; clear Item when Customer changes
        frappe.query_report.set_filter_value("item", null);
      },
    },

    // Item limited by selected Customer
    {
      fieldname: "item",
      label: "Item",
      fieldtype: "Link",
      options: "Warehouse Item",
      get_query() {
        const customer = frappe.query_report.get_filter_value("customer");
        return customer ? { filters: { customer } } : {};
      },
    },

    { fieldname: "storage_location", label: "Storage Location", fieldtype: "Link", options: "Storage Location" },
    { fieldname: "handling_unit",    label: "Handling Unit",    fieldtype: "Link", options: "Handling Unit" },
    {
      fieldname: "group_by",
      label: "Group By",
      fieldtype: "Select",
      options: "\nItem Only\nStorage Location and Handling Unit",
      default: "Item Only",
    },
  ],

  // Make Item cell clickable → open Warehouse Stock Ledger with same dates + item (+customer if any)
  formatter(value, row, column, data, default_formatter) {
    const rendered = default_formatter(value, row, column, data);
    if (column.fieldname !== "item" || !data || !data.item) return rendered;

    const from_date = frappe.query_report.get_filter_value("from_date") || "";
    const to_date   = frappe.query_report.get_filter_value("to_date") || "";
    const customer  = frappe.query_report.get_filter_value("customer") || null;
    const item      = String(data.item);

    const payload = { date_from: from_date, date_to: to_date, item };
    if (customer) payload.customer = customer;

    const store_and_go = `
      try {
        sessionStorage.setItem('WSL_PREFILL', JSON.stringify(${JSON.stringify(payload)}));
      } catch(e) {}
      frappe.set_route('query-report', 'Warehouse Stock Ledger');
    `;

    return `<a href="javascript:void(0)" onclick="${store_and_go}">${frappe.utils.escape_html(item)}</a>`;
  },
};
