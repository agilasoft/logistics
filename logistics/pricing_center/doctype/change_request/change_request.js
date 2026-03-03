// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.ui.form.on("Change Request", {
	refresh(frm) {
		// Approve: set status to Approved and save (server will apply charges to job)
		if (!frm.doc.__islocal && frm.doc.status !== "Approved" && frm.doc.status !== "Sales Quote Created" && frm.doc.charges && frm.doc.charges.length > 0) {
			frm.add_custom_button(__("Approve"), function () {
				frappe.confirm(
					__("Approve this Change Request and apply {0} charge(s) to the linked job?").format(frm.doc.charges.length),
					function () {
						frm.set_value("status", "Approved");
						frm.save();
					}
				);
			});
		}
		if (!frm.doc.__islocal && frm.doc.status !== "Sales Quote Created" && frm.doc.charges && frm.doc.charges.length > 0) {
			frm.add_custom_button(__("Create Sales Quote"), function () {
				frappe.confirm(
					__("Create a Sales Quote for this Change Request (Additional Charge)?"),
					function () {
						frappe.call({
							method: "logistics.pricing_center.doctype.change_request.change_request.create_sales_quote_from_change_request",
							args: { change_request_name: frm.doc.name },
							callback: function (r) {
								if (r.message) {
									frappe.set_route("Form", "Sales Quote", r.message);
									frm.reload_doc();
								}
							},
						});
					}
				);
			});
		}
	},
});
