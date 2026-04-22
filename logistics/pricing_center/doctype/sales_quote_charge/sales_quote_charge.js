// Copyright (c) 2026, www.agilasoft.com and contributors
// Sales Quote Charge - calculation events are in sales_quote.js (parent form)
// Weight Break / Qty Break handlers in charge_break_buttons.js
// Item Code filtering by Service Type is handled in sales_quote.js

/** Revenue side is editable when charge_type is not Cost or Disbursement (read_only_depends_on on revenue_calculation_method). */
function sales_quote_charge_needs_revenue_calculation_method(row) {
	if (!row) {
		return false;
	}
	const ct = row.charge_type;
	return ct && !["Cost", "Disbursement"].includes(ct);
}

frappe.ui.form.on("Sales Quote", {
	validate(frm) {
		const charges = frm.doc.charges || [];
		for (const row of charges) {
			const method = (row.revenue_calculation_method || "").trim();
			if (sales_quote_charge_needs_revenue_calculation_method(row) && !method) {
				frappe.throw(
					__("Charges row {0}: Calculation Method is required for charge type \"{1}\".", [
						row.idx || "?",
						row.charge_type || "",
					])
				);
			}
		}
	},
});
