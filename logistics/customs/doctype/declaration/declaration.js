// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Declaration', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	}).always(function() {
		setTimeout(function() { frm._milestone_html_called = false; }, 2000);
	});
}

frappe.ui.form.on("Declaration", {
	refresh(frm) {
		// Filter Declaration Product Code by importer/exporter for line items
		frm.set_query("declaration_product_code", "commercial_invoice_line_items", function() {
			const filters = [["Declaration Product Code", "active", "=", 1]];
			if (frm.doc.importer_consignee) {
				filters.push(["Declaration Product Code", "importer", "in", ["", frm.doc.importer_consignee]]);
			}
			if (frm.doc.exporter_shipper) {
				filters.push(["Declaration Product Code", "exporter", "in", ["", frm.doc.exporter_shipper]]);
			}
			return { filters };
		});
		// Load dashboard HTML in Dashboard tab (only when doc is saved)
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frm.call("get_dashboard_html").then((r) => {
					if (r.message && frm.fields_dict.dashboard_html) {
						frm.fields_dict.dashboard_html.$wrapper.html(r.message);
						if (window.logistics_bind_document_alert_cards) {
							window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
						}
					}
				}).catch(() => {}).always(() => {
					setTimeout(() => { frm._dashboard_html_called = false; }, 2000);
				});
			}
		}
		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
				_load_milestone_html(frm);
			});
		}

		// Populate Documents from Template
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__("Populate from Template"), function() {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Declaration", docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					}
				});
			}, __("Documents"));
		}

		// Generate from template button in Milestones section
		if (!frm.doc.__islocal && frm.fields_dict.milestones) {
			frm.add_custom_button(__('Generate from Template'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Declaration', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Milestones'));
		}

		// Add custom button to create Sales Invoice if declaration is submitted
		if (frm.doc.docstatus === 1 && !frm.doc.__islocal) {
			// Check if Sales Invoice already exists
			if (frm.doc.job_costing_number) {
				frappe.db.get_value("Sales Invoice", {"job_costing_number": frm.doc.job_costing_number}, "name", function(r) {
					if (r && r.name) {
						// Show view button if invoice exists
						frm.add_custom_button(__("View Sales Invoice"), function() {
							frappe.set_route("Form", "Sales Invoice", r.name);
						}, __("Actions"));
					} else {
						// Show create button if no invoice exists
						frm.add_custom_button(__("Create Sales Invoice"), function() {
							create_sales_invoice_from_declaration(frm);
						}, __("Post"));
					}
				});
			} else {
				// Show create button if no job costing number
				frm.add_custom_button(__("Create Sales Invoice"), function() {
					create_sales_invoice_from_declaration(frm);
				}, __("Post"));
			}
		}
		
		// Add button to view Declaration Order if linked
		if (frm.doc.declaration_order) {
			frm.add_custom_button(__("View Declaration Order"), function() {
				frappe.set_route("Form", "Declaration Order", frm.doc.declaration_order);
			}, __("Actions"));
		}
		// Add button to view Sales Quote if linked
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__("View Sales Quote"), function() {
				frappe.set_route("Form", "Sales Quote", frm.doc.sales_quote);
			}, __("Actions"));
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
