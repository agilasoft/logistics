// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Warehouse Contract", {
	refresh(frm) {
		// Add Get Rates action to the menu
		if (frm.doc.sales_quote && !frm.is_new()) {
			frm.add_custom_button(__("Get Rates"), function() {
				frm.call({
					method: "logistics.warehousing.doctype.warehouse_contract.warehouse_contract.get_rates_from_sales_quote",
					args: {
						warehouse_contract: frm.doc.name,
						sales_quote: frm.doc.sales_quote
					},
					callback: function(r) {
						if (r.message) {
							frm.refresh_field("items");
							frappe.show_alert({
								message: __("Rates have been successfully imported from Sales Quote"),
								indicator: "green"
							});
						}
					}
				});
			}, __("Actions"));
		}

		// Add Create menu buttons for linked doctypes (only when document is saved)
		if (!frm.is_new() && frm.doc.name) {
			frm.add_custom_button(__("Inbound Order"), function() {
				frappe.new_doc("Inbound Order", { contract: frm.doc.name, customer: frm.doc.customer });
			}, __("Create"));
			frm.add_custom_button(__("Release Order"), function() {
				frappe.new_doc("Release Order", { contract: frm.doc.name, customer: frm.doc.customer });
			}, __("Create"));
			frm.add_custom_button(__("Transfer Order"), function() {
				frappe.new_doc("Transfer Order", { contract: frm.doc.name, customer: frm.doc.customer });
			}, __("Create"));
			frm.add_custom_button(__("VAS Order"), function() {
				frappe.new_doc("VAS Order", { contract: frm.doc.name, customer: frm.doc.customer });
			}, __("Create"));
			frm.add_custom_button(__("Stocktake Order"), function() {
				frappe.new_doc("Stocktake Order", { contract: frm.doc.name, customer: frm.doc.customer });
			}, __("Create"));
			frm.add_custom_button(__("Warehouse Job"), function() {
				frappe.new_doc("Warehouse Job", { warehouse_contract: frm.doc.name, customer: frm.doc.customer });
			}, __("Create"));
		}
	},
	
	sales_quote(frm) {
		// Populate shipper and consignee from Sales Quote
		if (frm.doc.sales_quote) {
			frappe.db.get_value("Sales Quote", frm.doc.sales_quote, ["shipper", "consignee"], function(r) {
				if (r) {
					if (r.shipper) {
						frm.set_value("shipper", r.shipper);
					}
					if (r.consignee) {
						frm.set_value("consignee", r.consignee);
					}
				}
			});
		} else {
			// Clear shipper and consignee if sales_quote is cleared
			frm.set_value("shipper", "");
			frm.set_value("consignee", "");
		}
	}
});
