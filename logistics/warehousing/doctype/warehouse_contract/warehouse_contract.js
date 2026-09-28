// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Warehouse Contract", {
	setup(frm) {
		frm.set_query("sales_quote", function() {
			var filters = {
				service_type: "Warehousing",
				reference_doctype: "Warehouse Contract",
				reference_name: frm.doc.name || ""
			};
			if (frm.doc.customer) {
				filters.customer = frm.doc.customer;
			}
			return {
				query: "logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search",
				filters: filters
			};
		});
	},
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
			}, __("Action"));
		}

		// Add Create menu buttons for linked doctypes (only when submitted),
		// filtered by charge types present on contract items.
		if (window.logistics && logistics.menu && logistics.menu.is_submitted
			? logistics.menu.is_submitted(frm)
			: (!frm.is_new() && frm.doc.name && frm.doc.docstatus === 1)) {
			const hasCharge = (flag) => (frm.doc.items || []).some((row) => row[flag]);
			const orderDefaults = () =>
				(logistics.warehousing && logistics.warehousing.warehouse_order_defaults_from_contract
					? logistics.warehousing.warehouse_order_defaults_from_contract(frm.doc)
					: {
						contract: frm.doc.name,
						customer: frm.doc.customer,
						company: frm.doc.company,
						branch: frm.doc.branch,
						cost_center: frm.doc.cost_center,
						profit_center: frm.doc.profit_center,
					});

			if (hasCharge("inbound_charge")) {
				frm.add_custom_button(__("Inbound Order"), function() {
					frappe.new_doc("Inbound Order", orderDefaults());
				}, __("Create"));
			}
			if (hasCharge("outbound_charge")) {
				frm.add_custom_button(__("Release Order"), function() {
					frappe.new_doc("Release Order", orderDefaults());
				}, __("Create"));
			}
			if (hasCharge("cross_dock_charge")) {
				frm.add_custom_button(__("Cross-Docking Order"), function() {
					frappe.new_doc("Cross-Docking Order", orderDefaults());
				}, __("Create"));
			}
			if (hasCharge("transfer_charge")) {
				frm.add_custom_button(__("Transfer Order"), function() {
					frappe.new_doc("Transfer Order", orderDefaults());
				}, __("Create"));
			}
			if (hasCharge("vas_charge")) {
				frm.add_custom_button(__("VAS Order"), function() {
					frappe.new_doc("VAS Order", orderDefaults());
				}, __("Create"));
			}
			if (hasCharge("stocktake_charge")) {
				frm.add_custom_button(__("Stocktake Order"), function() {
					frappe.new_doc("Stocktake Order", orderDefaults());
				}, __("Create"));
			}
			frm.add_custom_button(__("Warehouse Job"), function() {
				const defaults = orderDefaults();
				frappe.new_doc("Warehouse Job", {
					warehouse_contract: defaults.contract,
					customer: defaults.customer,
					company: defaults.company,
					branch: defaults.branch,
					cost_center: defaults.cost_center,
					profit_center: defaults.profit_center,
				});
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
