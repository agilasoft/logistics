// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

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

frappe.ui.form.on("Stocktake Order Charges", {
  charge_item(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "stocktake"); },
  item_code(frm, cdt, cdn){ _fetch(frm, cdt, cdn, "stocktake"); }
});


//Filter Items by Customer
// Doctype: Stocktake Order
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

  frappe.ui.form.on('Stocktake Order', {
    setup: set_item_query,
    refresh: set_item_query,
    customer: function (frm) {
      set_item_query(frm);
      drop_mismatched_rows(frm);
    },
  });
})();
