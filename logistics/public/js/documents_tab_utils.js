// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Template field triggers (document_list_template / milestone_template) are defined in each
 * doctype's form script and use frappe.call() to populate documents/milestones when the field changes.
 */

/**
 * Load document alerts HTML into documents_html field. Call from form refresh.
 * @param {object} frm - Frappe form
 * @param {string} doctype - DocType name (e.g. 'Air Booking', 'Declaration')
 */
window.logistics_load_documents_html = function (frm, doctype) {
	if (!frm.fields_dict.documents_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._documents_html_called) return;
	frm._documents_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_document_alerts_html",
		args: { doctype: doctype, docname: frm.doc.name },
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
};
