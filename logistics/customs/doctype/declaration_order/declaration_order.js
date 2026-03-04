// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Declaration Order', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	}).always(function() {
		setTimeout(function() { frm._milestone_html_called = false; }, 2000);
	});
}

function _populate_charges_from_sales_quote(frm) {
	var sales_quote = frm.doc.sales_quote;
	if (!sales_quote) return;
	frappe.call({
		method: "logistics.customs.doctype.declaration_order.declaration_order.populate_charges_from_sales_quote",
		args: { docname: frm.doc.name, sales_quote: sales_quote },
		freeze: true,
		freeze_message: __("Fetching charges from Sales Quote..."),
		callback: function(r) {
			if (r.message) {
				if (r.message.error) {
					frappe.msgprint({ title: __("Error"), message: r.message.error, indicator: "red" });
					return;
				}
				if (r.message.charges && r.message.charges.length > 0) {
					frm.clear_table("charges");
					r.message.charges.forEach(function(charge) {
						var row = frm.add_child("charges");
						Object.keys(charge).forEach(function(key) {
							if (charge[key] !== null && charge[key] !== undefined) {
								row[key] = charge[key];
							}
						});
					});
					frm.refresh_field("charges");
					if (r.message.charges_count > 0) {
						frappe.show_alert({
							message: __("Populated {0} charges from Sales Quote", [r.message.charges_count]),
							indicator: "green"
						}, 3);
					}
				} else {
					frm.clear_table("charges");
					frm.refresh_field("charges");
				}
			}
		}
	});
}

frappe.ui.form.on("Declaration Order", {
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
		// Load milestone HTML in Milestones tab
		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
				_load_milestone_html(frm);
			});
		}

		// Get Milestones button
		if (!frm.doc.__islocal && frm.fields_dict.milestones) {
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Declaration Order', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Milestones'));
		}

		// Populate Documents from Template
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__("Populate from Template"), function() {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Declaration Order", docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					}
				});
			}, __("Documents"));
		}

		// View Sales Quote
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__("View Sales Quote"), function() {
				frappe.set_route("Form", "Sales Quote", frm.doc.sales_quote);
			}, __("View"));
		}
		// Create Declaration or View Declaration
		if (!frm.doc.__islocal && frm.doc.sales_quote) {
			frappe.db.get_value("Declaration", { declaration_order: frm.doc.name, docstatus: ["<", 2] }, "name", function(r) {
				if (r && r.name) {
					frm.add_custom_button(__("View Declaration"), function() {
						frappe.set_route("Form", "Declaration", r.name);
					}, __("Create"));
				} else {
					frm.add_custom_button(__("Create Declaration"), function() {
						frappe.call({
							method: "logistics.customs.doctype.declaration.declaration.create_declaration_from_declaration_order",
							args: { declaration_order_name: frm.doc.name },
							callback: function(res) {
								if (res.exc) return;
								if (res.message && res.message.success && res.message.declaration) {
									frappe.msgprint({
										title: __("Declaration Created"),
										message: __("Declaration {0} created.", [res.message.declaration]),
										indicator: "green"
									});
									setTimeout(function() {
										frappe.set_route("Form", "Declaration", res.message.declaration);
									}, 100);
								}
							}
						});
					}, __("Create"));
				}
			});
		}
	},
	sales_quote(frm) {
		if (!frm.doc.sales_quote) {
			frm.clear_table("charges");
			frm.refresh_field("charges");
			return;
		}
		frappe.call({
			method: "logistics.customs.doctype.declaration_order.declaration_order.get_sales_quote_details",
			args: { sales_quote: frm.doc.sales_quote },
			callback: function(r) {
				if (r.message) {
					const msg = r.message;
					if (!frm.doc.customer) frm.set_value("customer", msg.customer || "");
					if (!frm.doc.company) frm.set_value("company", msg.company || "");
					if (!frm.doc.customs_authority) frm.set_value("customs_authority", msg.customs_authority || "");
					if (!frm.doc.branch) frm.set_value("branch", msg.branch || "");
					if (!frm.doc.cost_center) frm.set_value("cost_center", msg.cost_center || "");
					if (!frm.doc.profit_center) frm.set_value("profit_center", msg.profit_center || "");
					if (!frm.doc.declaration_type) frm.set_value("declaration_type", msg.declaration_type || "");
					if (!frm.doc.incoterm) frm.set_value("incoterm", msg.incoterm || "");
				}
			}
		});
		_populate_charges_from_sales_quote(frm);
	}
});
