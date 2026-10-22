// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Management Settings", {
	refresh(frm) {
		frm.set_intro(
			__(
				"Allow Legacy Jobs shows the Legacy Job checkbox on Air Shipment, Sea Shipment, Transport Job, Declaration, and Warehouse Job."
			)
		);
	},
});
