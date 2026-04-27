// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Air Shipment Charges", {
	charge_type: function(frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (row && row.charge_type === "Disbursement") {
			_calculate_charge_row(frm, cdt, cdn);
		}
	},
	revenue_calculation_method: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	rate: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	quantity: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	uom: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	currency: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	unit_type: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	minimum_quantity: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	minimum_unit_rate: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	minimum_charge: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	maximum_charge: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	base_amount: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	base_quantity: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_calculation_method: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_quantity: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_uom: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_currency: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	unit_cost: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_unit_type: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_minimum_quantity: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_minimum_unit_rate: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_minimum_charge: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_maximum_charge: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_base_amount: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	cost_base_quantity: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	// Weight Break / Qty Break handlers in charge_break_buttons.js
});

function _calculate_charge_row(frm, cdt, cdn) {
	if (!cdn) return;
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) return;
	frappe.call({
		method: "logistics.utils.charges_calculation.calculate_charge_row",
		args: {
			doctype: "Air Shipment Charges",
			parenttype: "Air Shipment",
			parent: frm.doc.name || "new",
			row_data: JSON.stringify(row),
			parent_overrides:
				window.logistics && logistics.charge_row_parent_overrides
					? logistics.charge_row_parent_overrides(frm)
					: null,
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				// Shipment charges: only update actual (estimated comes from Booking, do not overwrite)
				if ("actual_revenue" in r.message) {
					frappe.model.set_value(cdt, cdn, "actual_revenue", r.message.actual_revenue);
				}
				if ("actual_cost" in r.message) {
					frappe.model.set_value(cdt, cdn, "actual_cost", r.message.actual_cost);
				}
				if (r.message.quantity != null) {
					frappe.model.set_value(cdt, cdn, "quantity", r.message.quantity);
				}
				if (r.message.cost_quantity != null) {
					frappe.model.set_value(cdt, cdn, "cost_quantity", r.message.cost_quantity);
				}
				if ("revenue_calc_notes" in r.message) {
					frappe.model.set_value(cdt, cdn, "revenue_calc_notes", r.message.revenue_calc_notes || "");
				}
				if ("cost_calc_notes" in r.message) {
					frappe.model.set_value(cdt, cdn, "cost_calc_notes", r.message.cost_calc_notes || "");
				}
				if (logistics.charges_disbursement && logistics.charges_disbursement.apply_charge_row_response) {
					logistics.charges_disbursement.apply_charge_row_response(cdt, cdn, r);
				}
			}
		}
	});
}
