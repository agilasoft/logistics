// Copyright (c) 2026, Agilasoft and contributors

frappe.ui.form.on("Sales Quote Pack", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Add Sales Quote"), () => {
				frappe.call({
					method: "logistics.pricing_center.doctype.sales_quote_pack.sales_quote_pack.create_sales_quote_from_pack",
					args: { pack_name: frm.doc.name },
					callback(r) {
						if (r.message) {
							frappe.set_route("Form", "Sales Quote", r.message);
						}
					},
				});
			});
		}
	},
});
