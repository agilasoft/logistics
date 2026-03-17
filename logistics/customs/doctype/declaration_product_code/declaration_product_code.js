// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Declaration Product Code", {
	item_code(frm) {
		if (!frm.doc.product_code && frm.doc.item_code) {
			frm.set_value("product_code", frm.doc.item_code);
		}
	}
});
