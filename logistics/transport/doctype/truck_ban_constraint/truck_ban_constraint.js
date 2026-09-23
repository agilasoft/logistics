// Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Truck Ban Constraint", {
	constraint_type(frm) {
		_truck_ban_clear_hidden_type_data(frm);
	},
});

var _TRUCK_BAN_TYPE_CHILD_FIELDS = {
	"Area Ban": ["restricted_addresses"],
	"Route Ban": ["restricted_routes"],
	"Time-Based Ban": [],
	"Weight-Based Ban": [],
	"Vehicle Type Ban": ["restricted_vehicle_types"],
	"Plate Coding": ["plate_coding"],
};

var _TRUCK_BAN_OPTIONAL_VEHICLE_TYPES = {
	"Area Ban": 1,
	"Route Ban": 1,
	"Time-Based Ban": 1,
	"Plate Coding": 1,
};

function _truck_ban_clear_hidden_type_data(frm) {
	if (!frm.doc || frm.doc.__islocal === undefined) {
		return;
	}
	var ctype = frm.doc.constraint_type;
	if (!ctype) {
		return;
	}

	var keep = {};
	(_TRUCK_BAN_TYPE_CHILD_FIELDS[ctype] || []).forEach(function (f) {
		keep[f] = 1;
	});
	if (_TRUCK_BAN_OPTIONAL_VEHICLE_TYPES[ctype]) {
		keep.restricted_vehicle_types = 1;
	}

	var child_fields = [
		"restricted_addresses",
		"restricted_routes",
		"restricted_vehicle_types",
		"plate_coding",
	];
	var cleared = [];
	child_fields.forEach(function (fieldname) {
		if (keep[fieldname]) {
			return;
		}
		var rows = frm.doc[fieldname] || [];
		if (!rows.length) {
			return;
		}
		frm.clear_table(fieldname);
		frm.refresh_field(fieldname);
		cleared.push(__(frappe.meta.get_label(frm.doctype, fieldname) || fieldname));
	});

	if (ctype !== "Weight-Based Ban" && flt(frm.doc.min_vehicle_weight_restriction)) {
		frm.set_value("min_vehicle_weight_restriction", 0);
		cleared.push(__("Minimum Vehicle Weight (kg)"));
	}

	if (cleared.length) {
		frappe.show_alert({
			message: __("Cleared fields not used for {0}: {1}", [ctype, cleared.join(", ")]),
			indicator: "orange",
		});
	}
}
