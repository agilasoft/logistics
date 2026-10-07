// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Dismissible Transport-module banners for expiring and expired vehicle permits.
(function () {
	"use strict";

	const STORAGE_PREFIX = "logistics.vehicle_permit_banner.";

	function route_args() {
		const route = (frappe.get_route && frappe.get_route()) || [];
		const first = (route[0] || "").toString();
		const second = (route[1] || "").toString();
		const head = first.toLowerCase();
		if (head === "workspaces") {
			return { kind: "workspace", name: second };
		}
		if (head === "list" || head === "form" || head === "tree" || head === "report") {
			return { kind: "doctype", name: second };
		}
		if (head === "query-report") {
			return { kind: "report", name: second };
		}
		if (head === "dashboard" || head === "dashboard-view") {
			return { kind: "dashboard", name: second };
		}
		if (route.length <= 1) {
			return { kind: "page_or_workspace", name: first };
		}
		return { kind: "other", name: first };
	}

	function dismissed(kind, fingerprint) {
		try {
			return localStorage.getItem(STORAGE_PREFIX + kind) === fingerprint;
		} catch (e) {
			return false;
		}
	}

	function remember_dismiss(kind, fingerprint) {
		try {
			localStorage.setItem(STORAGE_PREFIX + kind, fingerprint);
		} catch (e) {
			// Private browsing can block storage; the banner still closes for this view.
		}
	}

	function host() {
		return document.querySelector(".layout-main-section") || document.querySelector(".page-content");
	}

	function clear_banners() {
		document.querySelectorAll(".vehicle-permit-banner").forEach((node) => node.remove());
	}

	function render_banner(kind, payload) {
		if (!payload || !payload.body || dismissed(kind, payload.fingerprint)) {
			return;
		}
		const parent = host();
		if (!parent) {
			return;
		}
		const banner = document.createElement("div");
		banner.className = "vehicle-permit-banner vehicle-permit-banner--" + kind;
		banner.setAttribute("role", "status");

		const text = document.createElement("div");
		text.className = "vehicle-permit-banner__text";
		const title = document.createElement("strong");
		title.textContent = (payload.title || "") + ": ";
		text.appendChild(title);
		payload.body.split("\n").forEach((line, index) => {
			if (index) {
				text.appendChild(document.createElement("br"));
			}
			text.appendChild(document.createTextNode(line));
		});

		const close = document.createElement("button");
		close.type = "button";
		close.className = "vehicle-permit-banner__close";
		close.setAttribute("aria-label", __("Dismiss"));
		close.textContent = "\u00d7";
		close.addEventListener("click", () => {
			remember_dismiss(kind, payload.fingerprint);
			banner.remove();
		});

		banner.appendChild(text);
		banner.appendChild(close);
		parent.insertBefore(banner, parent.firstChild);
	}

	function refresh() {
		if (!frappe.session || frappe.session.user === "Guest") {
			clear_banners();
			return;
		}
		const args = route_args();
		frappe.call({
			method: "logistics.transport.vehicle_permits.get_vehicle_permit_banners",
			args: args,
			callback(r) {
				clear_banners();
				const message = r && r.message;
				if (!message || !message.applicable || !message.enabled) {
					return;
				}
				// Expired sits above the advance warning when both are present.
				render_banner("expiring", message.expiring);
				render_banner("expired", message.expired);
			},
		});
	}

	frappe.provide("logistics.vehicle_permit_banner");
	logistics.vehicle_permit_banner.refresh = refresh;

	function bind() {
		if (frappe.router && !frappe.router.__vehicle_permit_banner) {
			frappe.router.on("change", () => setTimeout(refresh, 250));
			frappe.router.__vehicle_permit_banner = true;
		}
		setTimeout(refresh, 400);
	}

	if (frappe.router) {
		bind();
	} else {
		$(document).on("app_ready", bind);
	}
})();
