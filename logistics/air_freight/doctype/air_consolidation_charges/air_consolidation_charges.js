// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Air Consolidation Charges", {
	charge_type: function (frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (row && row.charge_type === "Disbursement") {
			_calculate_air_consolidation_charge_row(frm, cdt, cdn);
		}
	},
	revenue_calculation_method: function (frm, cdt, cdn) {
		_calculate_air_consolidation_charge_row(frm, cdt, cdn, {
			sync_qty_for_unit_type: true,
		});
	},
	rate: function (frm, cdt, cdn) {
		_calculate_air_consolidation_charge_row(frm, cdt, cdn);
	},
	quantity: function (frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (row && row._logistics_skip_charge_recalc === "quantity") {
			row._logistics_skip_charge_recalc = null;
			return;
		}
		_calculate_air_consolidation_charge_row(frm, cdt, cdn);
	},
	currency: function (frm, cdt, cdn) {
		_calculate_air_consolidation_charge_row(frm, cdt, cdn);
	},
	unit_of_measure: function (frm, cdt, cdn) {
		_calculate_air_consolidation_charge_row(frm, cdt, cdn, {
			sync_qty_for_unit_type: true,
		});
	},
	unit_type: function (frm, cdt, cdn) {
		_calculate_air_consolidation_charge_row(frm, cdt, cdn, {
			sync_qty_for_unit_type: true,
		});
	},
	discount_percentage: function (frm, cdt, cdn) {
		_calculate_air_consolidation_charge_row(frm, cdt, cdn);
	},
	surcharge_amount: function (frm, cdt, cdn) {
		_calculate_air_consolidation_charge_row(frm, cdt, cdn);
	},
	// Weight Break / Qty Break handlers in charge_break_buttons.js
});

function _fallback_sync_air_consolidation_charge_quantity(frm, cdt, cdn) {
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row || row.revenue_calculation_method !== "Per Unit") {
		return;
	}
	var doc = frm.doc;
	var q = null;
	var uom = (row.unit_of_measure || "").trim().toLowerCase();
	if (uom === "shipment") {
		var names = {};
		(doc.consolidation_packages || []).forEach(function (p) {
			if (p.air_freight_job) {
				names[p.air_freight_job] = 1;
			}
		});
		(doc.consolidation_planning_lines || []).forEach(function (p) {
			if (p.air_shipment) {
				names[p.air_shipment] = 1;
			}
		});
		q = Object.keys(names).length || 0;
	} else if (row.unit_type === "Weight") {
		q = frappe.utils.flt(doc.total_weight || doc.weight || 0);
	} else if (row.unit_type === "Chargeable Weight") {
		q = frappe.utils.flt(
			doc.chargeable_weight || doc.chargeable || doc.total_weight || 0
		);
	} else if (row.unit_type === "Volume") {
		q = frappe.utils.flt(doc.total_volume || doc.volume || 0);
	} else if (row.unit_type === "Package" || row.unit_type === "Piece") {
		q = frappe.utils.flt(doc.total_packages || 0);
	}
	if (q == null) {
		return;
	}
	row._logistics_skip_charge_recalc = "quantity";
	row.quantity = q;
	frappe.model.set_value(cdt, cdn, "quantity", q);
}

function _calculate_air_consolidation_charge_row(frm, cdt, cdn, opts) {
	opts = opts || {};
	if (!cdn) {
		return;
	}
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	if (
		opts.sync_qty_for_unit_type &&
		window.logistics &&
		logistics.update_air_consolidation_charge_row_from_parent
	) {
		logistics.update_air_consolidation_charge_row_from_parent(frm, cdt, cdn, {
			server: false,
		});
	} else if (opts.sync_qty_for_unit_type) {
		_fallback_sync_air_consolidation_charge_quantity(frm, cdt, cdn);
		if (frm.refresh_field) {
			frm.refresh_field("consolidation_charges");
		}
	}
	if (!opts.skip_qty_sync && !opts.sync_qty_for_unit_type) {
		var resolved_before =
			window.logistics &&
			logistics.resolve_air_consolidation_charge_quantity &&
			logistics.resolve_air_consolidation_charge_quantity(frm, row);
		if (resolved_before != null) {
			row.quantity = resolved_before;
		}
	}

	frappe.call({
		method: "logistics.utils.charges_calculation.calculate_charge_row",
		args: {
			doctype: "Air Consolidation Charges",
			parenttype: "Air Consolidation",
			parent: frm.doc.name || "new",
			row_data: JSON.stringify(row),
			parent_overrides:
				window.logistics && logistics.charge_row_parent_overrides
					? logistics.charge_row_parent_overrides(frm)
					: null,
		},
		callback: function (r) {
			var current_row = locals[cdt] && locals[cdt][cdn];
			if (!current_row) {
				return;
			}

			var resolved_qty =
				window.logistics &&
				logistics.resolve_air_consolidation_charge_quantity
					? logistics.resolve_air_consolidation_charge_quantity(frm, current_row)
					: null;

			if (!r.message || !r.message.success) {
				if (resolved_qty != null) {
					frappe.model.set_value(cdt, cdn, "quantity", resolved_qty);
					if (logistics.refresh_charge_grid_cell) {
						logistics.refresh_charge_grid_cell(frm, cdt, cdn, "quantity");
					}
				}
				if (logistics.apply_air_consolidation_charge_amounts) {
					logistics.apply_air_consolidation_charge_amounts(
						frm,
						cdt,
						cdn,
						null
					);
				}
				return;
			}

			var qty_to_set =
				resolved_qty != null ? resolved_qty : r.message.quantity;
			if (qty_to_set != null) {
				frappe.model.set_value(cdt, cdn, "quantity", qty_to_set);
				if (logistics.refresh_charge_grid_cell) {
					logistics.refresh_charge_grid_cell(frm, cdt, cdn, "quantity");
				}
			}
			if (logistics.apply_air_consolidation_charge_amounts) {
				logistics.apply_air_consolidation_charge_amounts(
					frm,
					cdt,
					cdn,
					r.message
				);
			}
			var updates = r.message.row_updates;
			if (updates) {
				Object.keys(updates).forEach(function (fieldname) {
					if (
						updates[fieldname] !== undefined &&
						updates[fieldname] !== null
					) {
						frappe.model.set_value(
							cdt,
							cdn,
							fieldname,
							updates[fieldname]
						);
					}
				});
			}
			if (
				logistics.charges_disbursement &&
				logistics.charges_disbursement.apply_charge_row_response
			) {
				logistics.charges_disbursement.apply_charge_row_response(
					cdt,
					cdn,
					r
				);
			}
		},
	});
}

// Exposed for logistics.update_air_consolidation_charge_row_from_parent (optional server RPC).
window._calculate_air_consolidation_charge_row = _calculate_air_consolidation_charge_row;
