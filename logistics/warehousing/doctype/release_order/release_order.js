// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Release Order", {
  refresh(frm) {
    if (!frm.doc.docstatus) return;

    frm.add_custom_button(__("Warehouse Job"), () => {
      frappe.call({
        method: "logistics.warehousing.doctype.release_order.release_order.make_warehouse_job",
        args: { source_name: frm.doc.name },
        freeze: true,
        freeze_message: __("Creating Warehouse Job…"),
      }).then(({ message }) => {
        if (!message) return;
        const docs = frappe.model.sync(message);
        const doc = docs && docs[0];
        if (doc) frappe.set_route("Form", doc.doctype, doc.name);
      });
    }, __("Create"));
  },
});

//fetch rates from Contract

function _resolve_item(row){ return row.charge_item || row.item_code || row.item || row.item_charge; }
function _apply_vals(cdt, cdn, m){
  if (!m) return;
  if (typeof m.rate === "number") frappe.model.set_value(cdt, cdn, "rate", m.rate);
  if (m.currency) frappe.model.set_value(cdt, cdn, "currency", m.currency);

  // strictly use UOM from Contract
  let contract_uom = (m.storage_charge && m.billing_time_unit) ? m.billing_time_unit : (m.uom || null);
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

frappe.ui.form.on("Release Order Charges", {
  charge_item(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "outbound"); },
  item_code(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "outbound"); }
});


//Manage Planned Date

frappe.ui.form.on("Release Order", {
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

// Serial Management
frappe.ui.form.on("Release Order Item", {
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

// Recalculate a row's total = quantity * rate
function recalc_charge_total(cdt, cdn) {
  const row = locals[cdt][cdn];
  const qty  = parseFloat(row.quantity) || 0;
  const rate = parseFloat(row.rate) || 0;
  frappe.model.set_value(cdt, cdn, "total", qty * rate);
}

frappe.ui.form.on("Release Order Charges", {
  quantity(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  },
  rate(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  }
});

// When a new row is added to the charges table
frappe.ui.form.on("Release Order", {
  charges_add(frm, cdt, cdn) {   // if your table fieldname ≠ "charges", rename this to <your_fieldname>_add
    recalc_charge_total(cdt, cdn);
  },

  // Safety net: recompute all totals on validate (covers imports/paste edits)
  validate(frm) {
    (frm.doc.charges || []).forEach(row => {
      const qty  = parseFloat(row.quantity) || 0;
      const rate = parseFloat(row.rate) || 0;
      row.total = qty * rate;
    });
    frm.refresh_field("charges");
  }
});

// Child table event handlers for dimension and weight auto-population
frappe.ui.form.on('Release Order Item', {
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
            fieldname: ["default_volume_uom", "default_weight_uom"]
        },
        callback: function(r) {
            if (r.message) {
                const volume_uom = r.message.default_volume_uom;
                const weight_uom = r.message.default_weight_uom;
                if (volume_uom) {
                    frappe.model.set_value(cdt, cdn, 'volume_uom', volume_uom);
                }
                if (weight_uom) {
                    frappe.model.set_value(cdt, cdn, 'weight_uom', weight_uom);
                }
            }
        }
    });
}

function calculate_volume(frm, cdt, cdn) {
    console.log('calculate_volume called for', cdt, cdn);
    const doc = frappe.get_doc(cdt, cdn);
    const length = parseFloat(doc.length) || 0;
    const width = parseFloat(doc.width) || 0;
    const height = parseFloat(doc.height) || 0;
    
    console.log('Dimensions:', {length, width, height});
    
    if (length > 0 && width > 0 && height > 0) {
        const volume = length * width * height;
        console.log('Calculated volume:', volume);
        frappe.model.set_value(cdt, cdn, 'volume', volume);
        console.log('Volume set to:', volume);
    } else {
        console.log('Not all dimensions provided');
    }
}
