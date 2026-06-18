// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Restore the main desk workspace sidebar after a hard reload or deep link.
 *
 * Frappe hides the main sidebar for some pages (e.g. Desktop with hide_sidebar) and shows
 * it again from Sidebar.toggle() when the next view allows it. Toggle returns without doing
 * anything when frappe.container.page.page is not set yet (race on the first page-change
 * before Form.setup attaches the frappe.ui.Page). In that case the sidebar can stay hidden
 * or empty (only standard items / Getting Started).
 *
 * DocTypes linked from several workspaces (e.g. Sales Quote) can also leave the sidebar
 * unset when set_workspace_sidebar finds multiple matches but cannot resolve module.
 */
(function () {
	"use strict";
	if (window.__logistics_main_sidebar_visibility__) {
		return;
	}
	window.__logistics_main_sidebar_visibility__ = true;

	var STORAGE_KEY = "logistics_workspace_sidebar";
	var MAX_RETRIES = 24;
	var RETRY_MS = 50;

	var MAIN_SERVICE_WORKSPACE = {
		Air: "Air Freight",
		Sea: "Sea Freight",
		Transport: "Transport",
		Warehousing: "Warehousing",
		Custom: "Customs",
		Customs: "Customs",
		"Special Project": "Special Projects",
		Exhibits: "MICE",
	};

	/** Sales Quote doctype module → default workspace sidebar when list/form has no doc context. */
	var MODULE_DEFAULT_WORKSPACE_SIDEBAR = {
		"Pricing Center": "Pricing",
	};

	function route_view() {
		var route = frappe.get_route && frappe.get_route();
		return route && route[0] ? String(route[0]).toLowerCase() : "";
	}

	function is_sales_quote_route() {
		return route_link_to() === "Sales Quote";
	}

	function get_sidebar() {
		return frappe.app && frappe.app.sidebar;
	}

	function page_allows_main_sidebar() {
		var desk_page = frappe.container && frappe.container.page && frappe.container.page.page;
		return !(desk_page && desk_page.hide_sidebar);
	}

	function form_page_ready() {
		return !!(frappe.container && frappe.container.page && frappe.container.page.page);
	}

	function route_link_to() {
		var route = frappe.get_route && frappe.get_route();
		if (!route || !route.length) {
			return null;
		}
		if (route[0] === "Form" && route[1]) {
			return route[1];
		}
		if (route.length === 2) {
			return route[1];
		}
		return route[0];
	}

	function remember_workspace_sidebar(title) {
		if (!title) {
			return;
		}
		try {
			sessionStorage.setItem(STORAGE_KEY, title);
		} catch (e) {
			/* ignore quota / private mode */
		}
	}

	function recalled_workspace_sidebar(sidebars) {
		try {
			var stored = sessionStorage.getItem(STORAGE_KEY);
			if (stored && sidebars.includes(stored)) {
				return stored;
			}
		} catch (e) {
			/* ignore */
		}
		return null;
	}

	function sales_quote_main_service_from_locals(docname) {
		if (!docname || !locals["Sales Quote"] || !locals["Sales Quote"][docname]) {
			return null;
		}
		return locals["Sales Quote"][docname].main_service || null;
	}

	function map_main_service_to_sidebar(sidebars, main_service) {
		var mapped = MAIN_SERVICE_WORKSPACE[main_service];
		if (mapped && sidebars.includes(mapped)) {
			return mapped;
		}
		return null;
	}

	function sales_quote_main_service_sidebar(sidebars, docname) {
		return map_main_service_to_sidebar(sidebars, sales_quote_main_service_from_locals(docname));
	}

	function resolve_workspace_sidebar(sb) {
		var link_to = route_link_to();
		if (!link_to || !sb.get_workspace_sidebars) {
			return null;
		}
		var sidebars = sb.get_workspace_sidebars(link_to);
		if (!sidebars.length) {
			return null;
		}
		if (sidebars.length === 1) {
			return sidebars[0];
		}

		var route = frappe.get_route();
		var stored = recalled_workspace_sidebar(sidebars);
		if (stored) {
			return stored;
		}

		if (link_to === "Sales Quote" && route_view() === "form" && route[2]) {
			var from_doc = sales_quote_main_service_sidebar(sidebars, route[2]);
			if (from_doc) {
				return from_doc;
			}
		}

		if (link_to === "Sales Quote" && route_view() === "list") {
			var module_default = MODULE_DEFAULT_WORKSPACE_SIDEBAR["Pricing Center"];
			if (module_default && sidebars.includes(module_default)) {
				return module_default;
			}
		}

		var module = frappe.router && frappe.router.meta && frappe.router.meta.module;
		if (module && MODULE_DEFAULT_WORKSPACE_SIDEBAR[module]) {
			var mod_default = MODULE_DEFAULT_WORKSPACE_SIDEBAR[module];
			if (sidebars.includes(mod_default)) {
				return mod_default;
			}
		}
		if (module && sb.get_workspace_for_module) {
			var by_workspace = sb.get_workspace_for_module(module);
			if (by_workspace && sidebars.includes(by_workspace)) {
				return by_workspace;
			}
			var boot = frappe.boot.workspace_sidebar_item[module.toLowerCase()];
			if (boot && boot.label && sidebars.includes(boot.label)) {
				return boot.label;
			}
		}

		return sidebars[0];
	}

	function apply_workspace_sidebar_title(sb, title) {
		if (!title) {
			if (typeof sb.set_workspace_sidebar === "function") {
				sb.set_workspace_sidebar(frappe.router);
			}
			return;
		}
		var items = sb.workspace_sidebar_items;
		if (sb.sidebar_title !== title || !items || !items.length) {
			sb.setup(title);
			remember_workspace_sidebar(title);
		}
	}

	function ensure_workspace_sidebar_items(sb) {
		if (!page_allows_main_sidebar()) {
			return;
		}
		var items = sb.workspace_sidebar_items;
		if (items && items.length) {
			return;
		}
		var title = resolve_workspace_sidebar(sb);
		if (title) {
			apply_workspace_sidebar_title(sb, title);
			return;
		}

		var route = frappe.get_route();
		var link_to = route_link_to();
		if (link_to === "Sales Quote" && route && route_view() === "form" && route[2] && sb.get_workspace_sidebars) {
			var sidebars = sb.get_workspace_sidebars("Sales Quote");
			if (sidebars.length > 1 && !sales_quote_main_service_from_locals(route[2])) {
				frappe.db.get_value("Sales Quote", route[2], "main_service", function (r) {
					var from_doc = map_main_service_to_sidebar(
						sidebars,
						r.message && r.message.main_service
					);
					apply_workspace_sidebar_title(
						sb,
						from_doc || recalled_workspace_sidebar(sidebars) || sidebars[0]
					);
				});
				return;
			}
		}

		apply_workspace_sidebar_title(sb, title);
	}

	function sync_main_sidebar(retry) {
		retry = retry || 0;
		var sb = get_sidebar();
		if (!sb || !sb.wrapper || !sb.wrapper.length) {
			return;
		}
		if (!page_allows_main_sidebar()) {
			return;
		}

		if (!form_page_ready()) {
			if (retry < MAX_RETRIES) {
				setTimeout(function () {
					sync_main_sidebar(retry + 1);
				}, RETRY_MS);
			}
			return;
		}

		if (typeof sb.toggle === "function") {
			sb.toggle();
		} else {
			sb.wrapper.show();
		}
		ensure_workspace_sidebar_items(sb);
	}

	function schedule_sync() {
		setTimeout(function () {
			sync_main_sidebar(0);
		}, 0);
	}

	function bind_when_ready() {
		if (typeof frappe === "undefined" || !frappe.router || !frappe.router.on) {
			setTimeout(bind_when_ready, 50);
			return;
		}
		frappe.router.on("change", schedule_sync);
		$(document).on("page-change", schedule_sync);
		$(document).on("form-refresh", schedule_sync);
		$(document).on("form-load", function (_e, frm) {
			if (frm && frm.doctype === "Sales Quote") {
				schedule_sync();
			}
		});
		// List view: meta/page ready slightly later than form on hard reload.
		if (frappe.views && frappe.views.ListView) {
			var _list_show = frappe.views.ListView.prototype.show;
			frappe.views.ListView.prototype.show = function () {
				var ret = _list_show.apply(this, arguments);
				if (this.doctype === "Sales Quote") {
					schedule_sync();
				}
				return ret;
			};
		}
		$(document).on("sidebar_setup", function (e, data) {
			var title = data && data.sidebar && data.sidebar.sidebar_title;
			remember_workspace_sidebar(title);
		});
		schedule_sync();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", bind_when_ready);
	} else {
		bind_when_ready();
	}
})();
