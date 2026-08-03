// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Listview indicators + timer icon for Time Sensitive Case and flagged operational docs.
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
		settings.formatters = settings.formatters || {};
		const nameFmt = settings.formatters.name;
		settings.formatters.name = function (value, df, doc) {
			if (cint(doc.is_time_sensitive)) {
				return logistics.time_sensitive.timer.titleWithTimerIcon(value, doc);
			}
			if (typeof nameFmt === "function") {
				return nameFmt(value, df, doc);
			}
			return value;
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
