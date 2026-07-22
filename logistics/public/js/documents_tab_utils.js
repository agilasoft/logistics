// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Template field triggers (document_list_template / milestone_template) are defined in each
 * doctype's form script and use frappe.call() to populate documents/milestones when the field changes.
 */

frappe.provide("logistics");

/**
 * Run fn after the form has painted (idle callback with timeout fallback).
 */
logistics.schedule_idle = function (fn) {
	if (typeof requestIdleCallback === "function") {
		requestIdleCallback(fn, { timeout: 500 });
	} else {
		setTimeout(fn, 50);
	}
};

/**
 * True when the given Tab Break field is the active tab (or dashboard on first paint).
 */
logistics.is_form_tab_active = function (frm, tab_fieldname) {
	var field = frm.fields_dict && frm.fields_dict[tab_fieldname];
	if (field && field.tab && typeof field.tab.is_active === "function") {
		return field.tab.is_active();
	}
	return tab_fieldname === "dashboard_tab";
};

/**
 * Clear lazy-tab load cache so the next visit re-fetches (pass loader keys or omit for all).
 */
logistics.invalidate_lazy_tab_loaders = function (frm, loader_keys) {
	if (!frm._logistics_lazy_tab_loaded) {
		return;
	}
	if (!loader_keys) {
		frm._logistics_lazy_tab_loaded = {};
		return;
	}
	(loader_keys || []).forEach(function (key) {
		delete frm._logistics_lazy_tab_loaded[key];
	});
};

/**
 * Bind a tab-scoped loader: fetch when the tab is opened; defer once if that tab is already active.
 *
 * @param {object} frm
 * @param {string} tab_fieldname - Tab Break fieldname (e.g. "dashboard_tab")
 * @param {string} loader_key - unique cache key per loader
 * @param {function} load_fn - function(frm, opts) where opts = { force, done }
 * @param {{ defer_if_active?: boolean }} options
 */
logistics.bind_lazy_tab_loader = function (frm, tab_fieldname, loader_key, load_fn, options) {
	options = options || {};
	var defer_if_active = options.defer_if_active !== false;

	if (!frm._logistics_lazy_tab_inflight) {
		frm._logistics_lazy_tab_inflight = {};
	}
	if (!frm._logistics_lazy_tab_loaded) {
		frm._logistics_lazy_tab_loaded = {};
	}

	function run(force) {
		var docname = frm.doc && frm.doc.name;
		if (!docname || frm.doc.__islocal) {
			return;
		}
		if (!force && frm._logistics_lazy_tab_loaded[loader_key] === docname) {
			return;
		}
		if (frm._logistics_lazy_tab_inflight[loader_key]) {
			return;
		}
		frm._logistics_lazy_tab_inflight[loader_key] = true;
		load_fn(frm, {
			force: !!force,
			done: function () {
				frm._logistics_lazy_tab_inflight[loader_key] = false;
				frm._logistics_lazy_tab_loaded[loader_key] = docname;
			},
		});
	}

	if (!frm._logistics_lazy_tab_bindings) {
		frm._logistics_lazy_tab_bindings = {};
	}
	frm._logistics_lazy_tab_bindings[tab_fieldname] = { loader_key: loader_key, run: run };

	if (frm.layout && frm.layout.wrapper) {
		frm.layout.wrapper
			.off("click.lazy_tab." + loader_key)
			.on(
				"click.lazy_tab." + loader_key,
				'[data-fieldname="' + tab_fieldname + '"]',
				function () {
					run(true);
				}
			);
	}

	if (defer_if_active && logistics.is_form_tab_active(frm, tab_fieldname)) {
		logistics.schedule_idle(function () {
			run(false);
		});
	}
};

/**
 * Run the lazy-tab loader registered for tab_fieldname (e.g. from on_tab_change).
 */
logistics.trigger_lazy_tab_loaders = function (frm, tab_fieldname, force) {
	var binding =
		frm._logistics_lazy_tab_bindings && frm._logistics_lazy_tab_bindings[tab_fieldname];
	if (binding && binding.run) {
		binding.run(force !== false);
	}
};

/**
 * Load document alerts HTML into documents_html field (lazy-tab friendly).
 * @param {object} frm - Frappe form
 * @param {string} doctype - DocType name (e.g. 'Air Booking', 'Declaration')
 * @param {{ force?: boolean, done?: function }} opts
 */
window.logistics_load_documents_html = function (frm, doctype, opts) {
	opts = opts || {};
	if (!frm.fields_dict.documents_html || !frm.doc.name || frm.doc.__islocal) {
		if (opts.done) {
			opts.done();
		}
		return;
	}
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
		if (opts.done) {
			opts.done();
		}
	});
};

// Defensive patch: table controls are added to frm.grids before Grid.make(), so
// grid_pagination may be missing at switch time. Frappe's Form.switch_doc always
// calls go_to_page() and crashes. Mirror switch_doc but guard pagination access.
(function patch_form_switch_doc_for_grid_pagination() {
	if (!frappe || !frappe.ui || !frappe.ui.form || !frappe.ui.form.Form) return;
	const Form = frappe.ui.form.Form;
	if (Form.__logistics_switch_doc_patched) return;
	if (typeof Form.prototype.switch_doc !== "function") return;

	Form.prototype.switch_doc = function (docname) {
		(this.grids || []).forEach((grid_obj) => {
			const grid = grid_obj && grid_obj.grid;
			if (!grid) return;

			grid.visible_columns = null;

			// Only init pagination when the grid DOM exists; GridPagination needs wrapper.
			// Do not call Grid.make() here (data may be unset; see sales_quote.js).
			if (
				!grid.grid_pagination &&
				grid.wrapper &&
				typeof grid.setup_grid_pagination === "function"
			) {
				try {
					if (!Array.isArray(grid.data)) {
						grid.data = [];
					}
					grid.setup_grid_pagination();
				} catch (e) {
					// Best-effort; skip go_to_page below if still missing.
				}
			}

			if (grid.grid_pagination && typeof grid.grid_pagination.go_to_page === "function") {
				grid.grid_pagination.go_to_page(1, true);
			}
		});

		frappe.ui.form.close_grid_form();
		this.viewers && this.viewers.parent.empty();
		this.docname = docname;
		this.setup_docinfo_change_listener();
	};

	Form.__logistics_switch_doc_patched = true;
})();
