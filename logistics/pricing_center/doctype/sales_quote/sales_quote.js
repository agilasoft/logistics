// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Quote", {
	refresh(frm) {
		// Add custom button to create Transport Order if quote is One-Off and submitted
		if (frm.doc.one_off && frm.doc.transport && frm.doc.transport.length > 0 && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			// Always show create button - allow multiple Transport Orders from same Sales Quote
			frm.add_custom_button(__("Create Transport Order"), function() {
				create_transport_order_from_sales_quote(frm);
			}, __("Create"));
			
			// Also add a button to view existing Transport Orders if any exist
			frappe.db.get_value("Transport Order", {"sales_quote": frm.doc.name}, "name", function(r) {
				if (r && r.name) {
					frm.add_custom_button(__("View Transport Orders"), function() {
						frappe.route_options = {"sales_quote": frm.doc.name};
						frappe.set_route("List", "Transport Order");
					}, __("View"));
				}
			});
		}
	},
});

function create_transport_order_from_sales_quote(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Transport Order from this Sales Quote? You can create multiple orders from the same Sales Quote."),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Transport Order..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_transport_order_from_sales_quote",
				args: {
					sales_quote_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Transport Order Created"),
							message: __("Transport Order {0} has been created successfully.", [r.message.transport_order]),
							indicator: "green"
						});
						
						// Open the created Transport Order
						frappe.set_route("Form", "Transport Order", r.message.transport_order);
					} else if (r.message && r.message.message) {
						// Show info message (e.g., Transport Order already exists)
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						
						// Open existing Transport Order if available
						if (r.message.transport_order) {
							frappe.set_route("Form", "Transport Order", r.message.transport_order);
						}
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Transport Order. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}
