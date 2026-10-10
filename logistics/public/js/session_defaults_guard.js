// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt

// Desk users without a personal Company default stay on Session Defaults
// until they save one. Logout stays available from the user menu.
(function () {
	"use strict";

	if (window.__logistics_session_defaults_guard__) {
		return;
	}
	window.__logistics_session_defaults_guard__ = true;

	const PAGE = "session-defaults";
	const STORAGE_KEY = "logistics_session_defaults_return_route";
	const HOME = "/desk/transport";

	frappe.provide("logistics.session_defaults");
	logistics.session_defaults.HOME = HOME;
	logistics.session_defaults.STORAGE_KEY = STORAGE_KEY;

	function needs_setup() {
		const flag = frappe.boot && frappe.boot.logistics_needs_session_defaults;
		return flag === true || flag === 1 || flag === "1";
	}

	function is_setup_route(route) {
		const path = window.location.pathname || "";
		// The setup wizard owns the desk until the site is ready. Sending the
		// user to Session Defaults from there makes the two redirects chase
		// each other and the page never finishes loading.
		if (path.indexOf("/" + PAGE) !== -1 || path.indexOf("/setup-wizard") !== -1) {
			return true;
		}
		const head = route && route[0];
		return head === PAGE || head === "setup-wizard";
	}

	// Store the desk path, not frappe.get_route(). Workspace routes such as
	// ["Workspaces", "Transport"] do not turn back into /desk/transport.
	logistics.session_defaults.remember_return_route = function () {
		try {
			if (sessionStorage.getItem(STORAGE_KEY)) {
				return;
			}
			const path = (window.location.pathname || "") + (window.location.search || "");
			if (!path.startsWith("/desk") || path.indexOf("/" + PAGE) !== -1) {
				return;
			}
			if (path.indexOf("/setup-wizard") !== -1) {
				return;
			}
			if (path === "/desk" || path === "/desk/") {
				return;
			}
			sessionStorage.setItem(STORAGE_KEY, path);
		} catch (e) {
			// Private browsing can reject sessionStorage. The home workdesk is the fallback.
		}
	};

	logistics.session_defaults.consume_return_route = function () {
		let path = null;
		try {
			path = sessionStorage.getItem(STORAGE_KEY);
			sessionStorage.removeItem(STORAGE_KEY);
		} catch (e) {
			path = null;
		}
		if (path && path.startsWith("/desk") && path.indexOf("/" + PAGE) === -1) {
			return path;
		}
		return null;
	};

	function enforce() {
		if (!needs_setup()) {
			document.body.classList.remove("logistics-needs-session-defaults");
			return;
		}
		document.body.classList.add("logistics-needs-session-defaults");
		const route = (frappe.get_route && frappe.get_route()) || [];
		if (!route.length || is_setup_route(route)) {
			return;
		}
		logistics.session_defaults.remember_return_route();
		frappe.set_route(PAGE);
	}

	function inject_menu_option(opts) {
		const groups = opts && opts.options;
		if (!Array.isArray(groups)) {
			return;
		}
		const is_user_menu = groups.some((group) =>
			(group.options || []).some((option) => option && option.name === "logout")
		);
		if (!is_user_menu) {
			return;
		}
		const first = groups[0];
		if (!first || !Array.isArray(first.options)) {
			return;
		}
		if (first.options.some((option) => option && option.name === "session-defaults")) {
			return;
		}
		const item = {
			name: "session-defaults",
			label: __("Session Defaults"),
			icon: "building",
			onclick() {
				logistics.session_defaults.remember_return_route();
				frappe.set_route(PAGE);
			},
		};
		const settings_index = first.options.findIndex(
			(option) => option && option.name === "settings"
		);
		if (settings_index >= 0) {
			first.options.splice(settings_index + 1, 0, item);
		} else {
			first.options.unshift(item);
		}
	}

	function install_user_menu_item() {
		const Sidebar = frappe.ui && frappe.ui.Sidebar;
		if (
			!Sidebar ||
			!Sidebar.prototype ||
			!Sidebar.prototype.create_user_menu ||
			Sidebar.prototype.__logistics_session_defaults_menu
		) {
			return;
		}
		const original = Sidebar.prototype.create_user_menu;
		Sidebar.prototype.create_user_menu = function (args) {
			const OriginalDropdown = frappe.ui.Dropdown;
			if (!OriginalDropdown) {
				return original.call(this, args);
			}
			function WrappedDropdown(options) {
				inject_menu_option(options);
				return new OriginalDropdown(options);
			}
			WrappedDropdown.prototype = OriginalDropdown.prototype;
			frappe.ui.Dropdown = WrappedDropdown;
			try {
				return original.call(this, args);
			} finally {
				frappe.ui.Dropdown = OriginalDropdown;
			}
		};
		Sidebar.prototype.__logistics_session_defaults_menu = true;
	}

	function start() {
		install_user_menu_item();
		if (!needs_setup()) {
			try {
				sessionStorage.removeItem(STORAGE_KEY);
			} catch (e) {
				// Ignore storage failures. A missing return route falls back to Transport.
			}
		}
		enforce();
		if (frappe.router && !frappe.router.__logistics_session_defaults) {
			frappe.router.on("change", enforce);
			frappe.router.__logistics_session_defaults = true;
		}
	}

	if (frappe.router) {
		start();
	}
	$(document).on("app_ready", start);
})();
