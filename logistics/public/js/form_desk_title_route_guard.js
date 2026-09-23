// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Prevent a non-active Form (e.g. Air Shipment) from updating the desk/tab title after the user has
 * navigated to another DocType (e.g. Transport Order). Async reload_doc/refresh can finish later and
 * call refresh_header → frappe.utils.set_title with the wrong document.
 *
 * Route guard: the desk route must still be Form / this.doctype / this doc (the doc being shown).
 * This covers same-doctype navigation where `cur_frm` is the same Form instance but the document changed.
 * Instance guard: when `cur_frm` is set, it must be this form so a background form cannot update the title.
 */
(function () {
	"use strict";
	if (window.__logistics_desk_title_route_guard__) {
		return;
	}
	window.__logistics_desk_title_route_guard__ = true;

	function _route_targets_form(frm) {
		var r = frappe.get_route && frappe.get_route();
		if (!r || r[0] !== "Form" || !frm) {
			return false;
		}
		return r[1] === frm.doctype && String(r[2] || "") === String(frm.docname || "");
	}

	function _may_update_desk_title(frm) {
		if (!frm) {
			return true;
		}
		if (frm.meta && frm.meta.in_dialog && !frm.in_form) {
			return true;
		}
		if (!_route_targets_form(frm)) {
			return false;
		}
		if (typeof cur_frm !== "undefined" && cur_frm !== null && cur_frm !== frm) {
			return false;
		}
		return true;
	}

	function _route_still_form_doctype_name(doctype, name) {
		var r = frappe.get_route && frappe.get_route();
		if (!r || r[0] !== "Form" || !doctype) {
			return false;
		}
		return r[1] === doctype && String(r[2] || "") === String(name || "");
	}

	var orig_refresh_header = frappe.ui.form.Form.prototype.refresh_header;
	frappe.ui.form.Form.prototype.refresh_header = function (switched) {
		if (_may_update_desk_title(this)) {
			return orig_refresh_header.apply(this, arguments);
		}
		var _set = frappe.utils.set_title;
		frappe.utils.set_title = function () {};
		try {
			return orig_refresh_header.apply(this, arguments);
		} finally {
			frappe.utils.set_title = _set;
		}
	};

	if (frappe.ui.form.Toolbar) {
		var orig_toolbar_set_title = frappe.ui.form.Toolbar.prototype.set_title;
		frappe.ui.form.Toolbar.prototype.set_title = function () {
			if (!_may_update_desk_title(this.frm)) {
				return;
			}
			return orig_toolbar_set_title.apply(this, arguments);
		};
	}

	if (frappe.ui.Page && frappe.ui.Page.prototype.set_title) {
		var orig_page_set_title = frappe.ui.Page.prototype.set_title;
		frappe.ui.Page.prototype.set_title = function () {
			if (!this.frm || _may_update_desk_title(this.frm)) {
				return orig_page_set_title.apply(this, arguments);
			}
			var _set = frappe.utils.set_title;
			frappe.utils.set_title = function () {};
			try {
				return orig_page_set_title.apply(this, arguments);
			} finally {
				frappe.utils.set_title = _set;
			}
		};
	}

	frappe.ui.form.Form.prototype.reload_doc = function () {
		var reload_name = this.docname;
		if (
			!reload_name ||
			String(reload_name).toLowerCase() === "undefined" ||
			String(reload_name).toLowerCase() === "null"
		) {
			return Promise.resolve();
		}

		this.check_doctype_conflict(reload_name);

		if (this.doc && this.doc.__islocal) {
			return Promise.resolve();
		}

		var me = this;
		var reload_doctype = this.doctype;

		frappe.model.remove_from_locals(this.doctype, reload_name);
		return frappe.model.with_doc(this.doctype, reload_name, function () {
			if (!_route_still_form_doctype_name(reload_doctype, reload_name)) {
				return;
			}
			if (typeof cur_frm !== "undefined" && cur_frm !== null && cur_frm !== me) {
				return;
			}
			me.refresh();
		});
	};
})();
