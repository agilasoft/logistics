// Copyright (c) 2026, Agilasoft and contributors
// Service role (Main / Linked / Standalone) desk helpers.

(function () {
	if (typeof window.logistics_apply_service_role_field_visibility === "function") {
		return;
	}

	var OPERATIONAL_DOCTYPES = [
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
		"Exhibit Job",
	];

	function logistics_service_role_from_doc(doc) {
		if (!doc) return "Standalone";
		const role = (doc.service_role || "").trim();
		if (role === "Main" || role === "Linked" || role === "Standalone") {
			return role;
		}
		if ((doc.main_service_type || doc.main_job_type) && (doc.main_service || doc.main_job)) {
			return "Linked";
		}
		return "Standalone";
	}

	window.logistics_service_role_from_doc = logistics_service_role_from_doc;

	window.logistics_apply_service_role_field_visibility = function (frm) {
		if (!frm || !frm.doc) return;
		const role = logistics_service_role_from_doc(frm.doc);
		const linked = role === "Linked";

		if (frm.fields_dict.service_role) {
			frm.set_df_property("service_role", "read_only", 1);
			frm.toggle_display("service_role", true);
		}

		["main_service_type", "main_service"].forEach(function (fn) {
			if (frm.fields_dict[fn]) {
				frm.set_df_property(fn, "read_only", 1);
				frm.toggle_reqd(fn, linked);
				frm.toggle_display(fn, linked);
			}
		});

		// Hide legacy fields if still present on an older cached meta.
		["is_internal_job", "is_main_service", "main_job_type", "main_job", "internal_job"].forEach(
			function (fn) {
				if (frm.fields_dict[fn]) {
					frm.set_df_property(fn, "hidden", 1);
					frm.toggle_display(fn, false);
				}
			}
		);

		if (frm.fields_dict.linked_service) {
			frm.set_df_property("linked_service", "hidden", 1);
			frm.toggle_display("linked_service", false);
		}
	};

	function on_refresh(frm) {
		logistics_apply_service_role_field_visibility(frm);
	}

	if (typeof frappe !== "undefined" && frappe.ui && frappe.ui.form && frappe.ui.form.on) {
		OPERATIONAL_DOCTYPES.forEach(function (dt) {
			frappe.ui.form.on(dt, {
				refresh: on_refresh,
				service_role: on_refresh,
			});
		});
	}
})();
