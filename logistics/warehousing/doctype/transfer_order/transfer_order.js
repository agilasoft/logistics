// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transfer Order', {
  refresh(frm) {
    // Create → Warehouse Job (available for draft/submitted TO; adjust as you prefer)
    if (frm.doc.docstatus == 1) {
      frm.add_custom_button(
        __('Warehouse Job'),
        () => make_warehouse_job_from_to(frm),
        __('Create')
      );
    }
  }
});

function make_warehouse_job_from_to(frm) {
  frappe.model.open_mapped_doc({
    method: 'logistics.warehousing.doctype.transfer_order.transfer_order.make_warehouse_job',
    frm: frm
  });
}


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

frappe.ui.form.on("Transfer Order Charges", {
  charge_item(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "transfer"); },
  item_code(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "transfer"); }
});


//Limit Items by Customer
// Doctype: Transfer Order
(function () {
  const CHILD_TABLE = 'items';
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

  frappe.ui.form.on('Transfer Order', {
    setup: set_item_query,
    refresh: set_item_query,
    customer: function (frm) {
      set_item_query(frm);
      drop_mismatched_rows(frm);
    },
  });
})();


// Manage Planned Date

frappe.ui.form.on("Transfer Order", {
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

frappe.ui.form.on("Transfer Order Item", {
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

frappe.ui.form.on("Transfer Order Charges", {
  quantity(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  },
  rate(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  }
});

// When a new row is added to the charges table
frappe.ui.form.on("Transfer Order", {
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

// Serial Management
frappe.ui.form.on("Transfer Order Item", {
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