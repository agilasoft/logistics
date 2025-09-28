// logistics/transport/doctype/transport_order/transport_order.js
frappe.ui.form.on('Transport Order', {
  refresh(frm) {
    // Show the action only when NOT submitted
    if (frm.doc.docstatus !== 1) {
      frm.add_custom_button(__('Get Leg Plan'), async () => {
        if (!frm.doc.transport_template) {
          frappe.msgprint(__('Please select a Transport Template first.'));
          return;
        }

        const run = async () => {
          frappe.call({
            method: 'logistics.transport.doctype.transport_order.transport_order.action_get_leg_plan',
            args: { docname: frm.doc.name, replace: 1, save: 1 },
            freeze: true,
            freeze_message: __('Fetching legs from Transport Template...'),
            callback: (r) => {
              if (r && r.message) {
                const { template, added, cleared } = r.message;
                frappe.show_alert({
                  message: __(`Leg Plan updated from <b>${template}</b>: cleared ${cleared}, added ${added}.`),
                  indicator: 'green'
                });
              }
              frm.reload_doc();
            }
          });
        };

        if (frm.is_dirty()) {
          await frm.save();
        }
        await run();
      }, __('Actions'));
    }
  }
});

frappe.ui.form.on('Transport Order', {
  refresh(frm) {
    // Only when submitted
    if (frm.doc.docstatus === 1) {
      frm.add_custom_button(__('Transport Job'), () => {
        frappe.call({
          method: 'logistics.transport.doctype.transport_order.transport_order.action_create_transport_job',
          args: { docname: frm.doc.name },
          freeze: true,
          freeze_message: __('Creating Transport Job...'),
          callback: (r) => {
            if (!r || !r.message) return;
            const { name, created, already_exists } = r.message;

            if (already_exists) {
              frappe.msgprint(
                __('Transport Job already exists: {0}', [name])
              );
            } else if (created) {
              frappe.show_alert({
                message: __('Transport Job {0} created.', [name]),
                indicator: 'green'
              });
            }
            frappe.set_route('Form', 'Transport Job', name);
          }
        });
      }, __('Create'));
    }
  }
});


// --- Transport Order: child (Transport Order Legs) address filters ---

const TO_LEGS_FIELD = "legs"; // change to "legs" if that's your fieldname

frappe.ui.form.on("Transport Order", {
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
frappe.ui.form.on("Transport Order Legs", {
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

// transport_order.js (or custom client script)
frappe.ui.form.on("Transport Order Legs", {
    form_render: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.scheduled_date && frm.doc.scheduled_date) {
            frappe.model.set_value(cdt, cdn, "scheduled_date", frm.doc.scheduled_date);
        }
    }
});

