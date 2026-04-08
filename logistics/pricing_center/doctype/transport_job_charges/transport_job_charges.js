// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Job Charges", {
	charge_type: function(frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (row && row.charge_type === "Disbursement") {
			_calculate_charge_row(frm, cdt, cdn);
		}
	},
	item_code: function(frm, cdt, cdn) {
		var attempts = 0;
		var maxAttempts = 8;
		var tick = function() {
			attempts += 1;
			var currentRow = locals[cdt] && locals[cdt][cdn];
			if (currentRow && (currentRow.standard_unit_cost !== undefined || attempts >= maxAttempts)) {
				_recalculate_total_standard_cost(frm, cdt, cdn);
			} else {
				setTimeout(tick, 150);
			}
		};
		if (!locals[cdt][cdn].item_code) {
			frappe.model.set_value(cdt, cdn, "total_standard_cost", 0);
			return;
		}
		setTimeout(tick, 150);
	},
	quantity: function(frm, cdt, cdn) {
		_calculate_charge_row(frm, cdt, cdn);
		_recalculate_total_standard_cost(frm, cdt, cdn);
	},
	cost_quantity: function(frm, cdt, cdn) {
		_calculate_charge_row(frm, cdt, cdn);
		_recalculate_total_standard_cost(frm, cdt, cdn);
	},
	standard_unit_cost: function(frm, cdt, cdn) {
		_recalculate_total_standard_cost(frm, cdt, cdn);
	},
	revenue_calculation_method: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
	rate: function(frm, cdt, cdn) { _calculate_charge_row(frm, cdt, cdn); },
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
			doctype: "Transport Job Charges",
			parenttype: "Transport Job",
			parent: frm.doc.name || "new",
			row_data: JSON.stringify(row)
		},
		callback: function(r) {
			if (r.message && r.message.success) {
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

function _recalculate_total_standard_cost(frm, cdt, cdn) {
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) return;
	var qty = parseFloat(row.quantity) || 0;
	if (qty <= 0) {
		qty = parseFloat(row.cost_quantity) || 0;
	}
	var su = parseFloat(row.standard_unit_cost) || 0;
	frappe.model.set_value(cdt, cdn, "total_standard_cost", qty * su);
}
