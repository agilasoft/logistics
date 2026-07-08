// Copyright (c) 2026, Agilasoft and contributors

function load_vehicle_types_for_load_type(frm, load_type, callback) {
	if (!load_type) {
		if (callback) callback([]);
		return;
	}
	if (!frm._vehicle_types_by_load_type) {
		frm._vehicle_types_by_load_type = {};
	}
	if (frm._vehicle_types_by_load_type[load_type]) {
		if (callback) callback(frm._vehicle_types_by_load_type[load_type]);
		return;
	}
	if (!frm._loading_vehicle_types) {
		frm._loading_vehicle_types = {};
	}
	if (!frm._vehicle_type_load_callbacks) {
		frm._vehicle_type_load_callbacks = {};
	}
	if (!frm._vehicle_type_load_callbacks[load_type]) {
		frm._vehicle_type_load_callbacks[load_type] = [];
	}
	if (callback) {
		frm._vehicle_type_load_callbacks[load_type].push(callback);
	}
	if (frm._loading_vehicle_types[load_type]) {
		return;
	}
	frm._loading_vehicle_types[load_type] = true;
	frappe.call({
		method: "logistics.pricing_center.doctype.sales_quote.sales_quote.get_vehicle_types_for_load_type",
		args: { load_type },
		callback(r) {
			if (!frm._vehicle_types_by_load_type) {
				frm._vehicle_types_by_load_type = {};
			}
			const names = (r.message && r.message.vehicle_types) || [];
			frm._vehicle_types_by_load_type[load_type] = names;
			if (frm._loading_vehicle_types) {
				delete frm._loading_vehicle_types[load_type];
			}
			const pending = (frm._vehicle_type_load_callbacks &&
				frm._vehicle_type_load_callbacks[load_type]) || [];
			if (frm._vehicle_type_load_callbacks) {
				delete frm._vehicle_type_load_callbacks[load_type];
			}
			pending.forEach((cb) => cb(names));
		},
	});
}

function get_default_vehicle_type_filters(frm) {
	const load_type = frm.doc.default_load_type;
	if (!load_type) {
		return { filters: { is_active: 1 } };
	}
	// Resolve allowed names via API; never filter Vehicle Type by load_type
	// (that field is on the child table and fails field permission checks).
	const names =
		frm._vehicle_types_by_load_type && frm._vehicle_types_by_load_type[load_type];
	if (names) {
		return {
			filters: {
				is_active: 1,
				name: ["in", names.length ? names : ["__none__"]],
			},
		};
	}
	load_vehicle_types_for_load_type(frm, load_type, () => {
		frm.refresh_field("default_vehicle_type");
	});
	return {
		filters: {
			is_active: 1,
			name: ["in", ["__none__"]],
		},
	};
}

function sync_default_vehicle_type_for_load_type(frm) {
	const load_type = frm.doc.default_load_type;
	const previous = frm.doc.default_vehicle_type;

	if (!load_type) {
		frm.refresh_field("default_vehicle_type");
		return;
	}

	load_vehicle_types_for_load_type(frm, load_type, (names) => {
		if (previous && !(names && names.includes(previous))) {
			frm.set_value("default_vehicle_type", null);
		}
		frm.refresh_field("default_vehicle_type");
	});
}

frappe.ui.form.on("Transport Template", {
	refresh(frm) {
		// Table MultiSelect does not apply link_filters from the child Link field.
		frm.set_query("allowed_load_types", () => ({
			filters: {
				is_active: 1,
				transport: 1,
			},
		}));

		frm.set_query("default_load_type", () => {
			const allowed = (frm.doc.allowed_load_types || [])
				.map((row) => row.load_type)
				.filter(Boolean);
			if (!allowed.length) {
				return {
					filters: { is_active: 1, transport: 1 },
				};
			}
			return {
				filters: {
					name: ["in", allowed],
					is_active: 1,
					transport: 1,
				},
			};
		});

		frm.set_query("default_vehicle_type", () => get_default_vehicle_type_filters(frm));

		if (frm.doc.default_load_type) {
			load_vehicle_types_for_load_type(frm, frm.doc.default_load_type, () => {
				frm.refresh_field("default_vehicle_type");
			});
		}
	},

	default_load_type(frm) {
		sync_default_vehicle_type_for_load_type(frm);
	},


	legs_add(frm) {
		frm.trigger("suggest_allowed_load_types");
	},

	suggest_allowed_load_types(frm) {
		const legs = frm.doc.legs || [];
		if (!legs.length) {
			return;
		}

		frappe.call({
			method: "logistics.transport.doctype.transport_template.transport_template.suggest_load_types_for_template_legs",
			args: { legs_json: legs },
			callback(r) {
				const suggested = (r.message && r.message.suggested_load_types) || [];
				if (!suggested.length) {
					return;
				}

				const existing = new Set(
					(frm.doc.allowed_load_types || []).map((row) => row.load_type).filter(Boolean)
				);
				let added = false;
				suggested.forEach((load_type) => {
					if (existing.has(load_type)) {
						return;
					}
					const row = frm.add_child("allowed_load_types");
					row.load_type = load_type;
					existing.add(load_type);
					added = true;
				});

				if (added) {
					frm.refresh_field("allowed_load_types");
				}

				if (!frm.doc.default_load_type && suggested.length === 1) {
					frm.set_value("default_load_type", suggested[0]);
				} else if (
					frm.doc.default_load_type &&
					!suggested.includes(frm.doc.default_load_type)
				) {
					frm.set_value("default_load_type", suggested.length === 1 ? suggested[0] : null);
				}
			},
		});
	},
});

frappe.ui.form.on("Transport Template Leg", {
	facility_type_from(frm) {
		frm.trigger("suggest_allowed_load_types");
	},
	facility_type_to(frm) {
		frm.trigger("suggest_allowed_load_types");
	},
});
