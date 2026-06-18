// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_exhibit_job(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
}

frappe.ui.form.on("MICE Job", {
	refresh(frm) {
		logistics_set_site_query_exhibit_job(frm);
	},
});
