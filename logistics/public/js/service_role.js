// Copyright (c) 2026, Agilasoft and contributors
// Service role (Main / Linked / Standalone) desk helpers — extends legacy MS/IJ mutual exclusivity.

(function () {
	if (typeof window.logistics_apply_service_role_field_visibility === "function") {
		return;
	}

	function logistics_service_role_from_doc(doc) {
		if (!doc) return "Standalone";
		const role = (doc.service_role || "").trim();
		if (role === "Main" || role === "Linked" || role === "Standalone") {
			return role;
		}
		if (cint(doc.is_internal_job)) return "Linked";
		if (cint(doc.is_main_service)) return "Main";
		return "Standalone";
	}

	window.logistics_service_role_from_doc = logistics_service_role_from_doc;

	window.logistics_apply_service_role_field_visibility = function (frm) {
		if (!frm || !frm.doc) return;
		const role = logistics_service_role_from_doc(frm.doc);
		const linked = role === "Linked";
		const main = role === "Main";
		["main_service_type", "main_service", "main_job_type", "main_job"].forEach((fn) => {
			if (frm.fields_dict[fn]) {
				frm.toggle_reqd(fn, linked);
				frm.toggle_display(fn, linked);
			}
		});
		if (frm.fields_dict.service_role) {
			frm.toggle_display("service_scope", main || linked);
		}
		if (typeof logistics_apply_main_service_internal_job_mutual_exclusive === "function") {
			logistics_apply_main_service_internal_job_mutual_exclusive(frm);
		}
	};
})();
