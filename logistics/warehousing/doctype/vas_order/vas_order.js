// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// VAS Order Client Script
// Adds: Create → Warehouse Job (maps VAS Order → Warehouse Job via server mapper)

frappe.ui.form.on("VAS Order", {
  refresh(frm) {
    if (frm.is_new()) return;

    // Show while Draft/Submitted (hide when Cancelled)
    if (frm.doc.docstatus < 2) {
      frm.add_custom_button(
        __("Warehouse Job"),
        () => makeWarehouseJob(frm),
        __("Create")
      );
    }
    
    // Update UOM fields for child table items
    update_uom_fields_for_items(frm);
  },
});

function makeWarehouseJob(frm) {
  // Basic guardrails
  if (!frm.doc.type) {
    frappe.msgprint({
      title: __("Missing Type"),
      message: __("Please set the VAS <b>Type</b> before creating a Warehouse Job."),
      indicator: "orange",
    });
    return;
  }
  if (!Array.isArray(frm.doc.items) || frm.doc.items.length === 0) {
    frappe.msgprint({
      title: __("No Items"),
      message: __("Add at least one <b>VAS Order Item</b> before creating a Warehouse Job."),
      indicator: "orange",
    });
    return;
  }

  // Use standard mapped-doc opener (handles fetch + route)
  frappe.model.open_mapped_doc({
    method: "logistics.warehousing.doctype.vas_order.vas_order.make_warehouse_job",
    frm: frm,
  });
}


function _resolve_item(row){ return row.charge_item || row.item_code || row.item || row.item_charge; }
function _apply_vals(cdt, cdn, m){
  if (!m) return;
  if (typeof m.rate === "number") frappe.model.set_value(cdt, cdn, "rate", m.rate);
  if (m.currency) frappe.model.set_value(cdt, cdn, "currency", m.currency);

  // strictly use UOM from Contract
  let contract_uom = (m.storage_charge && m.storage_uom) ? m.storage_uom : (m.handling_uom || null);
  if (contract_uom) {
    frappe.model.set_value(cdt, cdn, "uom", contract_uom);
  } else {
    // ensure Item default doesn't stick
    frappe.model.set_value(cdt, cdn, "uom", "");
    frappe.show_alert({message: __("No UOM set on Warehouse Contract for this charge."), indicator: "orange"});
  }
}
function _fetch(frm, cdt, cdn, context){
  const row = locals[cdt][cdn];
  const contract = frm.doc.contract;
  const item_code = _resolve_item(row);
  if (!contract || !item_code) return;
  frappe.call({
    method: "logistics.warehousing.api.get_contract_charge",
    args: { contract, item_code, context },
    callback: (r) => _apply_vals(cdt, cdn, r.message)
  });
}

frappe.ui.form.on("VAS Order Charges", {
  charge_item(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "vas"); },
  item_code(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "vas"); }
});


//Limit Items by Customer
// Outputs
(function () {
  const CHILD_TABLE = 'outputs';
  const ITEM_FIELD  = 'item';

  function set_item_query(frm) {
    if (!frm.fields_dict[CHILD_TABLE]) return;
    frm.fields_dict[CHILD_TABLE].grid.get_field(ITEM_FIELD).get_query = () => {
      const customer = frm.doc.customer || '';
      return { filters: customer ? { customer } : {} };
    };
    frm.set_query(ITEM_FIELD, CHILD_TABLE, () => {
      const customer = frm.doc.customer || '';
      return { filters: customer ? { customer } : {} };
    });
  }

  function drop_mismatched_rows(frm) {
    const customer = frm.doc.customer;
    if (!customer || !Array.isArray(frm.doc[CHILD_TABLE])) return;
    let changed = false;
    (frm.doc[CHILD_TABLE] || []).forEach(r => {
      if (r[ITEM_FIELD]) { r[ITEM_FIELD] = null; changed = true; }
    });
    if (changed) frm.refresh_field(CHILD_TABLE);
  }

  frappe.ui.form.on('VAS Order', {
    setup: set_item_query,
    refresh: set_item_query,
    customer: function (frm) {
      set_item_query(frm);
      drop_mismatched_rows(frm);
    },
  });
})();


//Limit Items by Customer
// Inputs
(function () {
  const CHILD_TABLE = 'inputs';
  const ITEM_FIELD  = 'item_code';

  function set_item_query(frm) {
    if (!frm.fields_dict[CHILD_TABLE]) return;
    frm.fields_dict[CHILD_TABLE].grid.get_field(ITEM_FIELD).get_query = () => {
      const customer = frm.doc.customer || '';
      return { filters: customer ? { customer } : {} };
    };
    frm.set_query(ITEM_FIELD, CHILD_TABLE, () => {
      const customer = frm.doc.customer || '';
      return { filters: customer ? { customer } : {} };
    });
  }

  function drop_mismatched_rows(frm) {
    const customer = frm.doc.customer;
    if (!customer || !Array.isArray(frm.doc[CHILD_TABLE])) return;
    let changed = false;
    (frm.doc[CHILD_TABLE] || []).forEach(r => {
      if (r[ITEM_FIELD]) { r[ITEM_FIELD] = null; changed = true; }
    });
    if (changed) frm.refresh_field(CHILD_TABLE);
  }

  frappe.ui.form.on('VAS Order', {
    setup: set_item_query,
    refresh: set_item_query,
    customer: function (frm) {
      set_item_query(frm);
      drop_mismatched_rows(frm);
    },
  });
})();


frappe.ui.form.on("VAS Order", {
  onload(frm) { maybe_set_planned_date(frm); },
  before_save(frm) { if (!frm.doc.planned_date) maybe_set_planned_date(frm, true); }
});

function maybe_set_planned_date(frm, force=false) {
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
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }
}

frappe.ui.form.on("VAS Order Item", {
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
  }
});

// Serial Management
frappe.ui.form.on("VAS Order Item", {
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
  }
});// Update UOM fields for child table items
function update_uom_fields_for_items(frm) {
    console.log("Auto-populating UOM fields for VAS Order Items");
    
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
                            frappe.model.set_value("VAS Order Item", item.name, "volume_uom", volume_uom);
                        }
                        if (weight_uom) {
                            frappe.model.set_value("VAS Order Item", item.name, "weight_uom", weight_uom);
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
