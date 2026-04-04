// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

const SERVICE_TYPE_ITEM_FIELD_MAP = {
	Air: "custom_air_forwarding_charge",
	Sea: "custom_sea_forwarding_charge",
	Transport: "custom_land_transport_charge",
	Customs: "custom_customs_charge",
	Warehousing: "custom_warehousing_charge",
};

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
		if (row.service_type) {
			const item_field = SERVICE_TYPE_ITEM_FIELD_MAP[row.service_type];
			if (item_field) {
				frm.set_query("item_code", "charges", function () {
					return {
						filters: { disabled: 0, [item_field]: 1 },
					};
				});
			}
		}
		frm.refresh_field("charges");
	},

	item_code: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.service_type) {
			const item_field = SERVICE_TYPE_ITEM_FIELD_MAP[row.service_type];
			if (item_field) {
				frm.set_query("item_code", "charges", function () {
					return {
						filters: { disabled: 0, [item_field]: 1 },
					};
				});
			}
		}
	},

	charge_type: function (frm, cdt, cdn) {
		frm.refresh_field("charges");
		var row = locals[cdt] && locals[cdt][cdn];
		if (row && row.charge_type === "Disbursement") {
			_calculate_change_request_charge_row(frm, cdt, cdn);
		}
	},

	load_type: function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.service_type !== "Transport" || !row.load_type) return;
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

frappe.ui.form.on("Change Request", {
	charges_add: function (frm, cdt, cdn) {
		const job_to_service = {
			"Transport Job": "Transport",
			"Warehouse Job": "Warehousing",
			"Air Shipment": "Air",
			"Sea Shipment": "Sea",
			Declaration: "Customs",
			"Declaration Order": "Customs",
		};
		const st = job_to_service[frm.doc.job_type];
		if (st) {
			frappe.model.set_value(cdt, cdn, "service_type", st);
		}
	},
	refresh(frm) {
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
