// Copyright (c) 2026, Logistics Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Dispute", {
	reference_doctype(frm) {
		frm.set_value("reference_name", null);
	},

	reference_name(frm) {
		if (!frm.doc.reference_name || !frm.doc.reference_doctype) {
			return;
		}
		frappe.db.get_value(
			frm.doc.reference_doctype,
			frm.doc.reference_name,
			["company", "customer", "supplier", "outstanding_amount"],
		).then((r) => {
			const inv = r.message;
			if (!inv) {
				return;
			}
			frm.set_value("company", inv.company);
			if (frm.doc.reference_doctype === "Sales Invoice") {
				frm.set_value("party_type", "Customer");
				frm.set_value("party", inv.customer);
			} else {
				frm.set_value("party_type", "Supplier");
				frm.set_value("party", inv.supplier);
			}
			if (flt(inv.outstanding_amount) <= 0) {
				frappe.msgprint({
					title: __("Fully Paid"),
					indicator: "orange",
					message: __("This invoice has no outstanding balance."),
				});
			}
		});
	},

	status(frm) {
		const resolved = ["Resolved", "Closed"].includes(frm.doc.status);
		if (resolved && !frm.doc.resolution_date) {
			frm.set_value("resolution_date", frappe.datetime.get_today());
		}
		if (!resolved) {
			frm.set_value("resolution_date", null);
		}
	},
});
