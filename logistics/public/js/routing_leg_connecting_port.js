// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * When a new Routing Leg row is added, default its start port from the previous
 * leg's end port. The field stays editable — only empty values are filled.
 *
 * Booking/Shipment legs: previous discharge_port → new load_port
 * Sales Quote legs: previous destination → new origin
 */

(function () {
	if (window.__logistics_routing_leg_connecting_port_init) {
		return;
	}
	window.__logistics_routing_leg_connecting_port_init = true;

	const CONFIG = {
		"Air Booking Routing Leg": { start: "load_port", end: "discharge_port" },
		"Air Shipment Routing Leg": { start: "load_port", end: "discharge_port" },
		"Sea Booking Routing Leg": { start: "load_port", end: "discharge_port" },
		"Sea Shipment Routing Leg": { start: "load_port", end: "discharge_port" },
		"Sales Quote Routing Leg": { start: "origin", end: "destination" },
	};

	function strip(value) {
		if (value == null) {
			return "";
		}
		return String(value).trim();
	}

	/**
	 * Prefill connecting start port on a newly added routing leg row.
	 * No-op when there is no previous leg, previous end is empty, or start is already set.
	 */
	function apply_connecting_port_default(frm, cdt, cdn) {
		const fields = CONFIG[cdt];
		if (!fields || !frm || !frm.doc) {
			return;
		}

		const row = locals[cdt] && locals[cdt][cdn];
		if (!row) {
			return;
		}

		if (strip(row[fields.start])) {
			return;
		}

		const legs = (frm.doc.routing_legs || []).slice().sort((a, b) => (a.idx || 0) - (b.idx || 0));
		const pos = legs.findIndex((leg) => leg.name === cdn);
		if (pos <= 0) {
			return;
		}

		const prev_end = strip(legs[pos - 1][fields.end]);
		if (!prev_end) {
			return;
		}

		return frappe.model.set_value(cdt, cdn, fields.start, prev_end);
	}

	// Grid triggers ``routing_legs_add`` with the *child* doctype, so handlers must be
	// registered on each routing-leg child (parent-only handlers never run).
	Object.keys(CONFIG).forEach((cdt) => {
		frappe.ui.form.on(cdt, {
			routing_legs_add(frm, cdt, cdn) {
				return apply_connecting_port_default(frm, cdt, cdn);
			},
		});
	});

	// Expose for tests / reuse
	window.logistics_apply_routing_leg_connecting_port = apply_connecting_port_default;
})();
