// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt
//
// Gate custom form menus (Actions / Create / Post) with DocType permissions.
// Hide on the client; whitelist methods must still call logistics.utils.menu_permission.assert_perm.

frappe.provide("logistics.menu");

function _boot_user_can(list_name, doctype) {
	var user = frappe.boot && frappe.boot.user;
	var list = user && user[list_name];
	if (!list || !doctype) {
		return false;
	}
	return list.indexOf(doctype) !== -1;
}

function _can_create_doctype(doctype) {
	if (!doctype) {
		return false;
	}
	// in_create DocTypes are omitted from boot.user.can_create (hidden from Awesome Bar).
	if (_boot_user_can("can_create", doctype) || _boot_user_can("in_create", doctype)) {
		return true;
	}
	try {
		return typeof frappe.model.can_create === "function" && !!frappe.model.can_create(doctype);
	} catch (e) {
		return false;
	}
}

/**
 * @param {string} doctype
 * @param {string} ptype create|read|write|submit|delete|cancel
 * @param {frappe.ui.form.Form} [frm] when checking the open document, uses frm.has_perm
 * @returns {boolean}
 */
logistics.menu.can = function (doctype, ptype, frm) {
	ptype = String(ptype || "read").toLowerCase();
	if (!doctype) {
		return false;
	}
	if (frm && frm.doc && frm.doctype === doctype && typeof frm.has_perm === "function") {
		if (ptype === "create") {
			return _can_create_doctype(doctype);
		}
		// Submitted documents have write=0 in docinfo even when the role can write the DocType.
		// Convert / Action menus on submitted quotes must use role-level write, not frm.has_perm.
		if (ptype === "write" && (frm.doc.docstatus === 1 || frm.doc.docstatus === "1")) {
			return typeof frappe.model.can_write === "function" && !!frappe.model.can_write(doctype);
		}
		try {
			return !!frm.has_perm(ptype);
		} catch (e) {
			if (ptype === "write") {
				return typeof frappe.model.can_write === "function" && !!frappe.model.can_write(doctype);
			}
			if (ptype === "read") {
				return typeof frappe.model.can_read === "function" && !!frappe.model.can_read(doctype);
			}
			return false;
		}
	}
	if (ptype === "create") {
		return _can_create_doctype(doctype);
	}
	if (ptype === "write") {
		return typeof frappe.model.can_write === "function" && !!frappe.model.can_write(doctype);
	}
	if (ptype === "read") {
		return typeof frappe.model.can_read === "function" && !!frappe.model.can_read(doctype);
	}
	if (ptype === "delete") {
		return typeof frappe.model.can_delete === "function" && !!frappe.model.can_delete(doctype);
	}
	if (ptype === "submit") {
		if (typeof frappe.model.can_submit === "function") {
			return !!frappe.model.can_submit(doctype);
		}
		return _boot_user_can("can_submit", doctype);
	}
	if (ptype === "cancel") {
		return _boot_user_can("can_cancel", doctype);
	}
	if (frappe.perm && typeof frappe.perm.has_perm === "function") {
		return !!frappe.perm.has_perm(doctype, 0, ptype);
	}
	return false;
};

/**
 * @param {string[]} doctypes
 * @param {string} ptype
 * @returns {boolean}
 */
logistics.menu.can_any = function (doctypes, ptype) {
	if (!doctypes || !doctypes.length) {
		return false;
	}
	for (var i = 0; i < doctypes.length; i++) {
		if (logistics.menu.can(doctypes[i], ptype)) {
			return true;
		}
	}
	return false;
};

function _passes_requires(frm, opts) {
	if (opts.ptype !== false) {
		var doctype = opts.doctype || (frm && frm.doctype);
		var ptype = opts.ptype || "write";
		if (!logistics.menu.can(doctype, ptype, frm)) {
			return false;
		}
	}
	var also = opts.also || [];
	for (var i = 0; i < also.length; i++) {
		var req = also[i] || {};
		if (!logistics.menu.can(req.doctype, req.ptype || "read", frm)) {
			return false;
		}
	}
	return true;
}

/**
 * Add a custom button when DocType permission (and optional when()) pass.
 *
 * @param {frappe.ui.form.Form} frm
 * @param {object} opts
 * @param {string} opts.label
 * @param {function} opts.action
 * @param {string} [opts.group]
 * @param {string} [opts.doctype] defaults to frm.doctype
 * @param {string|false} [opts.ptype] create|read|write|submit; false skips the primary check
 * @param {Array<{doctype: string, ptype: string}>} [opts.also]
 * @param {function} [opts.when] extra document-state gate
 * @param {string} [opts.button_type] e.g. primary
 * @returns {*}
 */
logistics.menu.add = function (frm, opts) {
	opts = opts || {};
	if (!frm || !frm.doc || !opts.label || typeof opts.action !== "function") {
		return null;
	}
	if (typeof opts.when === "function" && !opts.when(frm)) {
		return null;
	}
	if (!_passes_requires(frm, opts)) {
		return null;
	}
	frm._logistics_menu_checked = true;
	var btn = null;
	try {
		btn = frm.add_custom_button(opts.label, opts.action, opts.group);
	} finally {
		frm._logistics_menu_checked = false;
	}
	if (opts.button_type && typeof frm.change_custom_button_type === "function") {
		frm.change_custom_button_type(opts.label, opts.group || null, opts.button_type);
	}
	if (opts.css_class && btn && typeof btn.addClass === "function") {
		btn.addClass(opts.css_class);
	}
	return btn;
};

/**
 * Standard gate for Create → next document (booking → shipment, order → job).
 * Submitted only (docstatus = 1). Draft and cancelled are excluded.
 */
logistics.menu.is_submitted = function (frm) {
	return !!(
		frm &&
		frm.doc &&
		frm.doc.name &&
		!frm.doc.__islocal &&
		String(frm.doc.name).indexOf("new-") !== 0 &&
		(frm.doc.docstatus === 1 || frm.doc.docstatus === "1")
	);
};

/**
 * Run Create-button setup now and again after workflow toolbar refresh.
 */
logistics.menu.when_submitted = function (frm, fn, delay_ms) {
	if (typeof fn !== "function" || !logistics.menu.is_submitted(frm)) {
		return;
	}
	fn(frm);
	setTimeout(function () {
		if (logistics.menu.is_submitted(frm)) {
			fn(frm);
		}
	}, delay_ms || 400);
};

logistics.menu.INTERNAL_JOB_TYPES = [
	"Transport Order",
	"Declaration Order",
	"Air Booking",
	"Sea Booking",
	"VAS Order",
	"Cross-Docking Order",
	"MICE Order",
];

/** Targets created from a Sales Quote Convert menu (Regular dialog + One-off Create). */
logistics.menu.SALES_QUOTE_CONVERT_TYPES = [
	"Air Booking",
	"Sea Booking",
	"Transport Order",
	"Declaration Order",
	"Warehouse Contract",
	"Inbound Order",
	"Cross-Docking Order",
	"Time Sensitive Case",
];

/**
 * Create-or-view toolbar for a 1:1 child, with create/read gates.
 * Delegates to logistics.submitted_child_doc_toolbar when that helper is loaded.
 *
 * @param {frappe.ui.form.Form} frm
 * @param {object} opts same as submitted_child_doc_toolbar.add_create_or_view
 */
logistics.menu.add_create_or_view = function (frm, opts) {
	opts = opts || {};
	if (window.logistics && logistics.submitted_child_doc_toolbar && logistics.submitted_child_doc_toolbar.add_create_or_view) {
		return logistics.submitted_child_doc_toolbar.add_create_or_view(frm, opts);
	}
	return null;
};

function _label_text(v) {
	if (v == null) {
		return "";
	}
	if (typeof v === "object" && v.message) {
		return String(v.message);
	}
	return String(v);
}

function _eq_label(actual, expected) {
	return _label_text(actual) === _label_text(expected);
}

function _create_target_from_label(frm, label) {
	var dt = frm && frm.doctype;
	var pairs = [
		[__("Sales Invoice"), "Sales Invoice"],
		[__("Create Sales Invoice"), "Sales Invoice"],
		[__("Purchase Invoice"), "Purchase Invoice"],
		[__("Change Request"), "Change Request"],
		[__("Create Change Request"), "Change Request"],
		[__("Warehouse Job"), "Warehouse Job"],
		[__("Create Warehouse Job"), "Warehouse Job"],
		[__("Run Sheet"), "Run Sheet"],
		[__("Run Sheets"), "Run Sheet"],
		[__("Create Run Sheet"), "Run Sheet"],
		[__("Create Transport Order"), "Transport Order"],
		[__("Create Air Booking"), "Air Booking"],
		[__("Create Sea Booking"), "Sea Booking"],
		[__("Create Declaration"), "Declaration"],
		[__("Declaration Order"), "Declaration Order"],
		[__("Permit Application"), "Permit Application"],
		[__("Exemption Certificate"), "Exemption Certificate"],
		[__("IATA / e-AWB"), "Air Shipment IATA Transaction"],
		[__("Create e-AWB"), "Air Shipment IATA Transaction"],
		[__("Create Draft Purchase Invoices"), "Purchase Invoice"],
		[__("Create Gate Passes"), "Gate Pass"],
		[__("Create Warehouse Contract"), "Warehouse Contract"],
		[__("Create Special Project"), "Special Project"],
		[__("Create Docket"), "Docket"],
		[__("Sales Quote"), "Sales Quote"],
		[__("Create Sales Quote"), "Sales Quote"],
		[__("Add Sales Quote"), "Sales Quote"],
		[__("Inbound Order"), "Inbound Order"],
		[__("Release Order"), "Release Order"],
		[__("Cross-Docking Order"), "Cross-Docking Order"],
		[__("Transfer Order"), "Transfer Order"],
		[__("VAS Order"), "VAS Order"],
		[__("Stocktake Order"), "Stocktake Order"],
		[__("Create Time Sensitive Case"), "Time Sensitive Case"],
		[__("Add Air Shipment"), "Air Shipment"],
		[__("Issue from Stock"), "Master Air Waybill"],
	];
	for (var i = 0; i < pairs.length; i++) {
		if (_eq_label(label, pairs[i][0])) {
			return pairs[i][1];
		}
	}
	if (_eq_label(label, __("Shipment"))) {
		if (dt === "Air Booking") {
			return "Air Shipment";
		}
		if (dt === "Sea Booking") {
			return "Sea Shipment";
		}
	}
	if (_eq_label(label, __("Job")) && dt === "MICE Order") {
		return "MICE Job";
	}
	if (_eq_label(label, __("Create Job")) && dt === "Exhibit Order") {
		return "Exhibit Job";
	}
	if (_eq_label(label, __("Declaration")) && dt === "Declaration Order") {
		return "Declaration";
	}
	return null;
}

function _view_target_from_label(label) {
	var pairs = [
		[__("View Air Shipment"), "Air Shipment"],
		[__("View Declaration"), "Declaration"],
		[__("View Declaration Order"), "Declaration Order"],
		[__("View Sales Quote"), "Sales Quote"],
		[__("View Sales Invoice"), "Sales Invoice"],
		[__("View Warehouse Contracts"), "Warehouse Contract"],
		[__("View Declaration Orders"), "Declaration Order"],
		[__("View Gate Passes"), "Gate Pass"],
		[__("View CASS Billing"), "CASS Settlement Period"],
		[__("View Call-Offs"), "Sales Quote"],
		[__("View Transport Orders"), "Transport Order"],
		[__("View Air Bookings"), "Air Booking"],
		[__("View Sea Bookings"), "Sea Booking"],
		[__("MICE Job"), "MICE Job"],
		[__("Open Case"), "Time Sensitive Case"],
		[__("Open Project"), "Project"],
		[__("Open Exhibit"), "MICE Project"],
		[__("Open Connected App"), "Connected App"],
	];
	for (var i = 0; i < pairs.length; i++) {
		if (_eq_label(label, pairs[i][0])) {
			return pairs[i][1];
		}
	}
	return null;
}

function _is_internal_job_label(label) {
	return (
		_eq_label(label, __("Booking / Order")) ||
		_eq_label(label, __("Internal Job")) ||
		_eq_label(label, __("Create Call-Off / New Booking…"))
	);
}

function _is_intercompany_label(label) {
	return _eq_label(label, __("Intercompany Transactions"));
}

function _is_action_group(group) {
	return _label_text(group) === _label_text(__("Action"));
}

/**
 * Same label is used for View (Action) and Create on Transport/Project Job.
 */
function _job_button_from_group(label, group) {
	if (_eq_label(label, __("Transport Job"))) {
		return {
			doctype: "Transport Job",
			ptype: _is_action_group(group) ? "read" : "create",
		};
	}
	if (_eq_label(label, __("Project Job"))) {
		return {
			doctype: "Project Job",
			ptype: _is_action_group(group) ? "read" : "create",
		};
	}
	return null;
}

function _is_gl_post_label(label, group) {
	var g = _label_text(group);
	if (
		_eq_label(label, __("WIP and Accrual")) ||
		_eq_label(label, __("Adjust WIP")) ||
		_eq_label(label, __("Adjust Accruals")) ||
		_eq_label(label, __("Close Recognition")) ||
		_eq_label(label, __("Standard Costs")) ||
		_eq_label(label, __("Post Standard Costs")) ||
		_eq_label(label, __("Internal Billing"))
	) {
		return true;
	}
	// Recognition group is GL. Do not treat Warehouse Job "Post" (stock) as JE create.
	return g === _label_text(__("Recognition"));
}

/**
 * Infer DocType permission for a leftover add_custom_button call.
 * @returns {{doctype: string, ptype: string, also?: Array}|{any: string[], ptype: string}|null}
 */
logistics.menu.infer = function (frm, label, group) {
	if (!frm || !frm.doctype) {
		return { doctype: null, ptype: "write" };
	}
	var view_dt = _view_target_from_label(label);
	if (view_dt) {
		return { doctype: view_dt, ptype: "read" };
	}
	if (_is_internal_job_label(label)) {
		// Quote convert is an action on the open quote; target create is enforced on the server.
		if (frm.doctype === "Sales Quote") {
			return null;
		}
		return { any: logistics.menu.INTERNAL_JOB_TYPES, ptype: "create" };
	}
	var job_btn = _job_button_from_group(label, group);
	if (job_btn) {
		return job_btn;
	}
	var create_dt = _create_target_from_label(frm, label);
	if (create_dt) {
		var convert = logistics.menu.SALES_QUOTE_CONVERT_TYPES || [];
		if (frm.doctype === "Sales Quote" && convert.indexOf(create_dt) !== -1) {
			return null;
		}
		return { doctype: create_dt, ptype: "create" };
	}
	if (_is_intercompany_label(label)) {
		return {
			doctype: frm.doctype,
			ptype: "write",
			also: [
				{ doctype: "Sales Invoice", ptype: "create" },
				{ doctype: "Purchase Invoice", ptype: "create" },
			],
		};
	}
	if (_is_gl_post_label(label, group)) {
		return {
			doctype: frm.doctype,
			ptype: "write",
			also: [{ doctype: "Journal Entry", ptype: "create" }],
		};
	}
	return { doctype: frm.doctype, ptype: "write" };
};

function _infer_allows(frm, inferred) {
	if (!inferred) {
		return true;
	}
	if (inferred.any) {
		return logistics.menu.can_any(inferred.any, inferred.ptype || "create");
	}
	if (!logistics.menu.can(inferred.doctype, inferred.ptype || "write", frm)) {
		return false;
	}
	var also = inferred.also || [];
	for (var i = 0; i < also.length; i++) {
		if (!logistics.menu.can(also[i].doctype, also[i].ptype || "read", frm)) {
			return false;
		}
	}
	return true;
}

function _install_form_button_gate() {
	if (!frappe.ui || !frappe.ui.form || !frappe.ui.form.Form) {
		setTimeout(_install_form_button_gate, 50);
		return;
	}
	var proto = frappe.ui.form.Form.prototype;
	if (proto._logistics_menu_gated) {
		return;
	}
	proto._logistics_menu_gated = true;
	var orig = proto.add_custom_button;
	proto.add_custom_button = function (label, fn, group) {
		if (this._logistics_menu_checked || this.doctype === "Sales Quote") {
			return orig.call(this, label, fn, group);
		}
		if (!_infer_allows(this, logistics.menu.infer(this, label, group))) {
			return;
		}
		return orig.call(this, label, fn, group);
	};
}

try {
	_install_form_button_gate();
} catch (e) {
	console.error("logistics.menu button gate", e);
}

