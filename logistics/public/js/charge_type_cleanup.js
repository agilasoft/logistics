// Copyright (c) 2026, www.agilasoft.com and contributors
// Clear locked cost/revenue side when charge_type becomes Revenue or Cost.

frappe.provide("logistics.charge_type_cleanup");

(function () {
	"use strict";

	var COST_CLEAR_FIELDS = [
		"cost_calculation_method",
		"unit_cost",
		"cost_unit_type",
		"cost_currency",
		"cost_quantity",
		"cost_uom",
		"cost_minimum_quantity",
		"cost_minimum_unit_rate",
		"cost_minimum_charge",
		"cost_maximum_charge",
		"cost_base_amount",
		"cost_base_quantity",
		"use_tariff_in_cost",
		"cost_tariff",
		"cost_sheet_source",
		"buying_currency",
		"estimated_cost",
		"cost_calc_notes",
		"actual_cost",
	];

	var REVENUE_CLEAR_FIELDS = [
		"revenue_calculation_method",
		"calculation_method",
		"unit_rate",
		"unit_type",
		"currency",
		"quantity",
		"uom",
		"minimum_quantity",
		"minimum_unit_rate",
		"minimum_charge",
		"maximum_charge",
		"base_amount",
		"base_quantity",
		"use_tariff_in_revenue",
		"revenue_tariff",
		"tariff",
		"selling_currency",
		"estimated_revenue",
		"revenue_calc_notes",
		"actual_revenue",
	];

	var CHARGE_DOCTYPES_WITH_TYPE_CLEANUP = [
		"Sales Quote Charge",
		"Change Request Charge",
		"Transport Order Charges",
		"Transport Job Charges",
		"Air Booking Charges",
		"Air Shipment Charges",
		"Sea Booking Charges",
		"Sea Shipment Charges",
		"Sea Consolidation Charges",
		"Air Consolidation Charges",
		"Special Project Charges",
		"Declaration Charges",
		"Declaration Order Charges",
		"MICE Project Charges",
		"Tariff Charge",
	];

	function _empty_value_for_field(cdt, fieldname) {
		var df = frappe.meta.get_docfield(cdt, fieldname);
		if (!df) {
			return null;
		}
		if (df.fieldtype === "Check") {
			return 0;
		}
		if (["Currency", "Float", "Int", "Percent"].indexOf(df.fieldtype) !== -1) {
			return 0;
		}
		if (["Link", "Select", "Dynamic Link"].indexOf(df.fieldtype) !== -1) {
			return null;
		}
		return "";
	}

	function _clear_fields_on_row(cdt, cdn, fieldnames) {
		fieldnames.forEach(function (fieldname) {
			if (!frappe.meta.get_docfield(cdt, fieldname)) {
				return;
			}
			frappe.model.set_value(cdt, cdn, fieldname, _empty_value_for_field(cdt, fieldname));
		});
	}

	logistics.charge_type_cleanup.clear_cost_fields_on_row = function (cdt, cdn) {
		_clear_fields_on_row(cdt, cdn, COST_CLEAR_FIELDS);
	};

	logistics.charge_type_cleanup.clear_revenue_fields_on_row = function (cdt, cdn) {
		_clear_fields_on_row(cdt, cdn, REVENUE_CLEAR_FIELDS);
	};

	logistics.charge_type_cleanup.apply_calculate_charge_row_response = function (frm, cdt, cdn, r) {
		if (!r || !r.message || !r.message.success) {
			return;
		}
		if (r.message.row_updates && typeof r.message.row_updates === "object") {
			frm._syncing_sq_charge_from_tariff = true;
			try {
				$.each(r.message.row_updates, function (key, v) {
					if (v !== undefined && v !== null) {
						frappe.model.set_value(cdt, cdn, key, v);
					}
				});
			} finally {
				frm._syncing_sq_charge_from_tariff = false;
			}
		}
		var numericFields = [
			"estimated_revenue",
			"estimated_cost",
			"actual_revenue",
			"actual_cost",
			"quantity",
			"cost_quantity",
		];
		numericFields.forEach(function (fn) {
			if (r.message[fn] != null && frappe.meta.get_docfield(cdt, fn)) {
				frappe.model.set_value(cdt, cdn, fn, r.message[fn]);
			}
		});
		if (frappe.meta.get_docfield(cdt, "revenue_calc_notes")) {
			frappe.model.set_value(cdt, cdn, "revenue_calc_notes", r.message.revenue_calc_notes || "");
		}
		if (frappe.meta.get_docfield(cdt, "cost_calc_notes")) {
			frappe.model.set_value(cdt, cdn, "cost_calc_notes", r.message.cost_calc_notes || "");
		}
		if (logistics.charges_disbursement && logistics.charges_disbursement.apply_charge_row_response) {
			logistics.charges_disbursement.apply_charge_row_response(cdt, cdn, r);
		}
	};

	logistics.charge_type_cleanup.recalculate_charge_row = function (frm, cdt, cdn) {
		if (!cdn || !frm || !frm.doc) {
			return;
		}
		var row = locals[cdt] && locals[cdt][cdn];
		if (!row) {
			return;
		}
		frappe.call({
			method: "logistics.utils.charges_calculation.calculate_charge_row",
			args: {
				doctype: cdt,
				parenttype: frm.doc.doctype,
				parent: frm.doc.name || "new",
				row_data: JSON.stringify(row),
				parent_overrides:
					window.logistics && logistics.charge_row_parent_overrides
						? logistics.charge_row_parent_overrides(frm)
						: null,
			},
			callback: function (r) {
				logistics.charge_type_cleanup.apply_calculate_charge_row_response(frm, cdt, cdn, r);
			},
		});
	};

	logistics.charge_type_cleanup.on_charge_type_change = function (frm, cdt, cdn, tableFieldname) {
		var row = locals[cdt] && locals[cdt][cdn];
		if (!row) {
			return;
		}
		var ct = row.charge_type;
		if (ct === "Revenue") {
			logistics.charge_type_cleanup.clear_cost_fields_on_row(cdt, cdn);
		} else if (ct === "Cost") {
			logistics.charge_type_cleanup.clear_revenue_fields_on_row(cdt, cdn);
		}
		var table = tableFieldname || "charges";
		if (frm && frm.refresh_field) {
			frm.refresh_field(table);
		}
		if (ct === "Revenue" || ct === "Cost" || ct === "Disbursement") {
			logistics.charge_type_cleanup.recalculate_charge_row(frm, cdt, cdn);
		}
	};

	CHARGE_DOCTYPES_WITH_TYPE_CLEANUP.forEach(function (doctype) {
		var events = {};
		events.charge_type = function (frm, cdt, cdn) {
			logistics.charge_type_cleanup.on_charge_type_change(frm, cdt, cdn);
		};
		frappe.ui.form.on(doctype, events);
	});
})();
