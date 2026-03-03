// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: "Sea Consolidation", docname: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		},
	}).always(function () {
		setTimeout(function () {
			frm._milestone_html_called = false;
		}, 2000);
	});
}

function _load_documents_html(frm) {
	if (!frm.fields_dict.documents_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._documents_html_called) return;
	frm._documents_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_document_alerts_html",
		args: { doctype: "Sea Consolidation", docname: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.documents_html) {
				frm.fields_dict.documents_html.$wrapper.html(r.message);
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.documents_html.$wrapper);
				}
			}
		},
	}).always(function () {
		setTimeout(function () {
			frm._documents_html_called = false;
		}, 2000);
	});
}

frappe.ui.form.on("Sea Consolidation", {
	refresh: function (frm) {
		// Dashboard tab
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frm.call("get_dashboard_html").then(function (r) {
					if (r.message && frm.fields_dict.dashboard_html) {
						frm.fields_dict.dashboard_html.$wrapper.html(r.message);
						if (window.logistics_bind_document_alert_cards) {
							window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
						}
					}
				});
				setTimeout(function () {
					frm._dashboard_html_called = false;
				}, 2000);
			}
		}
		_load_documents_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				_load_documents_html(frm);
			});
		}
		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.milestone_html").on("click.milestone_html", '[data-fieldname="milestones_tab"]', function () {
				_load_milestone_html(frm);
			});
		}
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Get Milestones"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_milestones_from_template",
					args: { doctype: "Sea Consolidation", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Actions"));
			frm.add_custom_button(__("Get Documents"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Sea Consolidation", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Actions"));
		}
		if (frm.doc.consolidation_charges && frm.doc.consolidation_charges.length > 0) {
			frm.add_custom_button(__("Calculate Charges"), function () {
				frappe.call({
					method: "logistics.sea_freight.doctype.sea_consolidation.sea_consolidation.recalculate_all_charges",
					args: { docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "green" }, 3);
						}
					},
				});
			}, __("Actions"));
		}
		if (frm.doc.origin_port && frm.doc.destination_port) {
			frm.add_custom_button(__("Populate from Ports"), function () {
				frappe.call({
					method: "logistics.sea_freight.doctype.sea_consolidation.sea_consolidation.populate_routing_from_ports",
					args: { docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.message) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "green" }, 3);
						}
					},
				});
			}, __("Actions"));
		}
	},
});

