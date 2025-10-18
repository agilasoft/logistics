// Copyright (c) 2025,
// www.agilasoft.com. For license information, please see license.txt

// -----------------------------------------------------------------------------
// Contract Charge helpers (Stocktake Order Charges child)
// -----------------------------------------------------------------------------
function _resolve_item(row) {
  return row.charge_item || row.item_code || row.item || row.item_charge;
}
function _apply_vals(cdt, cdn, m) {
  if (!m) return;
  if (typeof m.rate === "number") frappe.model.set_value(cdt, cdn, "rate", m.rate);
  if (m.currency) frappe.model.set_value(cdt, cdn, "currency", m.currency);

  // strictly use UOM from Contract
  const contract_uom = (m.storage_charge && m.billing_time_unit) ? m.billing_time_unit : (m.uom || null);
  if (contract_uom) {
    frappe.model.set_value(cdt, cdn, "uom", contract_uom);
  } else {
    frappe.model.set_value(cdt, cdn, "uom", "");
    frappe.show_alert({ message: __("No UOM set on Warehouse Contract for this charge."), indicator: "orange" });
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
  })
    .then(r => _apply_vals(cdt, cdn, (r && r.message) || {}))
    .catch(err => {
      console.error(err);
      frappe.show_alert({ message: __("Failed to fetch contract charge."), indicator: "red" });
    });
}
frappe.ui.form.on("Stocktake Order Charges", {
  charge_item(frm, cdt, cdn) { _fetch(frm, cdt, cdn, "stocktake"); },
  item_code(frm, cdt, cdn) { _fetch(frm, cdt, cdn, "stocktake"); },
});

// -----------------------------------------------------------------------------
// Stocktake Order — item link filter by Customer + Action menu
// -----------------------------------------------------------------------------
(() => {
  const CHILD_TABLE = "items";
  const ITEM_FIELD  = "item";

  function set_item_query(frm) {
    // Filter item link by Customer (blank = no filter)
    if (!frm.fields_dict[CHILD_TABLE]) return;

    const make_query = () => {
      const customer = frm.doc.customer || "";
      return { filters: customer ? { customer } : {} };
    };

    // Grid link field & inline row dialog
    frm.fields_dict[CHILD_TABLE].grid.get_field(ITEM_FIELD).get_query = make_query;
    frm.set_query(ITEM_FIELD, CHILD_TABLE, make_query);
  }

  function drop_mismatched_rows(frm) {
    // When customer is set (not blank), clear chosen items to avoid cross-customer mixing
    const customer = frm.doc.customer;
    if (!customer || !Array.isArray(frm.doc[CHILD_TABLE])) return;
    let changed = false;
    (frm.doc[CHILD_TABLE] || []).forEach(r => {
      if (r[ITEM_FIELD]) { r[ITEM_FIELD] = null; changed = true; }
    });
    if (changed) frm.refresh_field(CHILD_TABLE);
  }

  function openGetItemsDialog(frm) {
    const d = new frappe.ui.Dialog({
      title: __("Get Count Items"),
      fields: [
        { fieldtype: "Section Break", label: __("Scope") },
        { fieldname: "company",  label: __("Company"),  fieldtype: "Link", options: "Company", default: frm.doc.company || "" },
        { fieldname: "branch",   label: __("Branch"),   fieldtype: "Link", options: "Branch",  default: frm.doc.branch  || "" },

        // Customer defaults BLANK (leave empty for all customers)
        { fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer",
          description: __("Leave blank to fetch items for all customers") },

        { fieldtype: "Section Break", label: __("Location Filter") },
        { fieldname: "storage_type", label: __("Storage Type"), fieldtype: "Link", options: "Storage Type",
          description: __("Optional filter by storage type") },

        { fieldtype: "Section Break" },
        { fieldname: "only_active",    label: __("Only Active Items"), fieldtype: "Check", default: 1 },
        { fieldname: "limit_rows",     label: __("Limit Rows"),        fieldtype: "Int",   default: 1000 },
        { fieldname: "clear_existing", label: __("Clear existing rows before insert"), fieldtype: "Check", default: 1 },
      ],
      primary_action_label: __("Fetch"),
      primary_action(values) {
        d.hide();
        if (!frm.doc.name) {
          frappe.msgprint(__("Please save the document first."));
          return;
        }

        const limit_rows = Number.parseInt(values.limit_rows, 10) || 1000;

        frappe.call({
          method: "logistics.warehousing.doctype.stocktake_order.stocktake_order.stocktake_get_count_items",
          freeze: true,
          freeze_message: __("Fetching items…"),
          args: {
            stocktake_order: frm.doc.name,
            customer: (values.customer || "").trim() || null, // blank = all
            company: (values.company || "").trim() || null,
            branch: (values.branch || "").trim() || null,
            storage_type: (values.storage_type || "").trim() || null,
            only_active: values.only_active ? 1 : 0,
            limit_rows,
            clear_existing: values.clear_existing ? 1 : 0,
            do_update: 1,
          },
        })
          .then(r => {
            const res = (r && r.message) || {};
            const msg = res.message || __("Items fetched.");
            let html = `<div>${frappe.utils.escape_html(msg)}</div>`;
            if (res.warnings && res.warnings.length) {
              const lis = res.warnings.map(w => `<li>${frappe.utils.escape_html(w)}</li>`).join("");
              html += `<div style="margin-top:8px">${__("Warnings")}:</div><ul>${lis}</ul>`;
            }
            frappe.msgprint({ title: __("Get Count Items"), message: html, indicator: "blue" });
            frm.reload_doc();
          })
          .catch(err => {
            console.error(err);
            frappe.msgprint({ title: __("Get Count Items Failed"), message: __("See console for details."), indicator: "red" });
          });
      },
    });
    d.show();
  }

  frappe.ui.form.on("Stocktake Order", {
    setup(frm) { set_item_query(frm); },
    refresh(frm) {
      set_item_query(frm);

      // --- Action menu buttons ---
      if (!frm.doc.__islocal) {
        // 1) Get Count Items (always available once saved)
        frm.add_custom_button(__("Get Count Items"), () => openGetItemsDialog(frm), __("Action"));

        // 2) Create Warehouse Job — allowed ONLY when submitted
        if ((frm.doc.docstatus || 0) === 1) {
          frm.add_custom_button(__("Create Warehouse Job"), () => {
            frappe.model.open_mapped_doc({
              method: "logistics.warehousing.doctype.stocktake_order.stocktake_order.make_warehouse_job",
              frm,
            });
          }, __("Action"));
        }
      }
    },
    customer(frm) {
      set_item_query(frm);
      drop_mismatched_rows(frm);
    },
  });
})();

// Manage Planned Date

frappe.ui.form.on("Stocktake Order", {
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

frappe.ui.form.on("Stocktake Order Item", {
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

frappe.ui.form.on("Stocktake Order Charges", {
  quantity(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  },
  rate(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  }
});

// When a new row is added to the charges table
frappe.ui.form.on("Stocktake Order", {
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
frappe.ui.form.on("Stocktake Order Item", {
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