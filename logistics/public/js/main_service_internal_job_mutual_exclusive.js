// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Legacy Main Service / Internal Job checkbox exclusivity.
 * Service Role is now the source of truth; this file only applies sales-quote
 * MS/IJ desk rules when present and keeps service_role field visibility in sync.
 */
(function () {
	"use strict";

	if (typeof frappe === "undefined" || !frappe.ui || !frappe.ui.form || !frappe.ui.form.on) {
		return;
	}

	var DOCTYPES = [
		"Air Booking",
		"Air Shipment",
		"Sea Booking",
		"Sea Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration Order",
		"Declaration",
		"Warehouse Job",
		"VAS Order",
		"Inbound Order",
		"Release Order",
		"Project Job",
		"MICE Job",
	];

	function on_refresh(frm) {
		if (window.logistics && logistics.apply_sales_quote_ms_ij_rules) {
			logistics.apply_sales_quote_ms_ij_rules(frm);
		}
		if (typeof logistics_apply_service_role_field_visibility === "function") {
			logistics_apply_service_role_field_visibility(frm);
		}
	}

	DOCTYPES.forEach(function (dt) {
		frappe.ui.form.on(dt, { refresh: on_refresh });
	});
})();
