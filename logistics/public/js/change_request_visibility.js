/*!
 * Change Request form visibility: Job Type / Job lock + fields by job type ∩ change_sections.
 * Keep JOB_TYPE_HEADER_FIELDS in sync with change_request_field_apply.py.
 */
frappe.provide("logistics.change_request_visibility");

(function () {
	"use strict";

	const SECTION_FIELDS = {
		Parties: [
			"customer",
			"local_customer",
			"booking_party",
			"shipper",
			"consignee",
			"shipper_address",
			"consignee_address",
			"shipper_contact",
			"consignee_contact",
			"notify_party",
			"notify_party_address",
			"freight_agent",
			"sending_agent",
			"receiving_agent",
			"broker",
			"controlling_party",
			"incoterm",
			"direction",
			"house_type",
			"release_type",
			"entry_type",
			"service_level",
			"logistics_service_level",
		],
		"Places & Dates": [
			"origin_port",
			"destination_port",
			"etd",
			"eta",
			"scheduled_date",
			"booking_date",
			"vehicle_type",
			"transport_mode",
			"load_type",
			"transport_company",
			"transport_job_type",
			"container_type",
			"container_no",
			"cargo_cut_off",
			"document_cut_off",
			"vgm_cut_off",
			"gate_in_cut_off",
			"empty_return_cut_off",
			"other_cut_off",
			"run_date",
			"run_type",
			"route_name",
			"vehicle",
			"driver",
			"trailer_type",
			"dispatch_terminal",
			"return_terminal",
			"estimated_completion_time",
			"estimated_dispatch_datetime",
			"estimated_return_datetime",
			"transport_consolidation",
		],
		Notes: [
			"internal_notes",
			"client_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"description",
			"marks_and_nos",
			"customer_ref_no",
			"dispatcher",
			"return_inspector",
			"remarks",
		],
	};

	const AIR_SEA_PARTIES = [
		"local_customer",
		"booking_party",
		"shipper",
		"consignee",
		"shipper_address",
		"consignee_address",
		"shipper_contact",
		"consignee_contact",
		"notify_party",
		"notify_party_address",
		"freight_agent",
		"sending_agent",
		"receiving_agent",
		"broker",
		"controlling_party",
		"incoterm",
		"direction",
		"house_type",
		"release_type",
		"entry_type",
		"service_level",
	];

	const AIR_SEA_PLACES = [
		"origin_port",
		"destination_port",
		"etd",
		"eta",
		"booking_date",
		"transport_mode",
		"load_type",
	];

	const SEA_CUTOFFS = [
		"cargo_cut_off",
		"document_cut_off",
		"vgm_cut_off",
		"gate_in_cut_off",
		"empty_return_cut_off",
		"other_cut_off",
	];

	const AIR_SEA_NOTES = [
		"internal_notes",
		"client_notes",
		"sales_rep",
		"operations_rep",
		"customer_service_rep",
		"description",
		"marks_and_nos",
	];

	const TRANSPORT_PLACES = [
		"scheduled_date",
		"booking_date",
		"vehicle_type",
		"transport_mode",
		"load_type",
		"transport_company",
		"transport_job_type",
		"container_type",
		"container_no",
	];

	const TRANSPORT_NOTES = [
		"internal_notes",
		"client_notes",
		"sales_rep",
		"operations_rep",
		"customer_service_rep",
		"customer_ref_no",
	];

	const RUN_SHEET_PLACES = [
		"vehicle_type",
		"transport_company",
		"run_date",
		"run_type",
		"route_name",
		"vehicle",
		"driver",
		"trailer_type",
		"dispatch_terminal",
		"return_terminal",
		"estimated_completion_time",
		"estimated_dispatch_datetime",
		"estimated_return_datetime",
		"transport_consolidation",
	];

	function set_of(arr) {
		const o = {};
		(arr || []).forEach(function (x) {
			o[x] = true;
		});
		return o;
	}

	const JOB_TYPE_HEADER_FIELDS = {
		"Air Shipment": set_of(AIR_SEA_PARTIES.concat(AIR_SEA_PLACES, AIR_SEA_NOTES)),
		"Air Booking": set_of(AIR_SEA_PARTIES.concat(AIR_SEA_PLACES, AIR_SEA_NOTES)),
		"Sea Shipment": set_of(
			AIR_SEA_PARTIES.concat(AIR_SEA_PLACES, SEA_CUTOFFS, [
				"internal_notes",
				"sales_rep",
				"operations_rep",
				"customer_service_rep",
				"description",
				"marks_and_nos",
			])
		),
		"Sea Booking": set_of(AIR_SEA_PARTIES.concat(AIR_SEA_PLACES, SEA_CUTOFFS, AIR_SEA_NOTES)),
		"Transport Job": set_of(
			[
				"customer",
				"shipper",
				"consignee",
				"shipper_address",
				"consignee_address",
				"shipper_contact",
				"consignee_contact",
				"logistics_service_level",
			].concat(TRANSPORT_PLACES, TRANSPORT_NOTES)
		),
		"Transport Order": set_of(
			[
				"customer",
				"shipper",
				"consignee",
				"shipper_address",
				"consignee_address",
				"shipper_contact",
				"consignee_contact",
				"service_level",
			].concat(TRANSPORT_PLACES, TRANSPORT_NOTES)
		),
		"Warehouse Job": set_of(["customer", "shipper", "consignee", "logistics_service_level"]),
		"Inbound Order": set_of(["customer", "shipper", "consignee"]),
		"Release Order": set_of(["customer", "shipper", "consignee"]),
		"Cross-Docking Order": set_of(["customer", "shipper", "consignee"]),
		Declaration: set_of([
			"customer",
			"notify_party",
			"notify_party_address",
			"freight_agent",
			"incoterm",
			"service_level",
			"etd",
			"eta",
			"transport_mode",
			"internal_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"remarks",
		]),
		"Declaration Order": set_of([
			"customer",
			"notify_party",
			"freight_agent",
			"incoterm",
			"service_level",
			"etd",
			"eta",
			"transport_mode",
			"internal_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"remarks",
		]),
		"Special Project": set_of([
			"customer",
			"logistics_service_level",
			"internal_notes",
			"client_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"description",
		]),
		Docket: set_of([
			"customer",
			"internal_notes",
			"client_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"description",
		]),
		"Run Sheet": set_of(RUN_SHEET_PLACES.concat(["dispatcher", "return_inspector"])),
	};

	const JOB_TYPES_WITH_PACKAGES = set_of([
		"Air Shipment",
		"Air Booking",
		"Sea Shipment",
		"Sea Booking",
		"Transport Job",
		"Transport Order",
		"Declaration",
		"Declaration Order",
		"Special Project",
		"Docket",
	]);

	const JOB_TYPES_WITHOUT_CHARGES = set_of(["Run Sheet"]);
	const JOB_TYPES_WITHOUT_SERVICES = set_of(["Run Sheet"]);

	/** Layout blocks: hide when none of their member data fields are visible. */
	const LAYOUT_GROUPS = [
		{
			fields: ["parties_tab"],
			members: [
				"customer",
				"local_customer",
				"booking_party",
				"controlling_party",
				"shipper",
				"consignee",
				"freight_agent",
				"shipper_address",
				"shipper_contact",
				"consignee_address",
				"consignee_contact",
				"notify_party",
				"notify_party_address",
				"sending_agent",
				"receiving_agent",
				"broker",
				"incoterm",
				"direction",
				"house_type",
				"release_type",
				"entry_type",
				"service_level",
				"logistics_service_level",
			],
		},
		{
			fields: ["section_parties", "column_break_parties"],
			members: [
				"customer",
				"local_customer",
				"booking_party",
				"controlling_party",
				"shipper",
				"consignee",
				"freight_agent",
			],
		},
		{
			fields: ["section_party_addresses", "column_break_party_addr"],
			members: [
				"shipper_address",
				"shipper_contact",
				"consignee_address",
				"consignee_contact",
			],
		},
		{
			fields: ["section_notify", "column_break_agents"],
			members: [
				"notify_party",
				"notify_party_address",
				"sending_agent",
				"receiving_agent",
				"broker",
			],
		},
		{
			fields: ["section_commercial_party", "column_break_commercial"],
			members: [
				"incoterm",
				"direction",
				"house_type",
				"release_type",
				"entry_type",
				"service_level",
				"logistics_service_level",
			],
		},
		{
			// Whole Places tab — any routing / transport / run-sheet / cut-off field.
			fields: ["places_tab"],
			members: [
				"origin_port",
				"destination_port",
				"etd",
				"eta",
				"scheduled_date",
				"booking_date",
				"transport_mode",
				"load_type",
				"vehicle_type",
				"transport_company",
				"transport_job_type",
				"container_type",
				"container_no",
				"run_date",
				"run_type",
				"route_name",
				"vehicle",
				"driver",
				"trailer_type",
				"transport_consolidation",
				"dispatch_terminal",
				"return_terminal",
				"estimated_dispatch_datetime",
				"estimated_return_datetime",
				"estimated_completion_time",
				"cargo_cut_off",
				"document_cut_off",
				"vgm_cut_off",
				"gate_in_cut_off",
				"empty_return_cut_off",
				"other_cut_off",
			],
		},
		{
			fields: ["section_places", "column_break_places"],
			members: [
				"origin_port",
				"destination_port",
				"etd",
				"eta",
				"scheduled_date",
				"booking_date",
				"transport_mode",
				"load_type",
			],
		},
		{
			fields: ["section_transport_places", "column_break_container"],
			members: [
				"vehicle_type",
				"transport_company",
				"transport_job_type",
				"container_type",
				"container_no",
			],
		},
		{
			fields: ["section_run_sheet", "column_break_run_sheet"],
			members: [
				"run_date",
				"run_type",
				"route_name",
				"vehicle",
				"driver",
				"trailer_type",
				"transport_consolidation",
			],
		},
		{
			fields: ["section_run_sheet_terminals", "column_break_run_sheet_est"],
			members: [
				"dispatch_terminal",
				"return_terminal",
				"estimated_dispatch_datetime",
				"estimated_return_datetime",
				"estimated_completion_time",
			],
		},
		{
			fields: ["section_cutoffs", "column_break_cutoffs"],
			members: [
				"cargo_cut_off",
				"document_cut_off",
				"vgm_cut_off",
				"gate_in_cut_off",
				"empty_return_cut_off",
				"other_cut_off",
			],
		},
		{
			fields: ["notes_tab"],
			members: [
				"internal_notes",
				"client_notes",
				"sales_rep",
				"operations_rep",
				"customer_service_rep",
				"dispatcher",
				"return_inspector",
				"description",
				"marks_and_nos",
				"customer_ref_no",
				"remarks",
			],
		},
		{
			fields: ["section_notes", "column_break_notes"],
			members: [
				"internal_notes",
				"client_notes",
				"sales_rep",
				"operations_rep",
				"customer_service_rep",
				"dispatcher",
				"return_inspector",
			],
		},
		{
			fields: ["section_cargo_notes"],
			members: ["description", "marks_and_nos", "customer_ref_no"],
		},
		{
			fields: ["section_break_remarks"],
			members: ["remarks"],
		},
	];

	function parse_sections(value) {
		if (!value) return [];
		if (Array.isArray(value)) {
			return value.map(function (v) {
				return String(v || "").trim();
			}).filter(Boolean);
		}
		return String(value)
			.replace(/,/g, "\n")
			.split("\n")
			.map(function (s) {
				return s.trim();
			})
			.filter(Boolean);
	}

	function header_fields_for_job_type(job_type) {
		if (!job_type) return null;
		return JOB_TYPE_HEADER_FIELDS[job_type] || null;
	}

	function supports_packages(job_type) {
		if (!job_type) return true;
		return !!JOB_TYPES_WITH_PACKAGES[job_type];
	}

	function supports_charges(job_type) {
		if (!job_type) return true;
		return !JOB_TYPES_WITHOUT_CHARGES[job_type];
	}

	function supports_services(job_type) {
		if (!job_type) return true;
		return !JOB_TYPES_WITHOUT_SERVICES[job_type];
	}

	function applicable_header_fields(job_type, sections_value) {
		const by_type = header_fields_for_job_type(job_type);
		const sections = parse_sections(sections_value);
		let section_allowed = null;
		if (sections.length) {
			section_allowed = {};
			sections.forEach(function (sec) {
				(SECTION_FIELDS[sec] || []).forEach(function (fn) {
					section_allowed[fn] = true;
				});
			});
		}
		const out = {};
		const all = [];
		Object.keys(SECTION_FIELDS).forEach(function (sec) {
			SECTION_FIELDS[sec].forEach(function (fn) {
				all.push(fn);
			});
		});
		const source = by_type ? Object.keys(by_type) : all;
		source.forEach(function (fn) {
			if (by_type && !by_type[fn]) return;
			if (section_allowed && !section_allowed[fn]) return;
			out[fn] = true;
		});
		return out;
	}

	function section_in_scope(sections_value, label) {
		const sections = parse_sections(sections_value);
		if (!sections.length) return true;
		return sections.indexOf(label) !== -1;
	}

	function set_hidden(frm, fieldname, hidden) {
		if (!frm.fields_dict[fieldname]) return;
		frm.set_df_property(fieldname, "hidden", hidden ? 1 : 0);
	}

	function lock_job_context(frm) {
		const lock = !!cstr(frm.doc.job).trim();
		frm.set_df_property("job_type", "read_only", lock ? 1 : 0);
		frm.set_df_property("job", "read_only", lock ? 1 : 0);
	}

	function apply_visibility(frm) {
		if (!frm || !frm.doc) return;
		lock_job_context(frm);

		const job_type = cstr(frm.doc.job_type).trim();
		const applicable = applicable_header_fields(job_type, frm.doc.change_sections);

		Object.keys(SECTION_FIELDS).forEach(function (sec) {
			SECTION_FIELDS[sec].forEach(function (fn) {
				set_hidden(frm, fn, !applicable[fn]);
			});
		});

		LAYOUT_GROUPS.forEach(function (group) {
			const any = (group.members || []).some(function (fn) {
				return !!applicable[fn];
			});
			(group.fields || []).forEach(function (fn) {
				set_hidden(frm, fn, !any);
			});
		});

		const show_packages =
			supports_packages(job_type) && section_in_scope(frm.doc.change_sections, "Packages");
		set_hidden(frm, "packages_tab", !show_packages);
		set_hidden(frm, "package_changes", !show_packages);

		const show_charges =
			supports_charges(job_type) && section_in_scope(frm.doc.change_sections, "Charges");
		set_hidden(frm, "charges_tab", !show_charges);
		set_hidden(frm, "section_break_charges", !show_charges);
		set_hidden(frm, "charges", !show_charges);

		const show_services = supports_services(job_type);
		set_hidden(frm, "services_tab", !show_services);
		set_hidden(frm, "linked_services_section", !show_services);
		set_hidden(frm, "linked_services", !show_services);
	}

	logistics.change_request_visibility = {
		SECTION_FIELDS: SECTION_FIELDS,
		JOB_TYPE_HEADER_FIELDS: JOB_TYPE_HEADER_FIELDS,
		parse_sections: parse_sections,
		header_fields_for_job_type: header_fields_for_job_type,
		applicable_header_fields: applicable_header_fields,
		supports_packages: supports_packages,
		supports_charges: supports_charges,
		supports_services: supports_services,
		section_in_scope: section_in_scope,
		lock_job_context: lock_job_context,
		apply: apply_visibility,
	};
})();
