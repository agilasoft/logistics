// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/** Canonical charge-line service_type (aligned with Sales Quote Charge / Load Type modules). */
function cr_canonical_charge_service_type(st) {
	const raw = (st && String(st).trim()) || "";
	if (!raw) return "";
	const byTitle = {
		Air: "air",
		Sea: "sea",
		Transport: "transport",
		Custom: "custom",
		Customs: "custom",
		custom: "custom",
		customs: "custom",
		Warehousing: "warehousing",
		"Special Project": "special project",
		MICE: "exhibits",
		Exhibits: "exhibits",
		Events: "exhibits",
	};
	if (byTitle[raw] !== undefined) return byTitle[raw];
	const low = raw.toLowerCase();
	if (low === "customs") return "custom";
	if (low === "events" || low === "mice") return "exhibits";
	if (["air", "sea", "transport", "warehousing", "special project", "exhibits"].includes(low)) return low;
	return low;
}

function cr_item_charge_field_for_service_type(st) {
	const c = cr_canonical_charge_service_type(st);
	const m = {
		air: "custom_air_forwarding_charge",
		sea: "custom_sea_forwarding_charge",
		transport: "custom_land_transport_charge",
		custom: "custom_customs_charge",
		warehousing: "custom_warehousing_charge",
		"special project": "custom_special_project_charge",
		exhibits: "custom_mice_charge",
	};
	return m[c] || null;
}

/**
 * Static link_filters on item_code (disabled=0 only) override get_query on every Link search.
 * Strip so Service Type → Item logistics checkbox filters apply (same as Sales Quote Charge).
 */
function cr_strip_charge_item_code_link_filters_from_meta(frm) {
	const df = frappe.meta.get_docfield("Change Request Charge", "item_code");
	if (df && df.link_filters) {
		df.link_filters = null;
	}
	if (frm && frm.fields_dict && frm.fields_dict.charges && frm.fields_dict.charges.grid) {
		const gdf = frm.fields_dict.charges.grid.get_docfield("item_code");
		if (gdf && gdf.link_filters) {
			gdf.link_filters = null;
		}
	}
}

/** Item link filters for a charge row from service_type (Item Logistics tab checkboxes). */
function cr_item_code_filters_for_charge_row(row) {
	const filters = { disabled: 0 };
	if (!row) return filters;
	const field = cr_item_charge_field_for_service_type(row.service_type);
	if (field) {
		filters[field] = 1;
	}
	return filters;
}

/** Re-apply item_code Link query after service_type changes (grid row or expanded child form). */
function cr_refresh_charge_item_code_link(frm, cdt, cdn) {
	const grid = frm.fields_dict.charges && frm.fields_dict.charges.grid;
	if (grid && cdn && grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn]) {
		const grid_row = grid.grid_rows_by_docname[cdn];
		if (grid_row.refresh_field) {
			grid_row.refresh_field("item_code");
		}
	}
	if (frappe.ui.form.get_open_grid_form) {
		const grid_form = frappe.ui.form.get_open_grid_form();
		if (
			grid_form &&
			grid_form.doc &&
			grid_form.doc.doctype === cdt &&
			grid_form.doc.name === cdn &&
			grid_form.fields_dict.item_code
		) {
			grid_form.fields_dict.item_code.refresh();
		}
	}
}

/** Resolve charge row for item_code get_query (expanded grid form can pass stale cdn). */
function cr_resolved_change_request_charge_row(frm, doc, cdt, cdn) {
	if (cdt !== "Change Request Charge") return null;
	let row = null;
	if (cdn) {
		row = frappe.get_doc(cdt, cdn) || (locals[cdt] && locals[cdt][cdn]) || null;
	}
	if ((!row || !row.name) && cdn && doc && doc.charges) {
		row = doc.charges.find((r) => r.name === cdn) || row;
	}
	if ((!row || !row.service_type) && frm && frm.cur_grid && frm.cur_grid.doc) {
		const d = frm.cur_grid.doc;
		if (d && d.doctype === cdt) row = d;
	}
	if ((!row || !row.service_type) && frappe.ui.form.get_open_grid_form) {
		const gr = frappe.ui.form.get_open_grid_form();
		const d = gr && gr.doc;
		if (d && d.doctype === cdt) row = d;
	}
	return row;
}

function _load_cr_allowed_vehicle_types(frm, load_type, callback) {
	if (!load_type) {
		if (callback) callback();
		return;
	}
	if (!frm.allowed_vehicle_types_cache) frm.allowed_vehicle_types_cache = {};
	if (frm.allowed_vehicle_types_cache[load_type]) {
		if (callback) callback();
		return;
	}
	frappe.call({
		method: "logistics.pricing_center.doctype.sales_quote.sales_quote.get_vehicle_types_for_load_type",
		args: { load_type: load_type },
		callback: function (r) {
			if (!frm.allowed_vehicle_types_cache) frm.allowed_vehicle_types_cache = {};
			if (r.message && r.message.vehicle_types) {
				frm.allowed_vehicle_types_cache[load_type] = r.message.vehicle_types;
			} else {
				frm.allowed_vehicle_types_cache[load_type] = [];
			}
			if (callback) callback();
		},
	});
}

frappe.ui.form.on("Change Request Charge", {
	service_type: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			frappe.model.set_value(cdt, cdn, "item_code", "");
			frappe.model.set_value(cdt, cdn, "item_name", "");
		}
		frm.events.setup_item_code_query(frm);
		cr_refresh_charge_item_code_link(frm, cdt, cdn);
	},

	load_type: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (cr_canonical_charge_service_type(row.service_type) !== "transport" || !row.load_type) return;
		if (!frm.allowed_vehicle_types_cache) frm.allowed_vehicle_types_cache = {};
		const previous_vehicle_type = row.vehicle_type;
		if (previous_vehicle_type) frappe.model.set_value(cdt, cdn, "vehicle_type", "");
		_load_cr_allowed_vehicle_types(frm, row.load_type, function () {
			if (!frm.allowed_vehicle_types_cache) frm.allowed_vehicle_types_cache = {};
			const allowed = frm.allowed_vehicle_types_cache[row.load_type] || [];
			if (previous_vehicle_type && allowed.length > 0 && allowed.includes(previous_vehicle_type)) {
				frappe.model.set_value(cdt, cdn, "vehicle_type", previous_vehicle_type);
			}
			frm.refresh_field("charges");
		});
	},

	calculation_method: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	unit_rate: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	quantity: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	unit_type: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	minimum_quantity: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	minimum_charge: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	maximum_charge: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	base_amount: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	cost_calculation_method: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	cost_quantity: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	unit_cost: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	cost_unit_type: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	cost_minimum_quantity: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	cost_minimum_charge: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	cost_maximum_charge: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
	cost_base_amount: function (frm, cdt, cdn) {
		_calculate_change_request_charge_row(frm, cdt, cdn);
	},
});

function _calculate_change_request_charge_row(frm, cdt, cdn) {
	if (!cdn) return;
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) return;
	frappe.call({
		method: "logistics.utils.charges_calculation.calculate_charge_row",
		args: {
			doctype: "Change Request Charge",
			parenttype: "Change Request",
			parent: frm.doc.name || "new",
			row_data: JSON.stringify(row),
		},
		callback: function (r) {
			if (r.message && r.message.success) {
				frappe.model.set_value(cdt, cdn, "estimated_revenue", r.message.estimated_revenue);
				frappe.model.set_value(cdt, cdn, "estimated_cost", r.message.estimated_cost);
				if (r.message.quantity != null) {
					frappe.model.set_value(cdt, cdn, "quantity", r.message.quantity);
				}
				if (r.message.cost_quantity != null) {
					frappe.model.set_value(cdt, cdn, "cost_quantity", r.message.cost_quantity);
				}
				frappe.model.set_value(cdt, cdn, "revenue_calc_notes", r.message.revenue_calc_notes || "");
				frappe.model.set_value(cdt, cdn, "cost_calc_notes", r.message.cost_calc_notes || "");
				if (logistics.charges_disbursement && logistics.charges_disbursement.apply_charge_row_response) {
					logistics.charges_disbursement.apply_charge_row_response(cdt, cdn, r);
				}
			}
		},
	});
}

/**
 * Job types that are linked-service satellite bookings (when a CR targets one of these, all charge
 * rows default to the satellite's own linked_service link, and the row-level linked_service is
 * restricted to that single value).
 */
const CR_LINKED_SERVICE_SATELLITE_JOB_TYPES = new Set([
	"Transport Order",
	"Sea Booking",
	"Air Booking",
	"Declaration Order",
	"Inbound Order",
	"Release Order",
]);

const CR_JOB_TYPE_TO_SERVICE_TYPE = {
	"Transport Job": "transport",
	"Warehouse Job": "warehousing",
	"Air Shipment": "air",
	"Sea Shipment": "sea",
	Declaration: "custom",
	"Declaration Order": "custom",
	"Special Project": "special project",
	// IJ satellite bookings: derive service from their implied service.
	"Transport Order": "transport",
	"Sea Booking": "sea",
	"Air Booking": "air",
	"Inbound Order": "warehousing",
	"Release Order": "warehousing",
};

/** Fetch eligible Linked Services for the CR's job_type/job; cache on the form. */
function cr_fetch_eligible_linked_services(frm, callback) {
	if (!frm.doc.job_type || !frm.doc.job) {
		frm._eligible_linked_services = {
			linked_services: [],
			default_linked_service: "",
			internal_jobs: [],
			default_internal_job: "",
		};
		if (callback) callback();
		return;
	}
	const cache_key = `${frm.doc.job_type}::${frm.doc.job}`;
	if (frm._eligible_linked_services_key === cache_key) {
		if (callback) callback();
		return;
	}
	frappe.call({
		method: "logistics.pricing_center.doctype.change_request.change_request.get_eligible_internal_jobs_for_change_request_job",
		args: { job_type: frm.doc.job_type, job_name: frm.doc.job },
		callback: function (r) {
			frm._eligible_linked_services_key = cache_key;
			const message = r.message || {};
			frm._eligible_linked_services = {
				linked_services: message.linked_services || message.internal_jobs || [],
				default_linked_service:
					message.default_linked_service || message.default_internal_job || "",
				internal_jobs: message.internal_jobs || message.linked_services || [],
				default_internal_job:
					message.default_internal_job || message.default_linked_service || "",
			};
			if (callback) callback();
		},
	});
}

frappe.ui.form.on("Change Request", {
	onload(frm) {
		frm.events.setup_item_code_query(frm);
		frm.events.setup_linked_service_query(frm);
		cr_fetch_eligible_linked_services(frm);
	},

	job_type(frm) {
		cr_fetch_eligible_linked_services(frm);
	},

	job(frm) {
		cr_fetch_eligible_linked_services(frm);
	},

	charges_add: function (frm, cdt, cdn) {
		const st = CR_JOB_TYPE_TO_SERVICE_TYPE[frm.doc.job_type];
		if (st) {
			frappe.model.set_value(cdt, cdn, "service_type", st);
		}
		// Default the new row's linked_service to the CR's resolved default (the satellite's
		// linked service when the CR targets a satellite booking).
		cr_fetch_eligible_linked_services(frm, function () {
			const eligible = frm._eligible_linked_services || {};
			const default_ls = eligible.default_linked_service;
			if (default_ls) {
				frappe.model.set_value(cdt, cdn, "linked_service", default_ls);
			}
		});
	},

	setup_linked_service_query(frm) {
		if (!frm.fields_dict.charges) return;
		frm.set_query("linked_service", "charges", function () {
			const eligible =
				(frm._eligible_linked_services && frm._eligible_linked_services.linked_services) || [];
			const names = eligible.map((r) => r.name).filter(Boolean);
			if (names.length === 0) {
				if (CR_LINKED_SERVICE_SATELLITE_JOB_TYPES.has(frm.doc.job_type)) {
					return { filters: {} };
				}
				return { filters: { parent_booking_name: frm.doc.job || "" } };
			}
			return { filters: { name: ["in", names] } };
		});
	},

	setup_item_code_query(frm) {
		cr_strip_charge_item_code_link_filters_from_meta(frm);
		if (!frm.fields_dict.charges) return;
		frm.set_query("item_code", "charges", function (doc, cdt, cdn) {
			cr_strip_charge_item_code_link_filters_from_meta(frm);
			const row = cr_resolved_change_request_charge_row(frm, doc, cdt, cdn);
			return { filters: cr_item_code_filters_for_charge_row(row) };
		});
	},

	refresh(frm) {
		cr_strip_charge_item_code_link_filters_from_meta(frm);
		frm.events.setup_item_code_query(frm);
		frm.events.setup_linked_service_query(frm);
		cr_fetch_eligible_linked_services(frm);
		// Cost lines are pushed to the job when the Change Request is submitted; revenue is updated when the linked Sales Quote is submitted.
		if (
			!frm.doc.__islocal &&
			frm.doc.docstatus === 1 &&
			frm.doc.status !== "Sales Quote Created" &&
			frm.doc.charges &&
			frm.doc.charges.length > 0
		) {
			frm.add_custom_button(__("Create Sales Quote"), function () {
				frappe.confirm(
					__("Create a Sales Quote for this Change Request (Additional Charge)?"),
					function () {
						frappe.call({
							method: "logistics.pricing_center.doctype.change_request.change_request.create_sales_quote_from_change_request",
							args: { change_request_name: frm.doc.name },
							callback: function (r) {
								if (r.message) {
									frappe.set_route("Form", "Sales Quote", r.message);
									frm.reload_doc();
								}
							},
						});
					}
				);
			}, __("Create"));
		}
	},
});
