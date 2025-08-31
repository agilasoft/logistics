// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/* eslint-disable */

/* global frappe */

frappe.query_reports["Storage Location Usage"] = {
  filters: [
    {
      fieldname: "site",
      label: "Site",
      fieldtype: "Link",
      options: "Storage Location Configurator",
      get_query: () => ({ filters: { level: "Site" } }),
      width: "120px",
    },
    {
      fieldname: "building",
      label: "Building",
      fieldtype: "Link",
      options: "Storage Location Configurator",
      get_query: () => ({ filters: { level: "Building" } }),
      width: "120px",
    },
    {
      fieldname: "zone",
      label: "Zone",
      fieldtype: "Link",
      options: "Storage Location Configurator",
      get_query: () => ({ filters: { level: "Zone" } }),
      width: "110px",
    },
    {
      fieldname: "aisle",
      label: "Aisle",
      fieldtype: "Link",
      options: "Storage Location Configurator",
      get_query: () => ({ filters: { level: "Aisle" } }),
      width: "90px",
    },
    {
      fieldname: "bay",
      label: "Bay",
      fieldtype: "Link",
      options: "Storage Location Configurator",
      get_query: () => ({ filters: { level: "Bay" } }),
      width: "90px",
    },
    {
      fieldname: "level",
      label: "Level",
      fieldtype: "Link",
      options: "Storage Location Configurator",
      get_query: () => ({ filters: { level: "Level" } }),
      width: "90px",
    },
    {
      fieldname: "storage_type",
      label: "Storage Type",
      fieldtype: "Link",
      options: "Storage Type",
      width: "140px",
    },
  ],

  // Fallback so Prepared Reports still render the chart client-side
  get_chart_data: function (_columns, rows) {
    const isInUse = (v) => (v === 1 || v === "1" || v === true || v === "Yes" || v === "Y" || v === "In Use");

    const total = (rows || []).length;
    const in_use = (rows || []).reduce((n, r) => n + (isInUse(r.in_use) ? 1 : 0), 0);
    const available = Math.max(total - in_use, 0);

    return {
      data: {
        labels: ["In Use", "Available"],
        datasets: [{ name: "Locations", values: [in_use, available] }],
      },
      type: "donut",
      height: 260,
    };
  },
};
