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

	/** Debounced draft save so mode + flags persist without closing the grid row (avoids ``frm.save()`` → ``close_grid_form``). */
	const ROUTING_MODE_AUTOSAVE_MS = 600;

	function schedule_autosave_parent_after_routing_mode_change(frm) {
		if (!frm || !frm.doc) {
			return;
		}
		if (cint(frm.doc.docstatus) !== 0) {
			return;
		}
		if (frm.read_only) {
			return;
		}
		clearTimeout(frm._logistics_routing_mode_autosave_t);
		frm._logistics_routing_mode_autosave_t = setTimeout(() => {
			delete frm._logistics_routing_mode_autosave_t;
			if (!frm.doc || cint(frm.doc.docstatus) !== 0) {
				return;
			}
			// Defer if a normal form save is in progress (same semantics as ``savedocs`` queue).
			if (frappe.ui.form.is_saving) {
				schedule_autosave_parent_after_routing_mode_change(frm);
				return;
			}
			// Mode + hidden flags were just synced; persist even if ``is_dirty`` is false in edge cases.
			if (frm.dirty) {
				frm.dirty();
			}
			// Use ``savedocs`` path (not ``frappe.client.save``) so child rows match Desk Save.
			frappe.call({
				method: "logistics.utils.transport_mode_flags.save_parent_with_routing_quiet",
				args: { doc: frm.doc, action: "Save" },
				freeze: false,
				silent: true,
				callback(r) {
					if (r.exc) {
						let detail = "";
						try {
							const sm = r._server_messages && JSON.parse(r._server_messages);
							if (Array.isArray(sm) && sm.length) {
								detail = sm.filter(Boolean).join(" ");
							}
						} catch (e) {
							// ignore
						}
						frappe.msgprint({
							title: __("Could not save"),
							indicator: "red",
							message:
								detail ||
								__(
									"Routing mode change could not be saved. Please save the document manually."
								),
						});
						return;
					}
					if (frm.doc) {
						frm.doc.__unsaved = 0;
					}
					frm.$wrapper && frm.$wrapper.trigger("save_complete");
				},
			});
		}, ROUTING_MODE_AUTOSAVE_MS);
	}

	/**
	 * Sync air/sea flags for one routing leg row.
	 * Returns a Promise so the Desk ``mode`` field pipeline waits before ``df.change`` runs
	 * ``refresh_dependency()`` — otherwise the row still had old flags while ``mode`` was already new,
	 * and Flight/Vessel ``depends_on`` stayed wrong until a manual save/refresh.
	 */
	function sync_row_mode_flags(frm, cdt, cdn, mode) {
		function after_flags(promise) {
			return Promise.resolve(promise).then(() => {
				refresh_routing_leg_row_ui(frm, cdt, cdn);
				schedule_autosave_parent_after_routing_mode_change(frm);
			});
		}

		if (!mode) {
			return after_flags(
				frappe.model.set_value(cdt, cdn, { transport_mode_air: 0, transport_mode_sea: 0 })
			);
		}
		// Use server-side resolution (same as validate): client ``get_value`` returns ``{}`` when no row
		// exists, which is truthy and incorrectly skipped the Transport Mode fallback.
		return new Promise((resolve) => {
			frappe.call({
				method: "logistics.utils.transport_mode_flags.get_transport_mode_flags_bulk",
				args: { modes: [mode] },
				callback(r) {
					const f = (r.message && r.message[mode]) || { air: 0, sea: 0 };
					after_flags(
						frappe.model.set_value(cdt, cdn, {
							transport_mode_air: f.air,
							transport_mode_sea: f.sea,
						})
					).then(resolve, resolve);
				},
				// Unblock the field pipeline if the request fails (flags stay until next successful change or save).
				error: resolve,
			});
		});
	}

	/** Re-run grid row form layout so ``depends_on`` (vessel vs flight) matches updated flags. */
	function refresh_open_routing_leg_grid_form_if_matches(frm, cdt, cdn) {
		const grid = frm.fields_dict.routing_legs;
		if (!grid || !grid.open_grid_row || !grid.open_grid_row.layout || !grid.open_grid_row.row) {
			return;
		}
		const open_doc = grid.open_grid_row.row.doc;
		if (!open_doc || open_doc.doctype !== cdt || open_doc.name !== cdn) {
			return;
		}
		const doc = locals[cdt] && locals[cdt][cdn];
		if (doc) {
			grid.open_grid_row.layout.refresh(doc);
		}
	}

	/** Expanded grid form + inline row: re-evaluate ``depends_on`` without saving the parent. */
	function refresh_routing_leg_row_ui(frm, cdt, cdn) {
		refresh_open_routing_leg_grid_form_if_matches(frm, cdt, cdn);
		const grid = frm.fields_dict.routing_legs;
		if (grid && grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn]) {
			grid.grid_rows_by_docname[cdn].refresh_dependency();
		}
	}

	/** After bulk flag sync, refresh expanded routing row so Flight/Vessel ``depends_on`` updates. */
	function refresh_open_routing_leg_after_flag_sync(frm, cdt) {
		const grid = frm.fields_dict.routing_legs;
		if (!grid?.open_grid_row?.row?.doc) {
			return;
		}
		const d = grid.open_grid_row.row.doc;
		if (d.doctype !== cdt || !ROUTING_LEG_CHILD_TYPES.includes(d.doctype)) {
			return;
		}
		refresh_routing_leg_row_ui(frm, d.doctype, d.name);
	}

	ROUTING_LEG_CHILD_TYPES.forEach((cdt) => {
		frappe.ui.form.on(cdt, {
			mode(frm, cdt, cdn) {
				const d = locals[cdt][cdn];
				return sync_row_mode_flags(frm, cdt, cdn, d && d.mode);
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
			const rows = (frm.doc.routing_legs || []).filter((r) => r.name);
			Promise.all(
				rows.map((row) =>
					frappe.model.set_value(cdt, row.name, { transport_mode_air: 0, transport_mode_sea: 0 })
				)
			).then(() => {
				refresh_open_routing_leg_after_flag_sync(frm, cdt);
			});
			return;
		}
		frappe.call({
			method: "logistics.utils.transport_mode_flags.get_transport_mode_flags_bulk",
			args: { modes },
			callback(r) {
				const flag_map = r.message || {};
				const rows = (frm.doc.routing_legs || []).filter((row) => row.name);
				Promise.all(
					rows.map((row) => {
						const f = flag_map[row.mode] || { air: 0, sea: 0 };
						return frappe.model.set_value(cdt, row.name, {
							transport_mode_air: f.air,
							transport_mode_sea: f.sea,
						});
					})
				).then(() => {
					// Do not ``frm.refresh_field("routing_legs")`` here: it rebuilds the grid and can drop the
					// expanded row layout before ``depends_on`` (Flight / Vessel) re-evaluates from the flags above.
					refresh_open_routing_leg_after_flag_sync(frm, cdt);
				});
			},
		});
	}

	PARENTS.forEach((dt) => {
		frappe.ui.form.on(dt, {
			refresh(frm) {
				sync_routing_legs_bulk(frm);
			},
			routing_legs_on_form_rendered(frm) {
				const grid = frm.fields_dict.routing_legs;
				if (!grid || !grid.open_grid_row || !grid.open_grid_row.row) {
					return;
				}
				const d = grid.open_grid_row.row.doc;
				if (!d || !ROUTING_LEG_CHILD_TYPES.includes(d.doctype)) {
					return;
				}
				return sync_row_mode_flags(frm, d.doctype, d.name, d.mode);
			},
			routing_legs_add(frm, cdt, cdn) {
				if (!ROUTING_LEG_CHILD_TYPES.includes(cdt)) {
					return;
				}
				const row = locals[cdt] && locals[cdt][cdn];
				return sync_row_mode_flags(frm, cdt, cdn, row && row.mode);
			},
		});
	});
})();
