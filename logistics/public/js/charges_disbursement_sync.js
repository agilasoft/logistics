// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt
// Applies calculate_charge_row disbursement_mirror to grid rows so revenue fields stay in sync with cost.

frappe.provide("logistics.charges_disbursement");

logistics.charges_disbursement.apply_charge_row_response = function(cdt, cdn, r) {
	if (!r || !r.message || !r.message.disbursement_mirror) {
		return;
	}
	var mirror = r.message.disbursement_mirror;
	if (!mirror || typeof mirror !== "object") {
		return;
	}
	var skip = { bill_to: 1, pay_to: 1 };
	for (var field in mirror) {
		if (Object.prototype.hasOwnProperty.call(mirror, field)) {
			if (skip[field]) {
				continue;
			}
			frappe.model.set_value(cdt, cdn, field, mirror[field]);
		}
	}
};
