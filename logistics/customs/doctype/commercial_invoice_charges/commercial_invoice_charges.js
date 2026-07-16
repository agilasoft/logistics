// Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
// For license information, please see license.txt

function _schedule_commercial_invoice_totals_recalc_from_grid(frm) {
	if (
		window.logistics &&
		logistics.schedule_commercial_invoice_totals_recalc &&
		frm &&
		(frm.doctype === "Declaration" || frm.doctype === "Declaration Order")
	) {
		logistics.schedule_commercial_invoice_totals_recalc(frm);
	}
}

frappe.ui.form.on("Commercial Invoice Charges", {
	charge_code(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
	amount(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
	currency(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
	add_to_fob(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
	included_in_inv_amt(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
	incl_in_inv_lines(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
});
