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

