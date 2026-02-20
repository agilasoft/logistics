// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Declaration Order", {
	refresh(frm) {
		// View Sales Quote
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__("View Sales Quote"), function() {
				frappe.set_route("Form", "Sales Quote", frm.doc.sales_quote);
			}, __("View"));
		}
		// Create Declaration
		if (!frm.doc.__islocal && frm.doc.sales_quote) {
			frm.add_custom_button(__("Create Declaration"), function() {
				frappe.call({
					method: "logistics.customs.doctype.declaration.declaration.create_declaration_from_declaration_order",
					args: { declaration_order_name: frm.doc.name },
					callback: function(r) {
						if (r.exc) return;
						if (r.message && r.message.success && r.message.declaration) {
							frappe.msgprint({
								title: __("Declaration Created"),
								message: __("Declaration {0} created.", [r.message.declaration]),
								indicator: "green"
							});
							setTimeout(function() {
								frappe.set_route("Form", "Declaration", r.message.declaration);
							}, 100);
						}
					}
				});
			}, __("Create"));
		}
	},
	sales_quote(frm) {
		if (!frm.doc.sales_quote) return;
		frappe.call({
			method: "logistics.customs.doctype.declaration_order.declaration_order.get_sales_quote_details",
			args: { sales_quote: frm.doc.sales_quote },
			callback: function(r) {
				if (r.message && !frm.doc.customer) {
					frm.set_value("customer", r.message.customer || "");
					frm.set_value("company", r.message.company || "");
					frm.set_value("customs_authority", r.message.customs_authority || "");
					frm.set_value("branch", r.message.branch || "");
					frm.set_value("cost_center", r.message.cost_center || "");
					frm.set_value("profit_center", r.message.profit_center || "");
				}
			}
		});
	}
});
