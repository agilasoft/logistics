// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Prevent a non-active Form (e.g. Air Shipment) from updating the desk/tab title after the user has
 * navigated to another DocType (e.g. Declaration Order). Async reload_doc/refresh can finish later and
 * call refresh_header → frappe.utils.set_title with the wrong document.
 *
 * Context guard: only the active desk form (`cur_frm`) may update the global title.
 * Route guard: if `cur_frm` is not yet set, allow only when the desk route still targets this form.
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
		if (typeof cur_frm !== "undefined" && cur_frm !== null) {
			return cur_frm === frm;
		}
		return _route_targets_form(frm);
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
			if (_may_update_desk_title(this.frm)) {
				return orig_toolbar_set_title.apply(this, arguments);
			}
			var _set2 = frappe.utils.set_title;
			frappe.utils.set_title = function () {};
			try {
				return orig_toolbar_set_title.apply(this, arguments);
			} finally {
				frappe.utils.set_title = _set2;
			}
		};
	}
})();
