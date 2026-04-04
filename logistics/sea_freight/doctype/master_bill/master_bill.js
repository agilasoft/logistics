// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Master Bill", {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Refresh Voyage Status"), function () {
				frappe.call({
					method: "logistics.sea_freight.doctype.master_bill.master_bill.refresh_voyage_status",
					args: { master_bill_name: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __("Voyage status refreshed"), indicator: "green" });
						} else if (r.message && r.message.error) {
							frappe.msgprint(r.message.error);
						}
					}
				});
			}, __("Action"));
		}
	}
});
