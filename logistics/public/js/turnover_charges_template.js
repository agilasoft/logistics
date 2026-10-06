// Turnover Shipment: pick a Turnover Charges Template and load its charge lines.
(function () {
	var PARENTS = {
		"Air Booking": { service: "Air", child: "Air Booking Charges" },
		"Air Shipment": { service: "Air", child: "Air Shipment Charges" },
		"Sea Booking": { service: "Sea", child: "Sea Booking Charges" },
		"Sea Shipment": { service: "Sea", child: "Sea Shipment Charges" },
	};

	function set_template_query(frm) {
		var spec = PARENTS[frm.doctype];
		if (!spec || !frm.fields_dict.turnover_charges_template) {
			return;
		}
		frm.set_query("turnover_charges_template", function () {
			return {
				filters: {
					service: spec.service,
					is_active: 1,
				},
			};
		});
	}

	function recalculate_charge_rows(frm, done) {
		var spec = PARENTS[frm.doctype];
		var charges = frm.doc.charges || [];
		if (!spec || !charges.length) {
			frm.refresh_field("charges");
			if (done) {
				done();
			}
			return;
		}
		var idx = 0;
		function run_next() {
			if (idx >= charges.length) {
				frm.refresh_field("charges");
				if (done) {
					done();
				}
				return;
			}
			var row = charges[idx];
			idx += 1;
			frappe.call({
				method: "logistics.utils.charges_calculation.calculate_charge_row",
				args: {
					doctype: spec.child,
					parenttype: frm.doctype,
					parent: frm.doc.name || "new",
					row_data: JSON.stringify(row),
					parent_overrides:
						window.logistics && logistics.charge_row_parent_overrides
							? logistics.charge_row_parent_overrides(frm)
							: null,
				},
				callback: function (r) {
					if (r.message && r.message.success && row.name) {
						["estimated_revenue", "estimated_cost", "quantity", "cost_quantity"].forEach(function (field) {
							if (r.message[field] != null) {
								frappe.model.set_value(spec.child, row.name, field, r.message[field]);
							}
						});
						if ("revenue_calc_notes" in r.message) {
							frappe.model.set_value(
								spec.child,
								row.name,
								"revenue_calc_notes",
								r.message.revenue_calc_notes || ""
							);
						}
						if ("cost_calc_notes" in r.message) {
							frappe.model.set_value(
								spec.child,
								row.name,
								"cost_calc_notes",
								r.message.cost_calc_notes || ""
							);
						}
					}
					run_next();
				},
				error: function () {
					run_next();
				},
			});
		}
		run_next();
	}

	function fetch_template_charges(frm) {
		if (frm.doc.docstatus) {
			return;
		}
		if (!frm.doc.turnover_charges_template) {
			frm.clear_table("charges");
			frm.refresh_field("charges");
			return;
		}
		frappe.call({
			method:
				"logistics.logistics.doctype.turnover_charges_template.turnover_charges_template.get_turnover_template_charge_rows",
			args: {
				template: frm.doc.turnover_charges_template,
				parent_doctype: frm.doctype,
			},
			freeze: true,
			freeze_message: __("Fetching charges from template"),
			callback: function (r) {
				if (!r || r.exc) {
					return;
				}
				frm.clear_table("charges");
				(r.message || []).forEach(function (row) {
					frm.add_child("charges", row);
				});
				frm.refresh_field("charges");
				recalculate_charge_rows(frm);
			},
		});
	}

	Object.keys(PARENTS).forEach(function (doctype) {
		frappe.ui.form.on(doctype, {
			refresh: function (frm) {
				set_template_query(frm);
			},
			is_turnover_shipment: function (frm) {
				if (frm.doc.docstatus) {
					return;
				}
				if (cint(frm.doc.is_turnover_shipment)) {
					set_template_query(frm);
					return;
				}
				if (frm.doc.turnover_charges_template) {
					frm._turnover_uncheck = true;
					frm.set_value("turnover_charges_template", "");
				}
			},
			turnover_charges_template: function (frm) {
				if (frm.doc.docstatus) {
					return;
				}
				if (frm._turnover_uncheck) {
					frm._turnover_uncheck = false;
					return;
				}
				fetch_template_charges(frm);
			},
		});
	});
})();
