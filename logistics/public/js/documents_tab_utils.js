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

// Defensive patch: some forms can carry table controls whose grid pagination is not initialized
// yet at switch time, which crashes Form.switch_doc on go_to_page(). Initialize lazily first.
(function patch_form_switch_doc_for_grid_pagination() {
	if (!frappe || !frappe.ui || !frappe.ui.form || !frappe.ui.form.Form) return;
	const Form = frappe.ui.form.Form;
	if (Form.__logistics_switch_doc_patched) return;

	const original_switch_doc = Form.prototype.switch_doc;
	if (typeof original_switch_doc !== "function") return;

	Form.prototype.switch_doc = function (docname) {
		(this.grids || []).forEach((grid_obj) => {
			const grid = grid_obj && grid_obj.grid;
			if (!grid) return;
			if (!grid.grid_pagination && typeof grid.setup_grid_pagination === "function") {
				try {
					grid.setup_grid_pagination();
				} catch (e) {
					// Keep original flow; this is only a best-effort initializer.
				}
			}
		});
		return original_switch_doc.call(this, docname);
	};

	Form.__logistics_switch_doc_patched = true;
})();
