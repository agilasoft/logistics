// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// ---------------------------- Inbound Order (Parent) ----------------------------
frappe.ui.form.on('Inbound Order', {
  refresh(frm) {
    // Populate Documents from Template
    if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
      frm.add_custom_button(__('Populate from Template'), function() {
        frappe.call({
          method: 'logistics.document_management.api.populate_documents_from_template',
          args: { doctype: 'Inbound Order', docname: frm.doc.name },
          callback: function(r) {
            if (r.message && r.message.added !== undefined) {
              frm.reload_doc();
              frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
            }
          }
        });
      }, __('Documents'));
    }

    // Create → Warehouse Job button (only when submitted)
    if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
      frm.add_custom_button(
        __('Warehouse Job'),
        function () {
          frappe.model.open_mapped_doc({
            method: "logistics.warehousing.doctype.inbound_order.inbound_order.make_warehouse_job",
            frm: frm
          });
        },
        __('Create')
      );
    }

    // Create → Serials & Batches manual button (when not new)
    if (!frm.is_new()) {
      frm.add_custom_button(
        __('Serials & Batches'),
        () => run_serials_and_batches(frm, { show_summary: true }),
        __('Create')
      );
    }
    
    // Update UOM fields for child table items
    update_uom_fields_for_items(frm);
  },

  onload(frm) {
    maybe_set_planned_date(frm);
  },

  before_save(frm) {
    if (!frm.doc.planned_date) maybe_set_planned_date(frm, true);
  },

  // Auto-run Serials & Batches right before submit
  // (ensures newly typed serial/batch text is materialized/linked at submission)
  async before_submit(frm) {
    await run_serials_and_batches(frm, { show_summary: false, throw_on_error: true });
  },

  // When a new row is added to the charges table, initialize total
  // NOTE: If your table fieldname ≠ "charges", rename this event to <your_fieldname>_add
  charges_add(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  },

  // Safety net: recompute all charge totals on validate (covers paste/import edits)
  validate(frm) {
    (frm.doc.charges || []).forEach(row => {
      const qty  = parseFloat(row.quantity) || 0;
      const rate = parseFloat(row.rate) || 0;
      row.total = qty * rate;
    });
    frm.refresh_field("charges");
  },

  contract(frm) {
    // Populate shipper and consignee from Warehouse Contract
    if (frm.doc.contract) {
      frappe.db.get_value("Warehouse Contract", frm.doc.contract, ["shipper", "consignee"], function(r) {
        if (r) {
          if (r.shipper) {
            frm.set_value("shipper", r.shipper);
          }
          if (r.consignee) {
            frm.set_value("consignee", r.consignee);
          }
        }
      });
    } else {
      // Clear shipper and consignee if contract is cleared
      frm.set_value("shipper", "");
      frm.set_value("consignee", "");
    }
  }
});

// ---------------------------- Contract Charge Helpers ----------------------------
function _resolve_item(row) {
  return row.charge_item || row.item_code || row.item || row.item_charge;
}

function _apply_vals(cdt, cdn, m) {
  if (!m) return;

  if (typeof m.rate === "number") frappe.model.set_value(cdt, cdn, "rate", m.rate);
  if (m.currency) frappe.model.set_value(cdt, cdn, "currency", m.currency);

  // Use UOM from Contract
  if (m.uom) {
    frappe.model.set_value(cdt, cdn, "uom", m.uom);
  } else {
    // Fallback to item's default UOM if no contract UOM found
    const row = locals[cdt][cdn];
    if (row.item) {
      frappe.call({
        method: "frappe.client.get_value",
        args: {
          doctype: "Warehouse Item",
          name: row.item,
          fieldname: ["uom"]
        },
        callback: function(item_r) {
          if (item_r.message && item_r.message.uom) {
            frappe.model.set_value(cdt, cdn, "uom", item_r.message.uom);
          }
        }
      });
    }
  }
}

function _fetch(frm, cdt, cdn, context) {
  const row = locals[cdt][cdn];
  const contract = frm.doc.contract;
  const item_code = _resolve_item(row);
  if (!contract || !item_code) return;

  frappe.call({
    method: "logistics.warehousing.api.get_contract_charge",
    args: { contract, item_code, context },
  }).then(r => _apply_vals(cdt, cdn, r.message));
}

frappe.ui.form.on("Inbound Order Charges", {
  charge_item(frm, cdt, cdn) { _fetch(frm, cdt, cdn, "inbound"); },
  item_code(frm, cdt, cdn)  { _fetch(frm, cdt, cdn, "inbound"); },

  // auto-calc total when editing charge lines
  quantity(frm, cdt, cdn)   { recalc_charge_total(cdt, cdn); },
  rate(frm, cdt, cdn)       { recalc_charge_total(cdt, cdn); },
});

// ---------------------------- Serials & Batches ----------------------------
async function run_serials_and_batches(frm, opts = {}) {
  const { show_summary = true, throw_on_error = false } = opts;

  // quick escape if no items
  if (!(frm.doc.items || []).length) return;

  try {
    const r = await frappe.call({
      method: 'logistics.warehousing.api.create_serial_and_batch_for_inbound',
      args: { inbound_order: frm.doc.name },
      freeze: true,
      freeze_message: __('Creating / linking Serials & Batches...'),
    });

    const m = r.message || {};
    if (show_summary) {
      const summary = [
        __('Created Serials: {0}', [m.created?.serial || 0]),
        __('Created Batches: {0}', [m.created?.batch || 0]),
        __('Linked Serials: {0}', [m.linked?.serial || 0]),
        __('Linked Batches: {0}', [m.linked?.batch || 0]),
        __('Skipped: {0}', [m.skipped || 0]),
        (m.errors && m.errors.length ? __('Errors: {0}', [m.errors.length]) : '')
      ].filter(Boolean).join('<br>');
      frappe.msgprint({ title: __('Serials & Batches'), message: summary, indicator: (m.errors?.length ? 'orange' : 'blue') });
    }

    // Always reload to reflect any created/linked records
    await frm.reload_doc();

    // If we’re in before_submit and there were errors, block submission
    if (throw_on_error && m.errors && m.errors.length) {
      frappe.throw(__('Could not finalize Serials & Batches. Please review the items and try again.'));
    }
  } catch (e) {
    if (throw_on_error) {
      // Block submit with a clear error
      frappe.throw(__('Failed to create/link Serials & Batches: {0}', [e.message || e]));
    } else {
      frappe.msgprint({
        title: __('Serials & Batches'),
        message: __('Failed to create/link: {0}', [e.message || e]),
        indicator: 'red'
      });
    }
  }
}

// ---------------------------- Planned Date Helper ----------------------------
function maybe_set_planned_date(frm, force = false) {
  if (!force && (frm.doc.planned_date || frm.__planned_date_set)) return;

  frappe.db.get_value("Warehouse Settings", frappe.defaults.get_user_default("Company"), "planned_date_offset_days")
    .then((val) => {
      const offset = parseInt(val, 10) || 0;
      const nowStr = frappe.datetime.now_datetime(); // "YYYY-MM-DD HH:mm:ss"
      const planned = addDaysPreserveTime(nowStr, offset);
      frm.set_value("planned_date", planned);
      frm.__planned_date_set = true;
    })
    .catch(() => {
      frm.set_value("planned_date", frappe.datetime.now_datetime());
      frm.__planned_date_set = true;
    });
}

function addDaysPreserveTime(baseStr, days) {
  if (window.dayjs) {
    return window.dayjs(baseStr).add(days, "day").format("YYYY-MM-DD HH:mm:ss");
  } else if (window.moment) {
    return window.moment(baseStr, "YYYY-MM-DD HH:mm:ss").add(days, "days").format("YYYY-MM-DD HH:mm:ss");
  } else {
    // Pure JS fallback
    const d = new Date(baseStr.replace(" ", "T"));
    d.setDate(d.getDate() + days);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }
}

// ---------------------------- Charges Math ----------------------------
function recalc_charge_total(cdt, cdn) {
  const row  = locals[cdt][cdn];
  const qty  = parseFloat(row.quantity) || 0;
  const rate = parseFloat(row.rate) || 0;
  frappe.model.set_value(cdt, cdn, "total", qty * rate);
}

// ---------------------------- Inbound Order Item rules ----------------------------
frappe.ui.form.on("Inbound Order Item", {
  serial_tracking(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.serial_tracking) {
      frappe.model.set_value(cdt, cdn, "quantity", 1);
    }
    // ensure grid re-evaluates read_only_depends_on per row
    frm.fields_dict.items.grid.refresh();
  },

  quantity(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.serial_tracking && row.quantity != 1) {
      frappe.model.set_value(cdt, cdn, "quantity", 1);
      frappe.show_alert(__("Serial-tracked items must have Quantity = 1"));
    }
  },

  item(frm, cdt, cdn) {
    // When item is selected, fetch UOM from warehouse contract using existing pattern
    _fetch(frm, cdt, cdn, "inbound");
  }
});

// Update UOM fields for child table items
function update_uom_fields_for_items(frm) {
    console.log("Auto-populating UOM fields for Inbound Order Items");
    
    // Get UOM values from Warehouse Settings
    const company = frappe.defaults.get_user_default("Company");
    console.log("Company:", company);
    
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Warehouse Settings",
            name: company,
            fieldname: ["default_volume_uom", "default_weight_uom"]
        },
        callback: function(r) {
            console.log("UOM response:", r);
            if (r.message) {
                const volume_uom = r.message.default_volume_uom;
                const weight_uom = r.message.default_weight_uom;
                console.log("Volume UOM:", volume_uom, "Weight UOM:", weight_uom);
                
                // Update UOM fields for all items in the child table
                if (frm.doc.items && frm.doc.items.length > 0) {
                    frm.doc.items.forEach(function(item, index) {
                        if (volume_uom) {
                            frappe.model.set_value("Inbound Order Item", item.name, "volume_uom", volume_uom);
                        }
                        if (weight_uom) {
                            frappe.model.set_value("Inbound Order Item", item.name, "weight_uom", weight_uom);
                        }
                    });
                    frm.refresh_field("items");
                    console.log("Updated UOM fields for", frm.doc.items.length, "items");
                } else {
                    console.log("No items found in the order");
                }
            } else {
                console.log("No UOM message received");
            }
        }
    });
}

// Child table event handlers for dimension and weight auto-population
frappe.ui.form.on('Inbound Order Item', {
    refresh: function(frm, cdt, cdn) {
        update_uom_fields(frm, cdt, cdn);
    },
    length: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    width: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    height: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    dimension_uom: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    },
    volume_uom: function(frm, cdt, cdn) {
        calculate_volume(frm, cdt, cdn);
    }
});

// Helper functions for dimension and weight auto-population
function update_uom_fields(frm, cdt, cdn) {
    const company = frappe.defaults.get_user_default("Company");
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Warehouse Settings",
            name: company,
            fieldname: ["default_volume_uom", "default_weight_uom", "default_dimension_uom"]
        },
        callback: function(r) {
            if (r.message) {
                const volume_uom = r.message.default_volume_uom;
                const weight_uom = r.message.default_weight_uom;
                const dimension_uom = r.message.default_dimension_uom;
                if (volume_uom) {
                    frappe.model.set_value(cdt, cdn, 'volume_uom', volume_uom);
                }
                if (weight_uom) {
                    frappe.model.set_value(cdt, cdn, 'weight_uom', weight_uom);
                }
                if (dimension_uom) {
                    frappe.model.set_value(cdt, cdn, 'dimension_uom', dimension_uom);
                }
            }
        }
    });
}

function calculate_volume(frm, cdt, cdn) {
    const doc = frappe.get_doc(cdt, cdn);
    const length = parseFloat(doc.length) || 0;
    const width = parseFloat(doc.width) || 0;
    const height = parseFloat(doc.height) || 0;
    
    if (length > 0 && width > 0 && height > 0) {
        // Get UOMs from child document or warehouse settings
        const dimension_uom = doc.dimension_uom;
        const volume_uom = doc.volume_uom;
        const company = frappe.defaults.get_user_default("Company");
        
        // Call server-side method to calculate volume with UOM conversion
        frappe.call({
            method: "logistics.warehousing.doctype.warehouse_settings.warehouse_settings.calculate_volume_from_dimensions",
            args: {
                length: length,
                width: width,
                height: height,
                dimension_uom: dimension_uom,
                volume_uom: volume_uom,
                company: company
            },
            callback: function(r) {
                if (r.message && r.message.volume !== undefined) {
                    frappe.model.set_value(cdt, cdn, 'volume', r.message.volume);
                }
            },
            error: function(r) {
                const volume = 0;
                frappe.model.set_value(cdt, cdn, 'volume', volume);
            }
        });
    } else {
        frappe.model.set_value(cdt, cdn, 'volume', 0);
    }
}
