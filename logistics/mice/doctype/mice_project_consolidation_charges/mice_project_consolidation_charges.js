// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("MICE Project Consolidation Charges", {
	revenue_calculation_method: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	unit_rate: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	quantity: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	discount_percentage: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	surcharge_amount: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	allocation_percentage: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
});

function _calculate_mice_consolidation_charge_row(frm, cdt, cdn) {
	if (!cdn) {
		return;
	}
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}

	var rate = frappe.utils.flt(row.unit_rate);
	var qty = frappe.utils.flt(row.quantity);
	var base = 0;

	if (row.revenue_calculation_method === "Per Unit") {
		base = rate * qty;
	} else if (row.revenue_calculation_method === "Flat Rate") {
		base = rate;
	} else if (row.revenue_calculation_method === "Percentage") {
		base = qty ? rate * (qty * 0.01) : 0;
	} else {
		base = frappe.utils.flt(row.base_amount);
	}

	var discount = 0;
	if (row.discount_percentage && base) {
		discount = base * (frappe.utils.flt(row.discount_percentage) / 100.0);
	}

	var total =
		frappe.utils.flt(base) -
		frappe.utils.flt(discount) +
		frappe.utils.flt(row.surcharge_amount);

	var allocated = 0;
	var pct = frappe.utils.flt(row.allocation_percentage);
	if (pct > 0) {
		allocated = total * (pct / 100.0);
	}

	frappe.model.set_value(cdt, cdn, "base_amount", base);
	frappe.model.set_value(cdt, cdn, "discount_amount", discount);
	frappe.model.set_value(cdt, cdn, "total_amount", total);
	frappe.model.set_value(cdt, cdn, "allocated_amount", allocated);

	if (frm && frm.refresh_field) {
		frm.refresh_field("consolidation_charges");
	}
}
