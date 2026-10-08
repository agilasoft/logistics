// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Show the desk sidebar once the page on screen exists.
 *
 * Frappe 16.50 hides both shells until frappe.ui.Page is attached, then
 * make_app_page calls apply_page_visibility. A route can still resolve
 * visibility before that page exists, which leaves the sidebar hidden.
 * This retries the same call. It does not pick a sidebar: each module has one.
 */
(function () {
	"use strict";
	if (window.__logistics_main_sidebar_visibility__) {
		return;
	}
	window.__logistics_main_sidebar_visibility__ = true;

	var MAX_RETRIES = 24;
	var RETRY_MS = 50;

	function get_sidebar() {
		return frappe.app && frappe.app.sidebar;
	}

	function page_ready() {
		return !!(frappe.container && frappe.container.page && frappe.container.page.page);
	}

	function sync_main_sidebar(retry) {
		retry = retry || 0;
		var sb = get_sidebar();
		if (!sb || typeof sb.apply_page_visibility !== "function") {
			if (retry < MAX_RETRIES) {
				setTimeout(function () {
					sync_main_sidebar(retry + 1);
				}, RETRY_MS);
			}
			return;
		}
		sb.apply_page_visibility();
		if (!page_ready() && retry < MAX_RETRIES) {
			setTimeout(function () {
				sync_main_sidebar(retry + 1);
			}, RETRY_MS);
		}
	}

	function schedule_sync() {
		setTimeout(function () {
			sync_main_sidebar(0);
		}, 0);
	}

	// The CargoNext rail, top to bottom. A saved arrangement must not put the
	// old line icons ahead of these, or bring back modules that are not listed.
	var DOCK_ORDER = [
		"Air Freight",
		"Sea Freight",
		"Customs",
		"Transport",
		"Warehousing",
		"Job Management",
		"Special Projects",
		"MICE",
		"High Value",
		"Time Sensitive",
		"Sustainability",
		"Pricing Center",
	];

	function install_dock_merge() {
		var Sidebar = frappe.ui && frappe.ui.Sidebar;
		if (!Sidebar || !Sidebar.prototype || typeof Sidebar.prototype.apply_dock_arrangement !== "function") {
			return false;
		}
		if (Sidebar.prototype.__logistics_dock_merge__) {
			return true;
		}
		Sidebar.prototype.apply_dock_arrangement = function (entries) {
			var by_module = {};
			(entries || []).forEach(function (entry) {
				if (entry && entry.link_type === "Sidebar" && entry.link_to) {
					by_module[entry.link_to] = entry;
				}
			});
			return DOCK_ORDER.map(function (name) {
				return by_module[name];
			}).filter(Boolean);
		};
		Sidebar.prototype.__logistics_dock_merge__ = true;
		var sb = get_sidebar();
		if (sb && sb.dock) {
			sb.dock.rendered = null;
			if (typeof sb.refresh_dock === "function") {
				sb.refresh_dock();
			}
		}
		return true;
	}

	function bind_when_ready() {
		if (typeof frappe === "undefined" || !frappe.router || !frappe.router.on) {
			setTimeout(bind_when_ready, 50);
			return;
		}
		var tries = 0;
		function merge_until_ready() {
			if (install_dock_merge() || tries > 200) {
				return;
			}
			tries += 1;
			setTimeout(merge_until_ready, 50);
		}
		merge_until_ready();
		frappe.router.on("change", function () {
			install_dock_merge();
			schedule_sync();
		});
		$(document).on("page-change", schedule_sync);
		schedule_sync();
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", bind_when_ready);
	} else {
		bind_when_ready();
	}
})();
