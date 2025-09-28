// Copyright (c) 2021, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Job', {
  refresh(frm) {
    const canShow = frm.doc.docstatus === 1; // only when submitted
    if (!canShow) return;

    frm.add_custom_button('Run Sheet', () => open_create_run_sheet_dialog(frm), 'Create');
  }
});

function open_create_run_sheet_dialog(frm) {
  // ask server for available vehicles (filtered by job.vehicle_type if present)
  frappe.call({
    method: 'logistics.transport.doctype.transport_job.transport_job.get_available_vehicles',
    args: {
      jobname: frm.doc.name
    }
  }).then(r => {
    const vehicles = (r && r.message && r.message.vehicles) || [];
    if (vehicles.length) {
      // Let user select a vehicle (and optional driver/company)
      const fields = [
        {
          fieldname: 'vehicle',
          label: 'Vehicle',
          fieldtype: 'Select',
          reqd: 1,
          options: vehicles.map(v => v.name).join('\n')
        },
        { fieldname: 'driver', label: 'Driver', fieldtype: 'Link', options: 'Driver' },
        { fieldname: 'transport_company', label: 'Transport Company', fieldtype: 'Link', options: 'Transport Company' }
      ];
      // Pre-fill from job if available
      const defaults = {};
      if (frm.doc.driver) defaults.driver = frm.doc.driver;
      if (frm.doc.transport_company) defaults.transport_company = frm.doc.transport_company;

      frappe.prompt(fields, (v) => {
        create_run_sheet_from_job(frm, {
          vehicle: v.vehicle,
          driver: v.driver || null,
          transport_company: v.transport_company || null
        });
      }, 'Create Run Sheet', 'Create', defaults);
    } else {
      // No vehicles free — ask only for Transport Company and proceed
      frappe.prompt([
        { fieldname: 'transport_company', label: 'Transport Company', fieldtype: 'Link', options: 'Transport Company', reqd: 1 },
        { fieldname: 'note', label: 'Note', fieldtype: 'Small Text', description: 'No available vehicle found. A Run Sheet will be created in Draft for later assignment.' }
      ], (v) => {
        create_run_sheet_from_job(frm, {
          vehicle: null,
          driver: null,
          transport_company: v.transport_company
        });
      }, 'No Vehicle Available');
    }
  });
}

function create_run_sheet_from_job(frm, payload) {
  frappe.call({
    method: 'logistics.transport.doctype.transport_job.transport_job.action_create_run_sheet',
    args: {
      jobname: frm.doc.name,
      vehicle: payload.vehicle,
      driver: payload.driver,
      transport_company: payload.transport_company
    },
    freeze: true,
    freeze_message: __('Creating Run Sheet …'),
  }).then(r => {
    const msg = r.message || {};
    if (msg.name) {
      frappe.msgprint(__('Run Sheet {0} created with {1} leg(s).', [msg.name, msg.legs_added || 0]));
      frappe.set_route('Form', 'Run Sheet', msg.name);
    }
  });
}

// --- Transport Job: child (Transport Job Legs) address filters ---

const TO_LEGS_FIELD = "legs"; // change to "legs" if that's your fieldname

frappe.ui.form.on("Transport Job", {
  setup(frm) {
    bind_leg_address_queries(frm);
  },
  refresh(frm) {
    bind_leg_address_queries(frm);
  },
});

function bind_leg_address_queries(frm) {
  // Pick Address: filter by (facility_type_from, facility_from)
  frm.set_query("pick_address", TO_LEGS_FIELD, function (doc, cdt, cdn) {
    const row = locals[cdt][cdn] || {};
    if (row.facility_type_from && row.facility_from) {
      return {
        filters: {
          link_doctype: row.facility_type_from,
          link_name: row.facility_from,
        },
      };
    }
    // block selection until a facility is chosen
    return { filters: { name: "__none__" } };
  });

  // Drop Address: filter by (facility_type_to, facility_to)
  frm.set_query("drop_address", TO_LEGS_FIELD, function (doc, cdt, cdn) {
    const row = locals[cdt][cdn] || {};
    if (row.facility_type_to && row.facility_to) {
      return {
        filters: {
          link_doctype: row.facility_type_to,
          link_name: row.facility_to,
        },
      };
    }
    return { filters: { name: "__none__" } };
  });
}

// Optional: clear addresses if related facility changes (prevents stale values)
frappe.ui.form.on("Transport Job Legs", {
  facility_type_from(frm, cdt, cdn) {
    frappe.model.set_value(cdt, cdn, "pick_address", null);
    frappe.model.set_value(cdt, cdn, "pick_address_html", "");
  },
  facility_from(frm, cdt, cdn) {
    frappe.model.set_value(cdt, cdn, "pick_address", null);
    frappe.model.set_value(cdt, cdn, "pick_address_html", "");
  },
  facility_type_to(frm, cdt, cdn) {
    frappe.model.set_value(cdt, cdn, "drop_address", null);
    frappe.model.set_value(cdt, cdn, "drop_address_html", "");
  },
  facility_to(frm, cdt, cdn) {
    frappe.model.set_value(cdt, cdn, "drop_address", null);
    frappe.model.set_value(cdt, cdn, "drop_address_html", "");
  },

  // When an address is picked, format HTML using ERPNext's formatter
  pick_address(frm, cdt, cdn) {
    format_row_address_html(cdt, cdn, "pick_address", "pick_address_html");
  },
  drop_address(frm, cdt, cdn) {
    format_row_address_html(cdt, cdn, "drop_address", "drop_address_html");
  },
});

function format_row_address_html(cdt, cdn, addr_field, html_field) {
  const row = locals[cdt][cdn];
  const addr = row[addr_field];
  if (!addr) {
    frappe.model.set_value(cdt, cdn, html_field, "");
    return;
  }
  frappe.call({
    method: "frappe.contacts.doctype.address.address.get_address_display",
    args: { address_dict: addr }, // accepts name or dict
    callback: (r) => {
      frappe.model.set_value(cdt, cdn, html_field, r.message || "");
    },
  });
}
