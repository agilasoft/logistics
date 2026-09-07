// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Listview indicators + timer icon for Time Sensitive Case and flagged operational docs.
 *
 * Subject/ID cells cannot use HTML formatters — Frappe list view sets the link via
 * textContent. Icons are injected in settings.refresh after each render.
 */
(function () {
	const OPERATIONAL = [
		"Sales Quote",
		"Air Booking",
		"Air Shipment",
		"Sea Booking",
		"Sea Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration Order",
		"Declaration",
		"Inbound Order",
		"Release Order",
		"VAS Order",
		"Cross-Docking Order",
		"Warehouse Job",
	];

	function enhance(settings) {
		const prevIndicator = settings.get_indicator;
		const prevAdd = settings.add_fields || [];
		const prevRefresh = settings.refresh;
		settings.add_fields = Array.from(
			new Set(
				prevAdd.concat([
					"is_time_sensitive",
					"critical_deadline",
					"time_sensitive_case",
					"ts_case_type",
					"sla_status",
					"status",
				])
			)
		);
		settings.get_indicator = function (doc) {
			if (cint(doc.is_time_sensitive) || doc.doctype === "Time Sensitive Case") {
				return logistics.time_sensitive.timer.getListIndicator(doc);
			}
			if (typeof prevIndicator === "function") {
				return prevIndicator(doc);
			}
		};
		settings.refresh = function (listview) {
			if (typeof prevRefresh === "function") {
				prevRefresh(listview);
			}
			logistics.time_sensitive.timer.injectListSubjectTimerIcons(listview);
		};
	}

	function cint(v) {
		return parseInt(v, 10) ? 1 : 0;
	}

	frappe.provide("logistics.time_sensitive");

	function applyAll() {
		OPERATIONAL.forEach((dt) => {
			frappe.listview_settings[dt] = frappe.listview_settings[dt] || {};
			enhance(frappe.listview_settings[dt]);
		});
	}

	applyAll();
})();
