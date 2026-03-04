// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commercial Invoice Line Item", {
	declaration_product_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.declaration_product_code) {
			// Clear fetched fields when Declaration Product Code is cleared
			frappe.model.set_value(cdt, cdn, {
				item: "",
				product_code: "",
				procedure_code: "",
				tariff: "",
				goods_description: "",
				commodity_code: "",
				goods_origin: "",
				preference: ""
			});
			return;
		}
		frappe.call({
			method: "logistics.customs.doctype.declaration_product_code.declaration_product_code.get_declaration_product_code_details",
			args: { name: row.declaration_product_code },
			callback: function(r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, r.message);
				}
			}
		});
	}
});
