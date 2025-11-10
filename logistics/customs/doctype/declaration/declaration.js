// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Declaration", {
	refresh(frm) {
		// Add custom button to create Sales Invoice if declaration is submitted
		if (frm.doc.docstatus === 1 && !frm.doc.__islocal) {
			// Check if Sales Invoice already exists
			if (frm.doc.job_costing_number) {
				frappe.db.get_value("Sales Invoice", {"job_costing_number": frm.doc.job_costing_number}, "name", function(r) {
					if (r && r.name) {
						// Show view button if invoice exists
						frm.add_custom_button(__("View Sales Invoice"), function() {
							frappe.set_route("Form", "Sales Invoice", r.name);
						}, __("Create"));
					} else {
						// Show create button if no invoice exists
						frm.add_custom_button(__("Create Sales Invoice"), function() {
							create_sales_invoice_from_declaration(frm);
						}, __("Create"));
					}
				});
			} else {
				// Show create button if no job costing number
				frm.add_custom_button(__("Create Sales Invoice"), function() {
					create_sales_invoice_from_declaration(frm);
				}, __("Create"));
			}
		}
		
		// Add button to view Sales Quote if linked
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__("View Sales Quote"), function() {
				frappe.set_route("Form", "Sales Quote", frm.doc.sales_quote);
			}, __("View"));
		}
	},
});

function create_sales_invoice_from_declaration(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Sales Invoice from this Declaration?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Sales Invoice..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.customs.doctype.declaration.declaration.create_sales_invoice",
				args: {
					declaration_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Sales Invoice Created"),
							message: __("Sales Invoice {0} has been created successfully.", [r.message.sales_invoice]),
							indicator: "green"
						});
						
						// Open the created Sales Invoice
						frappe.set_route("Form", "Sales Invoice", r.message.sales_invoice);
					} else if (r.message && r.message.message) {
						// Show error message
						frappe.msgprint({
							title: __("Error"),
							message: r.message.message,
							indicator: "red"
						});
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Sales Invoice. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}
