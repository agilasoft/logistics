// Copyright (c) 2026, logistics.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Prominent Create / View toolbar buttons for submitted parent docs that spawn a 1:1 child.
 * Avoids hidden "Create → …" dropdown items and deferred setTimeout races on form refresh.
 */
frappe.provide("logistics.submitted_child_doc_toolbar");

logistics.submitted_child_doc_toolbar.navigate_when_exists = function (
	target_doctype,
	docname,
	exists_method,
	max_attempts
) {
	max_attempts = max_attempts || 15;
	function try_navigate(attempt) {
		if (attempt > max_attempts) {
			frappe.set_route("Form", target_doctype, docname);
			return;
		}
		frappe.call({
			method: exists_method,
			args: { docname: docname },
			callback: function (res) {
				if (res.message === true) {
					frappe.set_route("Form", target_doctype, docname);
				} else {
					setTimeout(function () {
						try_navigate(attempt + 1);
					}, 300);
				}
			},
			error: function () {
				setTimeout(function () {
					try_navigate(attempt + 1);
				}, 300);
			},
		});
	}
	try_navigate(1);
};

/**
 * @param {frappe.ui.form.Form} frm
 * @param {object} opts
 * @param {string} opts.child_doctype
 * @param {function} opts.get_child_filters - (frm) => object
 * @param {string} opts.create_label
 * @param {string} opts.view_label
 * @param {string} [opts.confirm_message]
 * @param {string} opts.create_method
 * @param {function} opts.get_create_args - (frm) => object
 * @param {function} opts.on_success - (frm, response) => void
 * @param {function} [opts.when] - (frm) => boolean
 * @param {string} [opts.freeze_message]
 * @param {function} [opts.before_create] - (frm) => void
 * @param {function} [opts.on_child_exists] - (frm, child_name) => void
 */
logistics.submitted_child_doc_toolbar.add_create_or_view = function (frm, opts) {
	if (!frm || !frm.doc || !opts) {
		return;
	}
	if (opts.when && !opts.when(frm)) {
		return;
	}
	if (opts.require_submitted !== false) {
		if (window.logistics && logistics.menu && logistics.menu.is_submitted) {
			if (!logistics.menu.is_submitted(frm)) {
				return;
			}
		} else if (frm.doc.docstatus !== 1) {
			return;
		}
	}
	if (!frm.doc.name || frm.doc.__islocal || String(frm.doc.name).indexOf("new-") === 0) {
		return;
	}

	var parent_name = frm.doc.name;
	var child_filters =
		typeof opts.get_child_filters === "function" ? opts.get_child_filters(frm) : {};

	frappe.db.get_value(opts.child_doctype, child_filters, "name", function (r) {
		if (!frm.doc || frm.doc.name !== parent_name) {
			return;
		}
			if (r && r.name) {
			if (opts.require_read_perm !== false) {
				if (
					!window.logistics ||
					!logistics.menu ||
					!logistics.menu.can(opts.child_doctype, "read", frm)
				) {
					return;
				}
			}
			frm.add_custom_button(opts.view_label, function () {
				frappe.set_route("Form", opts.child_doctype, r.name);
			});
			if (opts.on_child_exists) {
				opts.on_child_exists(frm, r.name);
			}
			return;
		}

		function run_create() {
			if (opts.before_create) {
				opts.before_create(frm);
			}
			frappe.call({
				method: opts.create_method,
				args: opts.get_create_args(frm),
				freeze: true,
				freeze_message: opts.freeze_message || __("Creating..."),
				callback: function (resp) {
					if (resp.exc) {
						return;
					}
					if (opts.on_success) {
						opts.on_success(frm, resp);
					}
				},
			});
		}

		if (opts.require_create_perm !== false) {
			if (
				!window.logistics ||
				!logistics.menu ||
				!logistics.menu.can(opts.child_doctype, "create", frm)
			) {
				return;
			}
		}

		frm.add_custom_button(opts.create_label, function () {
			if (opts.confirm_message) {
				frappe.confirm(opts.confirm_message, run_create);
			} else {
				run_create();
			}
		});
		frm.change_custom_button_type(opts.create_label, null, "primary");
	});
};
