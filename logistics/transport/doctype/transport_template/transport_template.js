// Copyright (c) 2026, Agilasoft and contributors

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

		frm.set_query("default_vehicle_type", () => {
			const load_type = frm.doc.default_load_type;
			if (!load_type) {
				return { filters: { is_active: 1 } };
			}
			return {
				query: "logistics.pricing_center.doctype.sales_quote.sales_quote.get_vehicle_types_for_load_type",
				filters: { load_type },
			};
		});
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
