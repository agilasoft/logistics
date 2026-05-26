// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// purchase_invoice_dialog.js hides the grid "open row" control for invoice-locked charge lines
// but never shows it again for unlocked lines. Keep row __read_only and the control in sync.
function _special_project_charge_row_is_invoice_locked(row) {
	if (!row) return false;
	var costLocked = ["Requested", "Invoiced", "Posted", "Paid"];
	var revenueLocked = ["Requested", "Posted", "Paid"];
	return (
		costLocked.indexOf(row.purchase_invoice_status) !== -1 ||
		revenueLocked.indexOf(row.sales_invoice_status) !== -1
	);
}

function _restore_special_project_charges_grid_edit_buttons(frm) {
	if (!frm || !frm.fields_dict.charges || !frm.fields_dict.charges.grid) return;
	var grid = frm.fields_dict.charges.grid;
	if (!grid.grid_rows || !grid.grid_rows.length) return;
	grid.grid_rows.forEach(function(grid_row) {
		if (!grid_row.doc) return;
		if (_special_project_charge_row_is_invoice_locked(grid_row.doc)) {
			grid_row.doc.__read_only = 1;
			if (grid_row.open_form_button) grid_row.open_form_button.toggle(false);
		} else {
			grid_row.doc.__read_only = 0;
			if (grid_row.open_form_button) grid_row.open_form_button.toggle(true);
		}
	});
}

frappe.ui.form.on("Special Project", {
	refresh: function(frm) {
		setTimeout(function() {
			_restore_special_project_charges_grid_edit_buttons(frm);
		}, 0);
	},
});

function _lifecycle_jobs_matching_service_type(frm, service_type) {
	const st = String(service_type || "").trim();
	if (!st) return [];
	return (frm.doc.lifecycle_jobs || []).filter(function (row) {
		return String(row.service_type || "").trim() === st;
	});
}

function _lifecycle_jobs_still_planning(matches) {
	return (matches || []).filter(function (row) {
		return !String(row.job_no || "").trim();
	});
}

function _maybe_default_lifecycle_job_row(frm, cdt, cdn) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row || row.lifecycle_job_row) return;
	const matches = _lifecycle_jobs_matching_service_type(frm, row.service_type);
	let target = null;
	if (matches.length === 1) {
		target = matches[0];
	} else {
		const planning = _lifecycle_jobs_still_planning(matches);
		if (planning.length === 1) {
			target = planning[0];
		}
	}
	if (target) {
		frappe.model.set_value(cdt, cdn, "lifecycle_job_row", target.idx);
	}
}

frappe.ui.form.on("Special Project Charges", {
	service_type: function (frm, cdt, cdn) {
		_maybe_default_lifecycle_job_row(frm, cdt, cdn);
	},
	lifecycle_job_row: function (frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row || !row.lifecycle_job_row) return;
		const lj = (frm.doc.lifecycle_jobs || []).find(function (r) {
			return cint(r.idx) === cint(row.lifecycle_job_row);
		});
		if (!lj) {
			frappe.msgprint({
				message: __("Lifecycle Job row {0} does not exist.", [row.lifecycle_job_row]),
				indicator: "orange",
			});
		}
	},
	form_render: function(frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (!row) return;
		if (!_special_project_charge_row_is_invoice_locked(row)) {
			row.__read_only = 0;
		}
		_restore_special_project_charges_grid_edit_buttons(frm);
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
			doctype: "Special Project Charges",
			parenttype: frm.doctype,
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
