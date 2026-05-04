// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

(function () {
	"use strict";

	var JOB_TYPE_BY_SERVICE = {
		Air: "Air Booking",
		Sea: "Sea Booking",
		Transport: "Transport Order",
		Customs: "Declaration Order",
		Warehousing: "Inbound Order",
		"Special Project": "Project Task Job",
	};

	/** Fields that should refresh the auto-generated Job Description when edited */
	var IJD_DESC_FIELDS = [
		"air_house_type",
		"airline",
		"freight_agent",
		"sea_house_type",
		"freight_agent_sea",
		"shipping_line",
		"transport_mode",
		"load_type",
		"direction",
		"origin_port",
		"destination_port",
		"transport_template",
		"vehicle_type",
		"container_type",
		"container_no",
		"location_type",
		"location_from",
		"location_to",
		"pick_mode",
		"drop_mode",
		"customs_authority",
		"declaration_type",
		"customs_broker",
		"customs_charge_category",
		"sp_site",
		"sp_manpower",
		"sp_skilled",
		"sp_equipment_type",
		"sp_handling",
		"sp_resource_notes",
		"job_type",
		"job_no",
	];

	function sync_job_type_from_service(cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (!row) {
			return;
		}
		var st = String(row.service_type || "").trim();
		var jt = JOB_TYPE_BY_SERVICE[st];
		if (jt) {
			frappe.model.set_value(cdt, cdn, "job_type", jt);
		}
	}

	function push_ijd_job_description(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row || !String(row.service_type || "").trim()) {
			return;
		}
		frappe.call({
			method: "logistics.logistics.doctype.internal_job_detail.internal_job_detail.suggest_job_description",
			args: { row: row },
			callback: function (r) {
				if (r.message === undefined || r.message === null) {
					return;
				}
				frappe.model.set_value(cdt, cdn, "job_description", r.message);
			},
		});
	}

	var debounced_ijd_desc =
		typeof frappe.utils.debounce === "function"
			? frappe.utils.debounce(function (frm, cdt, cdn) {
					push_ijd_job_description(frm, cdt, cdn);
			  }, 250)
			: function (frm, cdt, cdn) {
					push_ijd_job_description(frm, cdt, cdn);
			  };

	var events = {
		service_type: function (frm, cdt, cdn) {
			sync_job_type_from_service(cdt, cdn);
			push_ijd_job_description(frm, cdt, cdn);
		},
	};

	IJD_DESC_FIELDS.forEach(function (fieldname) {
		events[fieldname] = function (frm, cdt, cdn) {
			debounced_ijd_desc(frm, cdt, cdn);
		};
	});

	frappe.ui.form.on("Internal Job Detail", events);
})();
