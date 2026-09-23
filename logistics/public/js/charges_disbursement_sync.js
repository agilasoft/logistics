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
	var set_if_changed =
		logistics.charge_type_cleanup && logistics.charge_type_cleanup.set_row_value_if_changed;
	for (var field in mirror) {
		if (Object.prototype.hasOwnProperty.call(mirror, field)) {
			if (skip[field]) {
				continue;
			}
			// Unconditional set_value refreshes Quantity even when the value is unchanged,
			// and a null mirror wipes the qty row_updates just applied.
			if (set_if_changed) {
				set_if_changed(cdt, cdn, field, mirror[field]);
			} else {
				frappe.model.set_value(cdt, cdn, field, mirror[field]);
			}
		}
	}
};
