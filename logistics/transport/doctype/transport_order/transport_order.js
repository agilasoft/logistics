// logistics/transport/doctype/transport_order/transport_order.js
frappe.ui.form.on('Transport Order', {
  setup(frm) {
    bind_leg_address_queries(frm);
  },
  
  refresh(frm) {
    bind_leg_address_queries(frm);
    
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
              
              // Auto-fill transport_job_type and vehicle_type to all legs after reload
              setTimeout(() => {
                if (frm.doc.transport_job_type || frm.doc.vehicle_type) {
                  frm.doc.legs.forEach((leg) => {
                    if (frm.doc.transport_job_type && !leg.transport_job_type) {
                      frappe.model.set_value("Transport Order Legs", leg.name, "transport_job_type", frm.doc.transport_job_type);
                    }
                    if (frm.doc.vehicle_type && !leg.vehicle_type) {
                      frappe.model.set_value("Transport Order Legs", leg.name, "vehicle_type", frm.doc.vehicle_type);
                    }
                  });
                }
              }, 500); // Small delay to ensure reload is complete
            }
          });
        };

        if (frm.is_dirty()) {
          await frm.save();
        }
        await run();
      }, __('Actions'));
      
      // Add button to apply parent values to all legs
      frm.add_custom_button(__('Apply Parent Values to All Legs'), () => {
        if (!frm.doc.legs || frm.doc.legs.length === 0) {
          frappe.msgprint(__('No legs found. Please add legs first.'));
          return;
        }
        
        let updated = 0;
        frm.doc.legs.forEach((leg) => {
          let changed = false;
          
          // Apply transport_job_type if parent has it and leg doesn't
          if (frm.doc.transport_job_type && !leg.transport_job_type) {
            frappe.model.set_value("Transport Order Legs", leg.name, "transport_job_type", frm.doc.transport_job_type);
            changed = true;
          }
          
          // Apply vehicle_type if parent has it and leg doesn't
          if (frm.doc.vehicle_type && !leg.vehicle_type) {
            frappe.model.set_value("Transport Order Legs", leg.name, "vehicle_type", frm.doc.vehicle_type);
            changed = true;
          }
          
          if (changed) updated++;
        });
        
        if (updated > 0) {
          frappe.show_alert({
            message: __(`Applied parent values to ${updated} leg(s).`),
            indicator: 'green'
          });
        } else {
          frappe.msgprint(__('All legs already have values or parent values are not set.'));
        }
      }, __('Actions'));
    }
    
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
  },
  
  // Auto-fill transport_job_type to all existing legs when parent changes
  transport_job_type(frm) {
    if (frm.doc.transport_job_type && frm.doc.legs) {
      frm.doc.legs.forEach((leg, index) => {
        if (!leg.transport_job_type) {
          frappe.model.set_value("Transport Order Legs", leg.name, "transport_job_type", frm.doc.transport_job_type);
        }
      });
    }
  },
  
  // Auto-fill vehicle_type to all existing legs when parent changes
  vehicle_type(frm) {
    if (frm.doc.vehicle_type && frm.doc.legs) {
      frm.doc.legs.forEach((leg, index) => {
        if (!leg.vehicle_type) {
          frappe.model.set_value("Transport Order Legs", leg.name, "vehicle_type", frm.doc.vehicle_type);
        }
      });
    }
  },
  
  // Validate pick_mode and drop_mode before submission
  before_submit(frm) {
    if (!frm.doc.legs || frm.doc.legs.length === 0) {
      frappe.throw(__('Transport Order must have at least one leg. Please add transport legs before submitting.'));
    }
    
    let missing_fields = [];
    frm.doc.legs.forEach((leg, index) => {
      const row_num = index + 1;
      if (!leg.pick_mode) {
        missing_fields.push(__('Row {0}: Pick Mode is required', [row_num]));
      }
      if (!leg.drop_mode) {
        missing_fields.push(__('Row {0}: Drop Mode is required', [row_num]));
      }
    });
    
    if (missing_fields.length > 0) {
      frappe.throw(__('Please fill in the following required fields before submitting:<br><br>') + 
                   missing_fields.join('<br>'));
    }
  }
});


// --- Transport Order: child (Transport Order Legs) address filters ---

const TO_LEGS_FIELD = "legs"; // change to "legs" if that's your fieldname

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
    
    // Auto-fill pick address from facility
    auto_fill_address_from_facility(cdt, cdn, "pick");
  },
  facility_type_to(frm, cdt, cdn) {
    frappe.model.set_value(cdt, cdn, "drop_address", null);
    frappe.model.set_value(cdt, cdn, "drop_address_html", "");
  },
  facility_to(frm, cdt, cdn) {
    frappe.model.set_value(cdt, cdn, "drop_address", null);
    frappe.model.set_value(cdt, cdn, "drop_address_html", "");
    
    // Auto-fill drop address from facility
    auto_fill_address_from_facility(cdt, cdn, "drop");
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
        
        // Auto-fill transport_job_type from parent
        if (!row.transport_job_type && frm.doc.transport_job_type) {
            frappe.model.set_value(cdt, cdn, "transport_job_type", frm.doc.transport_job_type);
        }
        
        // Auto-fill vehicle_type from parent
        if (!row.vehicle_type && frm.doc.vehicle_type) {
            frappe.model.set_value(cdt, cdn, "vehicle_type", frm.doc.vehicle_type);
        }
    }
});

// Auto-fill address from facility
function auto_fill_address_from_facility(cdt, cdn, direction) {
    const row = locals[cdt][cdn];
    const facility_type = direction === "pick" ? row.facility_type_from : row.facility_type_to;
    const facility_name = direction === "pick" ? row.facility_from : row.facility_to;
    const address_field = direction === "pick" ? "pick_address" : "drop_address";
    const mode_field = direction === "pick" ? "pick_mode" : "drop_mode";
    
    if (facility_type && facility_name) {
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: facility_type,
                name: facility_name
            },
            callback: function(r) {
                if (r && r.message && r.message.address) {
                    frappe.model.set_value(cdt, cdn, address_field, r.message.address);
                    frappe.model.set_value(cdt, cdn, mode_field, "Address");
                    
                    // Format the address HTML
                    const html_field = direction === "pick" ? "pick_address_html" : "drop_address_html";
                    format_row_address_html(cdt, cdn, address_field, html_field);
                }
            }
        });
    }
}

