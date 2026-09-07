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

/** Item link filters for a charge row from service_type + charge_type. */
function cr_item_code_filters_for_charge_row(row) {
	const filters = { disabled: 0 };
	if (!row) return filters;
	const field = cr_item_charge_field_for_service_type(row.service_type);
	if (field) {
		filters[field] = 1;
	}
	if (row.charge_type) {
		filters.custom_default_charge_type = row.charge_type;
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

frappe.ui.form.on("Change Request Charge", {
	service_type: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.item_code) {
			frappe.model.set_value(cdt, cdn, "item_code", "");
			frappe.model.set_value(cdt, cdn, "item_name", "");
		}
		frm.events.setup_item_code_query(frm);
		cr_refresh_charge_item_code_link(frm, cdt, cdn);
		if (logistics.linked_service_link_query) {
			logistics.linked_service_link_query.clearLinkIfServiceTypeMismatch(frm, cdt, cdn);
		}
	},

	charge_type: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row && row.item_code) {
			frappe.model.set_value(cdt, cdn, "item_code", "");
			frappe.model.set_value(cdt, cdn, "item_name", "");
		}
		frm.events.setup_item_code_query(frm);
		cr_refresh_charge_item_code_link(frm, cdt, cdn);
	},

	charge_scope: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!row) return;
		const scope = (row.charge_scope || "Main").trim();
		if (scope !== "Linked" && scope !== "Internal Job" && row.linked_service) {
			frappe.model.set_value(cdt, cdn, "linked_service", "");
		}
	},

	calculation_method: function (frm, cdt, cdn) {
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
			if (logistics.charge_type_cleanup && logistics.charge_type_cleanup.apply_calculate_charge_row_response) {
				logistics.charge_type_cleanup.apply_calculate_charge_row_response(
					frm,
					cdt,
					cdn,
					r,
					"charges"
				);
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
	"Cross-Docking Order",
]);

const CR_JOB_TYPE_TO_SERVICE_TYPE = {
	"Transport Job": "transport",
	"Warehouse Job": "warehousing",
	"Air Shipment": "air",
	"Sea Shipment": "sea",
	Declaration: "custom",
	"Declaration Order": "custom",
	"Special Project": "special project",
	Docket: "exhibits",
	// IJ satellite bookings: derive service from their implied service.
	"Transport Order": "transport",
	"Sea Booking": "sea",
	"Air Booking": "air",
	"Inbound Order": "warehousing",
	"Release Order": "warehousing",
	"Cross-Docking Order": "cross-docking",
};

/** Fetch eligible Linked Services from this Change Request's Services tab (or job fallback). */
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
	const cache_key = `${frm.doc.name || "new"}::${frm.doc.job_type}::${frm.doc.job}`;
	if (frm._eligible_linked_services_key === cache_key) {
		if (callback) callback();
		return;
	}
	frappe.call({
		method: "logistics.pricing_center.doctype.change_request.change_request.get_eligible_internal_jobs_for_change_request_job",
		args: {
			job_type: frm.doc.job_type,
			job_name: frm.doc.job,
			change_request_name: frm.doc.name || null,
		},
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

const CR_SERVICES_API =
	"logistics.pricing_center.doctype.change_request.change_request";

/** Services tab is a read-only mirror; manage via toolbar Services dialog. */
function cr_setup_linked_services_grid(frm) {
	if (window.logistics && logistics.setup_virtual_linked_services_grid) {
		logistics.setup_virtual_linked_services_grid(frm);
		return;
	}
	if (!frm.get_docfield || !frm.get_docfield("linked_services")) return;
	frm.set_df_property("linked_services", "read_only", 1);
	frm.set_df_property("linked_services", "cannot_add_rows", 1);
	frm.set_df_property("linked_services", "cannot_delete_rows", 1);
}

function cr_can_manage_linked_services(frm) {
	return !!(frm && frm.doc && !frm.is_new() && frm.doc.docstatus === 0);
}

function cr_supports_services_tab(frm) {
	if (
		logistics.change_request_visibility &&
		typeof logistics.change_request_visibility.supports_services === "function"
	) {
		return logistics.change_request_visibility.supports_services(frm.doc.job_type);
	}
	return true;
}

function cr_open_services_dialog(frm) {
	function open() {
		if (!logistics.show_linked_services_dialog) {
			frappe.msgprint({
				message: __(
					"Services dialog failed to load. Hard-refresh the page (Ctrl+Shift+R)."
				),
				indicator: "orange",
			});
			return;
		}
		const can_manage = cr_can_manage_linked_services(frm);
		logistics.show_linked_services_dialog(frm, {
			listMethod: CR_SERVICES_API + ".list_change_request_linked_services",
			addMethod: can_manage ? CR_SERVICES_API + ".add_linked_service" : null,
			removeMethod: can_manage ? CR_SERVICES_API + ".remove_linked_service" : null,
			parentField: "change_request",
			parentLabel: __("Change Request"),
			allowAdd: can_manage,
			allowRemove: can_manage,
			allowEdit: can_manage,
			emptyHint: __(
				"Job services appear here automatically. Add a type only for a new extra leg."
			),
			addHint: __(
				"Add a service type only when the extra charge needs a new leg that is not already on the job. Existing job services can be picked on charge rows."
			),
			unsavedMessage: __("Save the Change Request before managing services."),
			removeConfirm: (ls) =>
				__("Remove linked service {0} from this change request?", [
					`<strong>${frappe.utils.escape_html(ls)}</strong>`,
				]),
		});
	}
	if (logistics.show_linked_services_dialog) {
		open();
		return;
	}
	frappe.require("/assets/logistics/js/linked_services_dialog.js", open);
}

function cr_setup_services_button(frm) {
	if (frm.is_new() || !cr_supports_services_tab(frm)) return;
	frm.add_custom_button(__("Services"), () => {
		cr_open_services_dialog(frm);
	});
}

frappe.ui.form.on("Change Request", {
	onload(frm) {
		frm.events.setup_item_code_query(frm);
		frm.events.setup_linked_service_query(frm);
		cr_setup_linked_services_grid(frm);
		cr_fetch_eligible_linked_services(frm);
		if (logistics.change_request_visibility && logistics.change_request_visibility.apply) {
			logistics.change_request_visibility.apply(frm);
		}
	},

	job_type(frm) {
		frm._eligible_linked_services_key = null;
		cr_fetch_eligible_linked_services(frm);
		if (logistics.change_request_visibility && logistics.change_request_visibility.apply) {
			logistics.change_request_visibility.apply(frm);
		}
	},

	job(frm) {
		frm._eligible_linked_services_key = null;
		cr_fetch_eligible_linked_services(frm);
		if (logistics.change_request_visibility && logistics.change_request_visibility.apply) {
			logistics.change_request_visibility.apply(frm);
		}
	},

	change_sections(frm) {
		if (logistics.change_request_visibility && logistics.change_request_visibility.apply) {
			logistics.change_request_visibility.apply(frm);
		}
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
				frappe.model.set_value(cdt, cdn, "charge_scope", "Linked");
				frappe.model.set_value(cdt, cdn, "linked_service", default_ls);
			} else {
				frappe.model.set_value(cdt, cdn, "charge_scope", "Main");
			}
		});
	},

	setup_linked_service_query(frm) {
		if (frm.fields_dict.charges && logistics.linked_service_link_query) {
			logistics.linked_service_link_query.setup(frm, {
				parentBookingType: "Change Request",
				chargeChildTable: "charges",
				chargeRowDoctype: "Change Request Charge",
			});
			return;
		}
		if (!frm.fields_dict.charges) return;
		frm.set_query("linked_service", "charges", function () {
			const eligible =
				(frm._eligible_linked_services && frm._eligible_linked_services.linked_services) || [];
			const names = eligible.map((r) => r.name).filter(Boolean);
			if (names.length) {
				return { filters: { name: ["in", names] } };
			}
			if (frm.doc.name) {
				return {
					filters: {
						parent_booking_type: "Change Request",
						parent_booking_name: frm.doc.name,
					},
				};
			}
			return { filters: { name: ["in", []] } };
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
		cr_setup_linked_services_grid(frm);
		cr_fetch_eligible_linked_services(frm);
		if (logistics.change_request_visibility && logistics.change_request_visibility.apply) {
			logistics.change_request_visibility.apply(frm);
		}
		if (logistics.change_request_summary && logistics.change_request_summary.render) {
			logistics.change_request_summary.render(frm);
		}
		cr_setup_services_button(frm);
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
