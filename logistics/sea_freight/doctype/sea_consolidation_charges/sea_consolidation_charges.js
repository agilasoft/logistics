// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sea Consolidation Charges", {
	charge_item: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	charge_type: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_calculation_method: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	unit_cost: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_quantity: function (frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (row && row._logistics_skip_charge_recalc === "cost_quantity") {
			row._logistics_skip_charge_recalc = null;
			return;
		}
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_uom: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_currency: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_unit_type: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn, { sync_qty_for_unit_type: true });
	},
	cost_minimum_quantity: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_minimum_unit_rate: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_minimum_charge: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_maximum_charge: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_base_amount: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	cost_base_quantity: function (frm, cdt, cdn) {
		_calculate_sea_consolidation_charge_row(frm, cdt, cdn);
	},
	// Weight Break / Qty Break handlers in charge_break_buttons.js
});

function _calculate_sea_consolidation_charge_row(frm, cdt, cdn, opts) {
	if (!cdn) {
		return;
	}
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	if (
		opts &&
		opts.sync_qty_for_unit_type &&
		window.logistics &&
		logistics.sync_air_charge_qty_for_unit_type_to_grid
	) {
		logistics.sync_air_charge_qty_for_unit_type_to_grid(frm, cdt, cdn, "cost");
	}
	frappe.call({
		method: "logistics.utils.charges_calculation.calculate_charge_row",
		args: {
			doctype: "Sea Consolidation Charges",
			parenttype: "Sea Consolidation",
			parent: frm.doc.name || "new",
			row_data: JSON.stringify(row),
			parent_overrides:
				window.logistics && logistics.charge_row_parent_overrides
					? logistics.charge_row_parent_overrides(frm)
					: null,
		},
		callback: function (r) {
			if (!r.message || !r.message.success) {
				return;
			}
			if (r.message.cost_quantity != null) {
				frappe.model.set_value(cdt, cdn, "cost_quantity", r.message.cost_quantity);
			}
			if (r.message.estimated_cost != null) {
				frappe.model.set_value(cdt, cdn, "estimated_cost", r.message.estimated_cost);
			}
			if ("cost_calc_notes" in r.message) {
				frappe.model.set_value(
					cdt,
					cdn,
					"cost_calc_notes",
					r.message.cost_calc_notes || ""
				);
			}
			var updates = r.message.row_updates;
			if (updates) {
				Object.keys(updates).forEach(function (fieldname) {
					if (updates[fieldname] !== undefined && updates[fieldname] !== null) {
						frappe.model.set_value(cdt, cdn, fieldname, updates[fieldname]);
					}
				});
			}
		},
	});
}
