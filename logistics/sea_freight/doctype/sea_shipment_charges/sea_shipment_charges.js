// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// purchase_invoice_dialog.js hides the grid "open row" control for invoice-locked charge lines
// but never shows it again for unlocked lines. Keep row __read_only and the control in sync.
function _sea_shipment_charge_row_is_invoice_locked(row) {
	if (!row) return false;
	var costLocked = ["Requested", "Invoiced", "Posted", "Paid"];
	var revenueLocked = ["Requested", "Posted", "Paid"];
	return (
		costLocked.indexOf(row.purchase_invoice_status) !== -1 ||
		revenueLocked.indexOf(row.sales_invoice_status) !== -1
	);
}

function _restore_sea_shipment_charges_grid_edit_buttons(frm) {
	if (!frm || !frm.fields_dict.charges || !frm.fields_dict.charges.grid) return;
	var grid = frm.fields_dict.charges.grid;
	if (!grid.grid_rows || !grid.grid_rows.length) return;
	grid.grid_rows.forEach(function(grid_row) {
		if (!grid_row.doc) return;
		if (_sea_shipment_charge_row_is_invoice_locked(grid_row.doc)) {
			grid_row.doc.__read_only = 1;
			if (grid_row.open_form_button) grid_row.open_form_button.toggle(false);
		} else {
			grid_row.doc.__read_only = 0;
			if (grid_row.open_form_button) grid_row.open_form_button.toggle(true);
		}
	});
}

frappe.ui.form.on("Sea Shipment", {
	refresh: function(frm) {
		setTimeout(function() {
			_restore_sea_shipment_charges_grid_edit_buttons(frm);
		}, 0);
	},
});

frappe.ui.form.on("Sea Shipment Charges", {
	form_render: function(frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (!row) return;
		if (!_sea_shipment_charge_row_is_invoice_locked(row)) {
			row.__read_only = 0;
		}
		_restore_sea_shipment_charges_grid_edit_buttons(frm);
	},
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
			doctype: "Sea Shipment Charges",
			parenttype: "Sea Shipment",
			parent: frm.doc.name || "new",
			row_data: JSON.stringify(row)
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
