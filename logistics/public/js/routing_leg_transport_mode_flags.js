// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/** Sync hidden transport_mode_air / transport_mode_sea from linked Load Type or Transport Mode checkboxes (child routing legs). */

(function () {
	if (window.__logistics_routing_leg_mode_flags_init) {
		return;
	}
	window.__logistics_routing_leg_mode_flags_init = true;

	const ROUTING_LEG_CHILD_TYPES = [
		"Air Booking Routing Leg",
		"Sea Booking Routing Leg",
		"Air Shipment Routing Leg",
		"Sea Shipment Routing Leg",
	];

	function sync_row_mode_flags(cdt, cdn, mode) {
		if (!mode) {
			frappe.model.set_value(cdt, cdn, "transport_mode_air", 0);
			frappe.model.set_value(cdt, cdn, "transport_mode_sea", 0);
			return;
		}
		frappe.db.get_value("Load Type", mode, ["air", "sea"]).then((r) => {
			const m = r && r.message;
			const tmProm =
				m != null
					? Promise.resolve({ air: m.air ? 1 : 0, sea: m.sea ? 1 : 0 })
					: frappe.db.get_value("Transport Mode", mode, ["air", "sea"]).then((r2) => {
							const x = (r2 && r2.message) || {};
							return { air: x.air ? 1 : 0, sea: x.sea ? 1 : 0 };
					  });
			return tmProm.then(({ air, sea }) => {
				frappe.model.set_value(cdt, cdn, "transport_mode_air", air);
				frappe.model.set_value(cdt, cdn, "transport_mode_sea", sea);
			});
		});
	}

	ROUTING_LEG_CHILD_TYPES.forEach((cdt) => {
		frappe.ui.form.on(cdt, {
			mode(frm, cdt, cdn) {
				const d = locals[cdt][cdn];
				sync_row_mode_flags(cdt, cdn, d && d.mode);
			},
		});
	});

	const PARENTS = ["Air Booking", "Sea Booking", "Air Shipment", "Sea Shipment"];

	function sync_routing_legs_bulk(frm) {
		const grid = frm.fields_dict.routing_legs;
		if (!grid || !frm.doc.routing_legs || !frm.doc.routing_legs.length) {
			return;
		}
		const cdt = grid.df.options;
		const modes = [...new Set((frm.doc.routing_legs || []).map((r) => r.mode).filter(Boolean))];
		if (!modes.length) {
			(frm.doc.routing_legs || []).forEach((row) => {
				if (!row.name) {
					return;
				}
				frappe.model.set_value(cdt, row.name, "transport_mode_air", 0);
				frappe.model.set_value(cdt, row.name, "transport_mode_sea", 0);
			});
			frm.refresh_field("routing_legs");
			return;
		}
		frappe.call({
			method: "logistics.utils.transport_mode_flags.get_transport_mode_flags_bulk",
			args: { modes },
			callback(r) {
				const flag_map = r.message || {};
				(frm.doc.routing_legs || []).forEach((row) => {
					if (!row.name) {
						return;
					}
					const f = flag_map[row.mode] || { air: 0, sea: 0 };
					frappe.model.set_value(cdt, row.name, "transport_mode_air", f.air);
					frappe.model.set_value(cdt, row.name, "transport_mode_sea", f.sea);
				});
				frm.refresh_field("routing_legs");
			},
		});
	}

	PARENTS.forEach((dt) => {
		frappe.ui.form.on(dt, {
			refresh(frm) {
				sync_routing_legs_bulk(frm);
			},
		});
	});
})();
