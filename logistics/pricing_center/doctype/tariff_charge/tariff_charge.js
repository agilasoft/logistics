// Copyright (c) 2026, www.agilasoft.com and contributors
// Tariff Charge — same calculation grid behaviour as Sales Quote Charge; parent validation on Tariff.

function tariff_charge_needs_revenue_calculation_method(row) {
	if (!row) {
		return false;
	}
	const ct = row.charge_type;
	return ct && !["Cost", "Disbursement"].includes(ct);
}

frappe.ui.form.on("Tariff", {
	validate(frm) {
		const rates = frm.doc.rates || [];
		for (const row of rates) {
			const method = (row.revenue_calculation_method || "").trim();
			if (tariff_charge_needs_revenue_calculation_method(row) && !method) {
				frappe.throw(
					__("Rates row {0}: Calculation Method is required for charge type \"{1}\".", [
						row.idx || "?",
						row.charge_type || "",
					])
				);
			}
		}
	},
});
