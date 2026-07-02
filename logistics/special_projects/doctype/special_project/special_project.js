// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Global helper used by the "Submission Blocked" msgprint primary_action to
// jump to the relevant tab on the current Special Project form, then close
// the dialog. The Python side passes `{ fieldname: "fulfillment_tab" }`
// (or "services_tab") as args.
window.logistics = window.logistics || {};
window.logistics.special_project_modals = window.logistics.special_project_modals || {};
window.logistics.special_project_modals.go_to_tab = function (args) {
	const fieldname = (args && args.fieldname) || "fulfillment_tab";
	const frm = cur_frm;
	if (frm && frm.fields_dict && frm.fields_dict[fieldname] && frm.fields_dict[fieldname].tab) {
		try {
			frm.fields_dict[fieldname].tab.set_active();
			frm.scroll_to_field && frm.scroll_to_field(fieldname);
			if (window.logistics && logistics.trigger_lazy_tab_loaders) {
				logistics.trigger_lazy_tab_loaders(frm, fieldname);
			}
		} catch (e) {
			// silent fail – modal still closes below
		}
	}
	if (typeof frappe !== "undefined" && frappe.hide_msgprint) {
		frappe.hide_msgprint();
	}
};

window.logistics.special_project_modals.open_source_job = function (args) {
	const doctype = args && args.doctype;
	const docname = args && args.docname;
	if (typeof frappe !== "undefined" && frappe.hide_msgprint) {
		frappe.hide_msgprint();
	}
	if (doctype && docname && typeof frappe !== "undefined" && frappe.set_route) {
		frappe.set_route("Form", doctype, docname);
	}
};

function _load_milestone_html(frm, opts) {
	opts = opts || {};
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) {
		if (opts.done) opts.done();
		return;
	}
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: "Special Project", docname: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		},
	}).always(function () {
		if (opts.done) opts.done();
	});
}

function _applicable_lifecycle_stages_for_dashboard(frm) {
	return (frm.doc.applicable_lifecycle_stages || [])
		.map((row) => row.lifecycle_stage)
		.filter(Boolean);
}

function _load_dashboard_html(frm, opts) {
	opts = opts || {};
	if (!frm.fields_dict.dashboard_html || !frm.doc.name || frm.doc.__islocal) {
		if (opts.done) opts.done();
		return;
	}
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_dashboard_html",
		args: {
			special_project: frm.doc.name,
			applicable_stages: _applicable_lifecycle_stages_for_dashboard(frm),
		},
		callback: function (r) {
			if (r.message && frm.fields_dict.dashboard_html) {
				frm.fields_dict.dashboard_html.$wrapper.html(r.message);
				_bind_fulfillment_panels_in_wrapper(frm, frm.fields_dict.dashboard_html.$wrapper);
				if (window.logistics_group_and_collapse_dash_alerts) {
					setTimeout(function () {
						window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
					}, 100);
				}
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
				}
			}
		},
	}).always(function () {
		if (opts.done) opts.done();
	});
}

function _load_profitability_html(frm, opts) {
	opts = opts || {};
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.profitability_section_html) {
		if (opts.done) {
			opts.done();
		}
		return;
	}
	var loader =
		window.logistics &&
		logistics.profitability &&
		logistics.profitability.load_project_profitability_html;
	if (typeof loader === "function") {
		loader(frm, opts);
		return;
	}
	frappe.require("/assets/logistics/js/profitability_project_form.js", function () {
		var retry =
			window.logistics &&
			logistics.profitability &&
			logistics.profitability.load_project_profitability_html;
		if (typeof retry === "function") {
			retry(frm, opts);
		} else if (opts.done) {
			opts.done();
		}
	});
}

function _load_cost_revenue_summary(frm, opts) {
	opts = opts || {};
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.cost_revenue_html) {
		if (opts.done) opts.done();
		return;
	}
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_cost_revenue_summary",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.cost_revenue_html) {
				frm.fields_dict.cost_revenue_html.$wrapper.html(r.message);
			}
		},
	}).always(function () {
		if (opts.done) opts.done();
	});
}

function _load_packages_summary(frm, opts) {
	opts = opts || {};
	if (!frm.fields_dict.packages_summary || !frm.doc.name || frm.doc.__islocal) {
		if (opts.done) opts.done();
		return;
	}
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_packages_summary_html",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.packages_summary) {
				frm.fields_dict.packages_summary.$wrapper.html(r.message);
				_reveal_packages_summary_section(frm);
				_bind_fulfillment_panels_in_wrapper(frm, frm.fields_dict.packages_summary.$wrapper);
			}
		},
	}).always(function () {
		if (opts.done) opts.done();
	});
}

function _bind_special_project_lazy_tabs(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !window.logistics || !logistics.bind_lazy_tab_loader) {
		return;
	}
	if (frm.doc.modified !== frm._logistics_lazy_modified) {
		logistics.invalidate_lazy_tab_loaders(frm);
		frm._logistics_lazy_modified = frm.doc.modified;
	}
	logistics.bind_lazy_tab_loader(frm, "dashboard_tab", "dashboard", _load_dashboard_html);
	logistics.bind_lazy_tab_loader(frm, "services_tab", "cost_revenue", _load_cost_revenue_summary);
	logistics.bind_lazy_tab_loader(frm, "fulfillment_tab", "packages_summary", _load_packages_summary);
	logistics.bind_lazy_tab_loader(frm, "milestones_tab", "milestones", _load_milestone_html);
	if (window.logistics_load_documents_html) {
		logistics.bind_lazy_tab_loader(
			frm,
			"documents_tab",
			"documents",
			function (f, o) {
				window.logistics_load_documents_html(f, "Special Project", o);
			},
			{ defer_if_active: false }
		);
	}
	// Profitability HTML lives on the Charges tab (no dedicated profitability_tab).
	logistics.bind_lazy_tab_loader(
		frm,
		"charges_tab",
		"profitability",
		_load_profitability_html
	);
	if (logistics.is_form_tab_active(frm, "charges_tab")) {
		setTimeout(function () {
			logistics.trigger_lazy_tab_loaders(frm, "charges_tab");
		}, 150);
	}
}

function _applicableLifecycleStageFilters(frm) {
	const stages = (frm.doc.applicable_lifecycle_stages || [])
		.map((row) => row.lifecycle_stage)
		.filter(Boolean);
	// Must be a plain object — array filters break when merged with link_filters in link.js.
	if (!stages.length) {
		return { for_special_project: 1 };
	}
	return { name: ["in", stages] };
}

function _refresh_special_project_services_grid_rows(frm) {
	if (!frm || !frm.doc || frm.doc.docstatus !== 0) return;
	const field = frm.fields_dict.special_project_services;
	if (!field || !field.grid) return;
	const grid = field.grid;
	if (!grid.grid_rows || typeof grid.is_editable !== "function" || !grid.is_editable()) {
		return;
	}
	grid.grid_rows.forEach((row) => {
		if (row && typeof row.refresh === "function") {
			row.refresh();
		}
	});
}

/** Virtual ``special_project_services`` defaults to Read display_status; show Add row on draft projects. */
function _enable_special_project_services_grid_add_row(frm) {
	if (!frm || !frm.doc || frm.doc.docstatus !== 0) return;
	const field = frm.fields_dict.special_project_services;
	if (!field || !field.grid || !field.grid.wrapper) return;
	const grid = field.grid;
	grid.display_status = "Write";
	grid.wrapper.find(".grid-footer").removeClass("hidden");
	grid.wrapper
		.find(".grid-add-row, .grid-add-multiple-rows")
		.removeClass("hidden d-none");
	if (typeof grid.setup_toolbar === "function") {
		grid.setup_toolbar();
	}
	_refresh_special_project_services_grid_rows(frm);
}

function _activate_special_project_services_grid_row(frm, cdn, attempt) {
	if (!frm || !cdn) return;
	const grid = frm.fields_dict.special_project_services?.grid;
	if (!grid) return;
	const row = (grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn]) || null;
	if (!row) {
		if ((attempt || 0) < 10) {
			setTimeout(
				() => _activate_special_project_services_grid_row(frm, cdn, (attempt || 0) + 1),
				50
			);
		}
		return;
	}
	_enable_special_project_services_grid_add_row(frm);
	if (typeof grid.allow_on_grid_editing === "function" && grid.allow_on_grid_editing()) {
		row.toggle_editable_row(true);
		return;
	}
	row.toggle_view(true);
}

function _is_special_project_services_grid(grid) {
	if (!grid || !grid.df || !grid.frm) return false;
	return grid.frm.doctype === "Special Project" && grid.df.fieldname === "special_project_services";
}

function _patch_special_project_services_grid_activate(frm) {
	const field = frm.fields_dict.special_project_services;
	if (!field || !field.grid || typeof field.grid.add_new_row !== "function") return false;
	const grid = field.grid;
	if (grid._logistics_sp_svc_activate_patched) return true;

	const orig_add_new_row = grid.add_new_row.bind(grid);
	grid.add_new_row = function (idx, callback, show, copy_doc, go_to_last_page, go_to_first_page) {
		const row_doc = orig_add_new_row(
			idx,
			callback,
			show,
			copy_doc,
			go_to_last_page,
			go_to_first_page
		);
		if (row_doc && row_doc.name) {
			_activate_special_project_services_grid_row(frm, row_doc.name);
		}
		return row_doc;
	};
	grid._logistics_sp_svc_activate_patched = true;
	return true;
}

function _setup_special_project_services_grid(frm) {
	_setup_special_project_services_duplicate_fix(frm);
	if (!_patch_special_project_services_grid_activate(frm) && !frm._logistics_sp_svc_grid_patch_retry) {
		frm._logistics_sp_svc_grid_patch_retry = true;
		setTimeout(() => _setup_special_project_services_grid(frm), 300);
		return;
	}
	_enable_special_project_services_grid_add_row(frm);
}

(function patch_sp_services_grid_refresh() {
	function patch_grid_refresh(grid) {
		if (!_is_special_project_services_grid(grid) || grid._logistics_sp_svc_refresh_patched) {
			return;
		}
		grid._logistics_sp_svc_refresh_patched = true;
		const orig = grid.refresh.bind(grid);
		grid.refresh = function () {
			orig.apply(this, arguments);
			if (this.frm) {
				_enable_special_project_services_grid_add_row(this.frm);
			}
		};
	}

	function run() {
		if (!frappe.ui.form || !frappe.ui.form.ControlTable) {
			setTimeout(run, 50);
			return;
		}
		if (frappe.ui.form.ControlTable.prototype.make.__logistics_sp_svc_hooked) {
			return;
		}
		const orig_make = frappe.ui.form.ControlTable.prototype.make;
		frappe.ui.form.ControlTable.prototype.make = function () {
			orig_make.apply(this, arguments);
			if (this.grid) {
				patch_grid_refresh(this.grid);
			}
		};
		frappe.ui.form.ControlTable.prototype.make.__logistics_sp_svc_hooked = true;
	}
	run();
})();

function _setup_special_project_services_duplicate_fix(frm) {
	if (window.logistics && logistics.lifecycle && logistics.lifecycle.setup_special_project_services_grid) {
		logistics.lifecycle.setup_special_project_services_grid(frm);
		return;
	}
	const field = frm.fields_dict.special_project_services;
	if (
		!field ||
		!field.grid ||
		typeof field.grid.add_new_row !== "function" ||
		typeof field.grid.duplicate_row !== "function" ||
		field.grid._logistics_lifecycle_duplicate_patched
	) {
		return;
	}
	const grid = field.grid;
	const orig_add_new_row = grid.add_new_row.bind(grid);
	grid.add_new_row = function (idx, callback, show, copy_doc, go_to_last_page, go_to_first_page) {
		if (copy_doc) {
			copy_doc = Object.assign({}, copy_doc);
			copy_doc.job_type = null;
			copy_doc.order_no = null;
			copy_doc.job_no = null;
			copy_doc.special_project_service_line = null;
		}
		return orig_add_new_row(idx, callback, show, copy_doc, go_to_last_page, go_to_first_page);
	};
	const orig_duplicate_row = grid.duplicate_row.bind(grid);
	grid.duplicate_row = function (d, copy_doc) {
		if (copy_doc) {
			copy_doc = Object.assign({}, copy_doc);
			copy_doc.job_type = null;
			copy_doc.order_no = null;
			copy_doc.job_no = null;
			copy_doc.special_project_service_line = null;
		}
		orig_duplicate_row(d, copy_doc);
		d.job_type = null;
		d.order_no = null;
		d.job_no = null;
		d.special_project_service_line = null;
		return d;
	};
	grid._logistics_lifecycle_duplicate_patched = true;
}

function logistics_clear_stale_package_grid_settings(frm) {
	const grid_view = frappe.get_user_settings(frm.doctype, "GridView") || {};
	let changed = false;
	[
		"Special Project Package",
		"Special Project Site Material",
		"Special Project Site Receipt",
	].forEach((child_dt) => {
		const cols = grid_view[child_dt];
		if (!Array.isArray(cols)) {
			return;
		}
		const filtered = cols.filter((col) => col && col.fieldname !== "item");
		if (filtered.length !== cols.length) {
			grid_view[child_dt] = filtered;
			changed = true;
		}
	});
	if (changed) {
		frappe.model.user_settings.save(frm.doctype, "GridView", grid_view);
	}
}

function logistics_set_packages_site_query(frm) {
	frm.set_query("site", "packages", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
	frm.set_query("warehouse_item", "packages", function (doc) {
		const filters = {};
		if (doc.customer) {
			filters.customer = doc.customer;
		}
		return { filters: filters };
	});
	frm.set_query("commodity", "packages", function () {
		return { filters: { active: 1 } };
	});
}

const SP_PACKAGES_SUMMARY_COLLAPSED_KEY = "sp_packages_summary_collapsed";
const SP_PACKAGE_EXECUTION_BALANCE_FIELDS = ["qty_on_site", "qty_short"];

function _setup_packages_execution_only_balances(frm) {
	const grid = frm.fields_dict.packages && frm.fields_dict.packages.grid;
	if (!grid || typeof grid.update_docfield_property !== "function") {
		return;
	}
	SP_PACKAGE_EXECUTION_BALANCE_FIELDS.forEach(function (fieldname) {
		grid.update_docfield_property(fieldname, "read_only", 1);
	});
}

function _refresh_packages_delivered_grid(frm) {
	const grid = frm.fields_dict.packages && frm.fields_dict.packages.grid;
	if (grid) {
		grid.refresh();
	}
	_refresh_packages_summary(frm);
}

function _bind_special_project_packages_realtime_refresh(frm) {
	if (frm.is_new() || frm.doc.__islocal || !frm.doc.name) {
		return;
	}
	if (frm._sp_packages_balance_rt) {
		return;
	}
	frm._sp_packages_balance_rt = true;
	frappe.realtime.on("doc_update", function (data) {
		if (
			!data ||
			data.doctype !== "Special Project" ||
			data.name !== frm.doc.name ||
			frm.is_dirty()
		) {
			return;
		}
		frm.reload_doc();
	});
}

function _reveal_packages_summary_section(frm) {
	const field = frm.fields_dict.packages_summary;
	if (!field || !field.$wrapper) {
		return;
	}
	field.$wrapper.removeClass("hide-control");
	const $section = field.$wrapper.closest(".form-section");
	$section.removeClass("empty-section").addClass("visible-section");
	$section.find(".section-head").hide();
	if (frm.layout && frm.layout.refresh_sections) {
		frm.layout.refresh_sections();
	}
}

function _bind_fulfillment_panels_in_wrapper(frm, $wrapper) {
	if (!$wrapper || !$wrapper.length) {
		return;
	}
	$wrapper.find("[data-sp-fulfillment-panel]").each(function () {
		const $panel = $(this);
		const $scope = $panel.parent();
		_bind_packages_summary_layout($scope);
		_bind_packages_summary_collapse($scope);
		_bind_packages_summary_filters($scope);
	});
	$wrapper.find("[data-sp-fulfillment-dash]").each(function () {
		_bind_special_project_main_dash_lifecycle($(this));
	});
}

function _bind_special_project_main_dash_lifecycle($root) {
	if (!$root || !$root.length || $root.attr("data-sp-fulfillment-dash-bound")) {
		return;
	}
	$root.attr("data-sp-fulfillment-dash-bound", "1");

	const currentStage = ($root.attr("data-sp-current-stage") || "").trim();

	function setStageHighlight(stage) {
		const normalized = (stage || "").trim();
		$root.attr("data-stage-filter", normalized);
		$root.find(".sp-dash-lifecycle-group").each(function () {
			const gs = ($(this).attr("data-stage") || "").trim();
			$(this).toggleClass("is-stage-filter", normalized && gs === normalized);
		});
		$root.find(".sp-dash-card").each(function () {
			const cs = ($(this).attr("data-sp-lifecycle-stage") || "").trim();
			$(this).toggleClass("is-selected", normalized && cs === normalized);
		});
	}

	function syncGroupCollapsedState($group) {
		const collapsed = $group.hasClass("collapsed");
		const $body = $group.find(".sp-dash-lifecycle-group-body");
		const $chevron = $group.find(".sp-dash-lifecycle-chevron");
		$body.css("display", collapsed ? "none" : "");
		$chevron.toggleClass("fa-chevron-right", collapsed);
		$chevron.toggleClass("fa-chevron-down", !collapsed);
	}

	function toggleGroup($group) {
		$group.toggleClass("collapsed");
		syncGroupCollapsedState($group);
	}

	$root.find(".sp-dash-lifecycle-group").each(function () {
		syncGroupCollapsedState($(this));
	});

	$root.find(".sp-dash-lifecycle-group-header").each(function () {
		const $header = $(this);
		if ($header.attr("data-sp-lifecycle-bound")) return;
		$header.attr("data-sp-lifecycle-bound", "1");
		const $chevron = $header.find(".sp-dash-lifecycle-chevron");
		if ($chevron.length && !$chevron.attr("data-sp-lifecycle-bound")) {
			$chevron.attr("data-sp-lifecycle-bound", "1");
			$chevron.on("click.sp-lifecycle-dash", function (ev) {
				ev.stopPropagation();
				const $group = $header.closest(".sp-dash-lifecycle-group");
				if ($group.length) toggleGroup($group);
			});
		}
		$header.on("click.sp-lifecycle-dash", function (ev) {
			if ($(ev.target).closest(".sp-dash-lifecycle-chevron").length) return;
			const $group = $header.closest(".sp-dash-lifecycle-group");
			if (!$group.length) return;
			const stage = ($group.attr("data-stage") || "").trim();
			const current = ($root.attr("data-stage-filter") || "").trim();
			if (stage) setStageHighlight(stage === current ? "" : stage);
			if ($group.hasClass("collapsed")) {
				$group.removeClass("collapsed");
				syncGroupCollapsedState($group);
			}
		});
	});

	$root.find(".sp-dash-card").each(function () {
		const $card = $(this);
		if ($card.attr("data-sp-lifecycle-bound")) return;
		$card.attr("data-sp-lifecycle-bound", "1");
		$card.on("click.sp-lifecycle-dash", function (ev) {
			ev.stopPropagation();
			const stage = ($card.attr("data-sp-lifecycle-stage") || "").trim();
			if (stage) setStageHighlight(stage);
		});
	});

	if (currentStage) {
		setStageHighlight(currentStage);
	}
}

function _sync_packages_summary_full_width($root) {
	if (!$root || !$root.length) {
		return;
	}
	let full_width = false;
	try {
		full_width =
			document.body.classList.contains("full-width") ||
			JSON.parse(localStorage.container_fullwidth || "false");
	} catch (e) {
		full_width = document.body.classList.contains("full-width");
	}
	$root.toggleClass("is-page-full-width", !!full_width);
}

function _bind_packages_summary_layout($scope) {
	if (!$scope || !$scope.length) {
		return;
	}
	$scope.addClass("sp-packages-summary-field");
	const $root = $scope.find(".sp-packages-summary").first();
	if (!$root.length && $scope.hasClass("sp-packages-summary")) {
		$scope.addClass("sp-packages-summary-field");
	}
	const $summary = $root.length ? $root : $scope.filter(".sp-packages-summary");
	_sync_packages_summary_full_width($summary);

	if (!window._logistics_sp_pks_fullwidth_bound) {
		window._logistics_sp_pks_fullwidth_bound = true;
		$(document.body).on("toggleFullWidth.sp-pks", function () {
			$(".sp-packages-summary").each(function () {
				_sync_packages_summary_full_width($(this));
			});
		});
	}
}

function _bind_packages_summary_collapse($scope) {
	if (!$scope || !$scope.length) {
		return;
	}
	const $root = $scope.find(".sp-packages-summary").first();
	if (!$root.length) {
		return;
	}
	const $toggle = $root.find(".sp-pks-toggle");
	if (!$toggle.length) {
		return;
	}

	function set_collapsed(collapsed) {
		$root.toggleClass("is-collapsed", collapsed);
		$toggle.attr("aria-expanded", collapsed ? "false" : "true");
		$toggle.attr(
			"title",
			collapsed ? __("Expand summary") : __("Collapse summary")
		);
		try {
			localStorage.setItem(SP_PACKAGES_SUMMARY_COLLAPSED_KEY, collapsed ? "1" : "0");
		} catch (e) {
			/* ignore quota / private mode */
		}
	}

	let collapsed = false;
	try {
		collapsed = localStorage.getItem(SP_PACKAGES_SUMMARY_COLLAPSED_KEY) === "1";
	} catch (e) {
		collapsed = false;
	}
	set_collapsed(collapsed);

	$toggle.off("click.sp-pks").on("click.sp-pks", function () {
		set_collapsed(!$root.hasClass("is-collapsed"));
	});
}

function _bind_packages_summary_filters($scope) {
	if (!$scope || !$scope.length) {
		return;
	}
	const $root = $scope.find(".sp-packages-summary").first();
	const $filters = $root.find(".sp-pfn-filters");
	if (!$root.length || !$filters.length) {
		return;
	}

	function apply_filter(filter) {
		const $rows = $root.find(".sp-pfn-summary-row");
		if (filter === "all") {
			$rows.show();
			return;
		}
		$rows.each(function () {
			const status = ($(this).attr("data-status") || "").trim();
			const show =
				filter === "in_progress"
					? status === "in_progress" || status === "stalled"
					: status === filter;
			$(this).toggle(show);
		});
	}

	$filters.find(".sp-pfn-filter-chip").off("click.sp-pfn-filter").on("click.sp-pfn-filter", function () {
		const filter = $(this).attr("data-filter") || "all";
		$filters.find(".sp-pfn-filter-chip").removeClass("is-active");
		$(this).addClass("is-active");
		apply_filter(filter);
	});
}

function _sync_programme_charge_sales_quote_links(frm) {
	if (!frm.doc.name || frm.doc.__islocal || frm.is_dirty()) {
		return;
	}
	var needs_sync = (frm.doc.charges || []).some(function (row) {
		return row.change_request && !row.sales_quote_link;
	});
	if (!needs_sync) {
		return;
	}
	if (frm._sp_sq_link_sync_pending) {
		return;
	}
	frm._sp_sq_link_sync_pending = true;
	frappe.call({
		method:
			"logistics.special_projects.doctype.special_project.special_project.sync_programme_charge_sales_quote_links",
		args: { docname: frm.doc.name },
		callback: function (r) {
			if (r.message && r.message.updated) {
				frm.reload_doc();
			}
		},
	}).always(function () {
		frm._sp_sq_link_sync_pending = false;
	});
}

function _refresh_packages_summary(frm) {
	if (!frm.doc.name || frm.doc.__islocal) {
		return;
	}
	if (frm.fields_dict.packages_summary) {
		if (window.logistics && logistics.invalidate_lazy_tab_loaders) {
			logistics.invalidate_lazy_tab_loaders(frm, ["packages_summary"]);
		}
		_load_packages_summary(frm, { force: true });
	}
	_refresh_dashboard_html(frm);
}

function _serviceRowLabel(frm, value) {
	if (!value) {
		return "";
	}
	const match = (frm.doc.special_project_services || []).find((row) => row.name === value);
	if (match) {
		return (
			match.lifecycle_row_label ||
			match.activity_name ||
			match.lifecycle_stage ||
			match.activity_code ||
			value
		);
	}
	return value;
}

function _setup_special_project_services_lifecycle_formatters(frm) {
	const grid = frm.fields_dict.special_project_services && frm.fields_dict.special_project_services.grid;
	if (!grid || grid._logistics_ps_lifecycle_label_patched) {
		return;
	}
	grid._logistics_ps_lifecycle_label_patched = true;
	grid.formatters = grid.formatters || {};
	grid.formatters.lifecycle_stage = function (value) {
		if (!value) {
			return "";
		}
		return frappe.utils.escape_html(value);
	};
}

function logistics_set_internal_job_site_query(frm) {
	frm.set_query("lifecycle_stage", function () {
		return { filters: _applicableLifecycleStageFilters(frm) };
	});
	frm.set_query("sp_site", "special_project_services", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
	frm.set_query("lifecycle_stage", "special_project_services", function () {
		return { filters: _applicableLifecycleStageFilters(frm) };
	});
	frm.set_query("lifecycle_stage", "charges", function () {
		return { filters: _applicableLifecycleStageFilters(frm) };
	});
	frm.set_query("special_project_service_line", "charges", function (doc, cdt, cdn) {
		var row = cdn && locals[cdt] && locals[cdt][cdn];
		var filters = [
			["Special Project Service", "parent_booking_type", "=", "Special Project"],
			["Special Project Service", "parent_booking_name", "=", frm.doc.name || ""],
		];
		if (row && row.lifecycle_stage) {
			filters.push(["Special Project Service", "lifecycle_stage", "=", row.lifecycle_stage]);
		}
		return { filters: filters };
	});
}

frappe.ui.form.on("Special Project", {
	on_tab_change(frm) {
		const tab = frm.get_active_tab && frm.get_active_tab();
		const fieldname = tab && tab.df && tab.df.fieldname;
		if (fieldname && window.logistics && logistics.trigger_lazy_tab_loaders) {
			logistics.trigger_lazy_tab_loaders(frm, fieldname);
		}
	},
	onload: function (frm) {
		if (frm.get_docfield && frm.get_docfield("charges")) {
			frm.set_df_property("charges", "cannot_add_rows", 1);
			frm.set_df_property("charges", "allow_bulk_edit", 0);
		}
		if (frm.get_docfield && frm.get_docfield("charge_execution_logs")) {
			frm.set_df_property("charge_execution_logs", "cannot_add_rows", 1);
			frm.set_df_property("charge_execution_logs", "cannot_delete_rows", 1);
		}
		if (frm.get_docfield && frm.get_docfield("deliveries")) {
			frm.set_df_property("deliveries", "cannot_add_rows", 1);
			frm.set_df_property("deliveries", "cannot_delete_rows", 1);
		}
		_setup_special_project_services_grid(frm);
	},
	setup: function (frm) {
		if (window.logistics && logistics.lifecycle && logistics.lifecycle.setup_queries) {
			logistics.lifecycle.setup_queries(frm);
		}
		logistics_set_internal_job_site_query(frm);
		frm.set_query("milestone_template", function () {
			return frappe.call("logistics.document_management.api.get_milestone_template_filters", { doctype: frm.doctype }).then(function (r) {
				return r.message || { filters: [] };
			});
		});
		frm.set_query("sales_quote_link", "charges", function (doc, cdt, cdn) {
			var row = cdn && locals[cdt] && locals[cdt][cdn];
			if (row && row.change_request) {
				return {
					filters: [["Sales Quote", "change_request", "=", row.change_request]],
				};
			}
			return {
				query: "logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search",
				filters: {
					service_type: (row && row.service_type) || "Special Project",
					reference_doctype: "Special Project",
					reference_name: doc.name || "",
				},
			};
		});
	},
	milestone_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_milestones_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				},
			});
		});
	},
	document_list_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_documents_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				},
			});
		});
	},
	refresh: function (frm) {
		if (frm.get_docfield && frm.get_docfield("deliveries")) {
			frm.set_df_property("deliveries", "cannot_add_rows", 1);
			frm.set_df_property("deliveries", "cannot_delete_rows", 1);
		}
		if (frm.get_docfield && frm.get_docfield("charge_execution_logs")) {
			frm.set_df_property("charge_execution_logs", "cannot_add_rows", 1);
			frm.set_df_property("charge_execution_logs", "cannot_delete_rows", 1);
		}
		logistics_set_internal_job_site_query(frm);
		_setup_special_project_services_grid(frm);
		_setup_special_project_services_lifecycle_formatters(frm);
		if (!frm.fields_dict.special_project_services?.grid?._logistics_ps_lifecycle_label_patched) {
			setTimeout(() => _setup_special_project_services_lifecycle_formatters(frm), 300);
		}
		logistics_clear_stale_package_grid_settings(frm);
		logistics_set_packages_site_query(frm);
		_setup_packages_execution_only_balances(frm);
		_bind_special_project_packages_realtime_refresh(frm);
		if (!frm.fields_dict.special_project_services?.grid?._logistics_sp_svc_activate_patched) {
			setTimeout(() => _setup_special_project_services_grid(frm), 300);
		}
		_bind_special_project_lazy_tabs(frm);
		_refresh_packages_summary(frm);
		_sync_programme_charge_sales_quote_links(frm);

		// --- Action menu: Get Milestones, Get Documents, Calculate Charges, Apply Lifecycle Template ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Get Milestones"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_milestones_from_template",
					args: { doctype: "Special Project", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Action"));

			if (frm.fields_dict.documents) {
				frm.add_custom_button(__("Get Documents"), function () {
					frappe.call({
						method: "logistics.document_management.api.populate_documents_from_template",
						args: { doctype: "Special Project", docname: frm.doc.name },
						callback: function (r) {
							if (r.message && r.message.added !== undefined) {
								frappe.show_alert({
									message: __("Added {0} document(s) from template.", [r.message.added]),
									indicator: "green",
								});
								frm.reload_doc();
							} else if (r.message && r.message.message) {
								frappe.msgprint(r.message.message);
							}
						},
					});
				}, __("Action"));
			}

			if (frm.doc.charges && frm.doc.charges.length > 0) {
				frm.add_custom_button(__("Calculate Charges"), function () {
					frappe.call({
						method: "logistics.special_projects.doctype.special_project.special_project.recalculate_all_charges",
						args: { docname: frm.doc.name },
						callback: function (r) {
							if (r.message && r.message.success) {
								frm.reload_doc();
								frappe.show_alert({ message: __(r.message.message), indicator: "green" }, 3);
							}
						},
					});
				}, __("Action"));
			}

			frm.add_custom_button(__("Apply Lifecycle Template"), function () {
				if (window.logistics_open_apply_lifecycle_template_dialog) {
					window.logistics_open_apply_lifecycle_template_dialog(frm, "Special Project");
				} else {
					frappe.require(
						"/assets/logistics/js/apply_lifecycle_template_dialog.js",
						function () {
							window.logistics_open_apply_lifecycle_template_dialog(frm, "Special Project");
						}
					);
				}
			}, __("Action"));
		}

		// --- Create menu: Sales Invoice, Purchase Invoice, Booking/Order, Change Request ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Sales Invoice"), function () {
				if (typeof window.show_create_sales_invoice_dialog === "function") {
					window.show_create_sales_invoice_dialog(frm);
				} else {
					frappe.msgprint({
						title: __("Not available"),
						message: __("The Sales Invoice dialog could not load. Refresh the page or contact your administrator."),
						indicator: "red",
					});
				}
			}, __("Create"));

			frm.add_custom_button(__("Purchase Invoice"), function () {
				if (typeof window.show_create_purchase_invoice_dialog === "function") {
					window.show_create_purchase_invoice_dialog(frm);
				} else {
					frappe.msgprint({
						title: __("Not available"),
						message: __("The Purchase Invoice dialog could not load. Refresh the page or contact your administrator."),
						indicator: "red",
					});
				}
			}, __("Create"));

			frm.add_custom_button(__("Booking / Order"), function () {
				function _openDlg() {
					if (window.logistics_show_special_project_booking_dialog) {
						window.logistics_show_special_project_booking_dialog(frm);
					} else {
						frappe.msgprint({
							title: __("Not available"),
							message: __("The Booking / Order dialog could not load. Refresh the page or contact your administrator."),
							indicator: "red",
						});
					}
				}
				function _launchBookingDialog() {
					if (window.logistics_show_special_project_booking_dialog) {
						_openDlg();
					} else {
						frappe.require(
							"/assets/logistics/js/special_project_booking_dialog.js",
							_openDlg
						);
					}
				}
				if (frm.is_dirty()) {
					frm.save().then(_launchBookingDialog);
				} else {
					_launchBookingDialog();
				}
			}, __("Create"));

			frm.add_custom_button(__("Change Request"), function () {
				frappe.call({
					method: "logistics.pricing_center.doctype.change_request.change_request.create_change_request",
					args: { job_type: "Special Project", job_name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.set_route("Form", "Change Request", r.message);
						}
					},
				});
			}, __("Create"));

			frm.add_custom_button(__("Refresh Delivery Funnel"), function () {
				frappe.call({
					method: "logistics.special_projects.special_project_packages.recalculate_package_delivery_balances",
					args: { special_project: frm.doc.name },
					callback: function () {
						frm.reload_doc();
					},
				});
			}, __("Packages"));

			_special_project_add_recognition_buttons(frm);
		}
	},
	packages_add: function (frm) {
		_refresh_packages_summary(frm);
	},
	packages_remove: function (frm) {
		_refresh_packages_summary(frm);
	},
	deliveries_add: function (frm) {
		_refresh_packages_delivered_grid(frm);
	},
	deliveries_remove: function (frm) {
		_refresh_packages_delivered_grid(frm);
	},
	milestones_add: function (frm) {
		_refresh_milestone_html(frm);
	},
	milestones_remove: function (frm) {
		_refresh_milestone_html(frm);
	},
	lifecycle_stage(frm) {
		_refresh_dashboard_html(frm);
	},

	special_project_services_add: function (frm, cdt, cdn) {
		if (logistics.lifecycle && logistics.lifecycle.clear_special_project_service_link_on_row_add) {
			logistics.lifecycle.clear_special_project_service_link_on_row_add(frm, cdt, cdn);
		} else if (
			(cdt === "Special Project Service Detail" || cdt === "Special Project Service") &&
			cdn &&
			locals[cdt] &&
			locals[cdt][cdn]
		) {
			const row = locals[cdt][cdn];
			row.special_project_service = null;
			row.job_type = null;
			row.order_no = null;
			row.job_no = null;
			row.special_project_service_line = null;
			const grid_row = frm.fields_dict.special_project_services?.grid?.grid_rows_by_docname?.[cdn];
			if (grid_row) {
				grid_row.refresh_field("job_type");
				grid_row.refresh_field("order_no");
				grid_row.refresh_field("job_no");
				grid_row.refresh_field("special_project_service_line");
			}
		}
		_activate_special_project_services_grid_row(frm, cdn);
		_refresh_cost_revenue_summary(frm);
		_refresh_dashboard_html(frm);
	},
	special_project_services_remove: function (frm) {
		_refresh_cost_revenue_summary(frm);
		_refresh_dashboard_html(frm);
	},
	applicable_lifecycle_stages_add: function (frm) {
		// Re-apply stage filters when applicable stages change.
		logistics_set_internal_job_site_query(frm);
		_refresh_dashboard_html(frm);
		if (frm.fields_dict.lifecycle_stage) {
			frm.refresh_field("lifecycle_stage");
		}
	},
	applicable_lifecycle_stages_remove: function (frm) {
		logistics_set_internal_job_site_query(frm);
		_refresh_dashboard_html(frm);
		if (frm.fields_dict.lifecycle_stage) {
			frm.refresh_field("lifecycle_stage");
		}
	},
});

frappe.ui.form.on("Special Project Scoping Activity", {
	currency(frm, cdt, cdn) {
		const grid_row = frm.fields_dict.scoping_activities?.grid?.grid_rows_by_docname?.[cdn];
		if (grid_row) {
			grid_row.refresh_field("cost");
		}
	},
});

frappe.ui.form.on("Special Project Charges", {
	service_type: function (frm) {
		if (frm.doc.__islocal) return;
		_refresh_cost_revenue_summary(frm);
	},
	estimated_cost: function (frm) {
		if (frm.doc.__islocal) return;
		_refresh_cost_revenue_summary(frm);
	},
	estimated_revenue: function (frm) {
		if (frm.doc.__islocal) return;
		_refresh_cost_revenue_summary(frm);
	},
});

function _refresh_cost_revenue_summary(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.cost_revenue_html) {
		return;
	}
	if (window.logistics && logistics.invalidate_lazy_tab_loaders) {
		logistics.invalidate_lazy_tab_loaders(frm, ["cost_revenue"]);
	}
	_load_cost_revenue_summary(frm, { force: true });
}

function _refresh_dashboard_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.dashboard_html) {
		return;
	}
	if (window.logistics && logistics.invalidate_lazy_tab_loaders) {
		logistics.invalidate_lazy_tab_loaders(frm, ["dashboard"]);
	}
	_load_dashboard_html(frm, { force: true });
}

function _refresh_profitability_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.profitability_section_html) {
		return;
	}
	if (window.logistics && logistics.invalidate_lazy_tab_loaders) {
		logistics.invalidate_lazy_tab_loaders(frm, ["profitability"]);
	}
	_load_profitability_html(frm, { force: true });
}

function _refresh_milestone_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.milestone_html) {
		return;
	}
	if (window.logistics && logistics.invalidate_lazy_tab_loaders) {
		logistics.invalidate_lazy_tab_loaders(frm, ["milestones"]);
	}
	_load_milestone_html(frm, { force: true });
}

function _special_project_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === "function") fn(frm, cdt, cdn, grid_row, "packages");
}

/**
 * Add WIP & Accrual recognition buttons to Special Project
 * (Post: WIP and Accrual; Recognition: Adjust WIP / Adjust Accruals / Close).
 * Inline here so buttons show even when recognition_client.js is not loaded.
 */
function _special_project_add_recognition_buttons(frm) {
	var d = frm.doc;
	var needs_wip =
		typeof logistics !== "undefined" &&
		logistics.recognition &&
		logistics.recognition.needs_wip_recognition
			? logistics.recognition.needs_wip_recognition(d)
			: (function () {
					var rows = d.charges || [];
					for (var iw = 0; iw < rows.length; iw++) {
						var rw = rows[iw];
						if ((rw.charge_type || "").toLowerCase() === "disbursement") continue;
						var erw =
							flt(rw.estimated_revenue) ||
							flt(rw.base_amount) ||
							flt(rw.actual_revenue) ||
							flt(rw.amount) ||
							flt(rw.total) ||
							0;
						if (erw > 0 && !rw.wip_recognition_journal_entry) return true;
					}
					return flt(d.estimated_revenue) > flt(d.wip_amount);
			  })();
	var needs_accrual =
		typeof logistics !== "undefined" &&
		logistics.recognition &&
		logistics.recognition.needs_accrual_recognition
			? logistics.recognition.needs_accrual_recognition(d)
			: (function () {
					var rowsa = d.charges || [];
					for (var ia = 0; ia < rowsa.length; ia++) {
						var ra = rowsa[ia];
						if ((ra.charge_type || "").toLowerCase() === "disbursement") continue;
						var ca =
							flt(ra.estimated_cost) ||
							flt(ra.cost_base_amount) ||
							flt(ra.actual_cost) ||
							flt(ra.cost) ||
							0;
						if (ca > 0 && !ra.accrual_recognition_journal_entry) return true;
					}
					return flt(d.estimated_costs) > flt(d.accrual_amount);
			  })();

	if (needs_wip || needs_accrual) {
		frm.add_custom_button(
			__("WIP and Accrual"),
			function () {
				frappe.call({
					method: "logistics.job_management.recognition_engine.recognize",
					args: { doctype: d.doctype, docname: d.name },
					freeze: true,
					freeze_message: __("Recognizing WIP and Accruals..."),
					callback: function (r) {
						if (r.message) {
							var msg = [];
							if (r.message.wip_journal_entry)
								msg.push(__("WIP: {0}", [r.message.wip_journal_entry]));
							if (r.message.accrual_journal_entry)
								msg.push(__("Accruals: {0}", [r.message.accrual_journal_entry]));
							if (msg.length) {
								frappe.show_alert({ message: msg.join(" | "), indicator: "green" });
							} else {
								var reason =
									r.message.message ||
									__("Nothing to recognize (already recognized or below minimum)");
								frappe.msgprint({
									title: __("Recognition"),
									message: reason,
									indicator: "blue",
								});
							}
							frm.reload_doc();
						}
					},
				});
			},
			__("Post")
		);
	}

	if (flt(d.wip_amount) > 0) {
		frm.add_custom_button(
			__("Adjust WIP"),
			function () {
				frappe.prompt(
					[
						{
							fieldname: "adjustment_amount",
							fieldtype: "Currency",
							label: __("Adjustment Amount"),
							description: __("Current WIP: {0}", [d.wip_amount]),
							reqd: 1,
						},
						{
							fieldname: "adjustment_date",
							fieldtype: "Date",
							label: __("Adjustment Date"),
							default: frappe.datetime.get_today(),
							reqd: 1,
						},
					],
					function (values) {
						frappe.call({
							method: "logistics.job_management.recognition_engine.adjust_wip",
							args: {
								doctype: d.doctype,
								docname: d.name,
								adjustment_amount: values.adjustment_amount,
								adjustment_date: values.adjustment_date,
							},
							freeze: true,
							freeze_message: __("Creating WIP Adjustment..."),
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({
										message: __("WIP Adjustment created: {0}", [r.message]),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					},
					__("Adjust WIP"),
					__("Create")
				);
			},
			__("Recognition")
		);
	}

	if (flt(d.accrual_amount) > 0) {
		frm.add_custom_button(
			__("Adjust Accruals"),
			function () {
				frappe.prompt(
					[
						{
							fieldname: "adjustment_amount",
							fieldtype: "Currency",
							label: __("Adjustment Amount"),
							description: __("Current Accrual: {0}", [d.accrual_amount]),
							reqd: 1,
						},
						{
							fieldname: "adjustment_date",
							fieldtype: "Date",
							label: __("Adjustment Date"),
							default: frappe.datetime.get_today(),
							reqd: 1,
						},
					],
					function (values) {
						frappe.call({
							method: "logistics.job_management.recognition_engine.adjust_accruals",
							args: {
								doctype: d.doctype,
								docname: d.name,
								adjustment_amount: values.adjustment_amount,
								adjustment_date: values.adjustment_date,
							},
							freeze: true,
							freeze_message: __("Creating Accrual Adjustment..."),
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Accrual Adjustment created: {0}", [r.message]),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					},
					__("Adjust Accruals"),
					__("Create")
				);
			},
			__("Recognition")
		);
	}

	if (flt(d.wip_amount) > 0 || flt(d.accrual_amount) > 0) {
		frm.add_custom_button(
			__("Close Recognition"),
			function () {
				frappe.confirm(
					__("This will close all remaining WIP and Accruals. Continue?"),
					function () {
						frappe.prompt(
							[
								{
									fieldname: "closure_date",
									fieldtype: "Date",
									label: __("Closure Date"),
									default: frappe.datetime.get_today(),
									reqd: 1,
								},
							],
							function (values) {
								frappe.call({
									method: "logistics.job_management.recognition_engine.close_job_recognition",
									args: {
										doctype: d.doctype,
										docname: d.name,
										closure_date: values.closure_date,
									},
									freeze: true,
									freeze_message: __("Closing Recognition..."),
									callback: function (r) {
										if (r.message) {
											var msg = [];
											if (r.message.wip_journal_entry)
												msg.push(__("WIP closed: {0}", [r.message.wip_journal_entry]));
											if (r.message.accrual_journal_entry)
												msg.push(__("Accrual closed: {0}", [r.message.accrual_journal_entry]));
											if (msg.length)
												frappe.show_alert({
													message: msg.join(" | "),
													indicator: "green",
												});
											frm.reload_doc();
										}
									},
								});
							},
							__("Close Recognition"),
							__("Close")
						);
					}
				);
			},
			__("Recognition")
		);
	}
}

frappe.ui.form.on("Special Project", {
	packages_on_form_rendered: function (frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(
				frm,
				"Special Project Package",
				"packages",
				"special_project_volume"
			);
		}
	},
});

frappe.ui.form.on("Special Project Package", {
	form_render: function (frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger("packages_on_form_rendered");
		setTimeout(function () {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === "function") fn_immediate(frm, cdt, cdn);
			else if (typeof fn_debounced === "function") fn_debounced(frm, cdt, cdn);
			else _special_project_volume_fallback(
				frm,
				cdt,
				cdn,
				frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form()
			);
		}, 50);
	},
});
