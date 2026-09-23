// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.provide("logistics.operational_exchange_rate");

function mice_consolidation_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn) {
	logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate(frm, cdt, cdn, {
		source_field: "pay_to_exchange_rate_source",
		currency_field: "currency",
		rate_field: "pay_to_exchange_rate",
		as_of_date: frm.doc.start_date,
	});
}

function mice_consolidation_charge_refresh_exchange_rates(frm) {
	if (!frm || !frm.doc) {
		return;
	}
	const charges = frm.doc.consolidation_charges || [];
	for (const row of charges) {
		if (!row.name) {
			continue;
		}
		if (row.pay_to_exchange_rate_source && row.currency) {
			mice_consolidation_charge_fetch_pay_to_exchange_rate(
				frm,
				"MICE Project Consolidation Charges",
				row.name
			);
		}
	}
}

function mice_consolidation_charge_sync_category_apply_95_5(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row) {
		return;
	}
	if (!row.charge_category) {
		frappe.model.set_value(cdt, cdn, "category_apply_95_5_rule", 0);
		return;
	}
	frappe.db.get_value("Charge Category", row.charge_category, "apply_95_5_rule", (r) => {
		frappe.model.set_value(cdt, cdn, "category_apply_95_5_rule", cint(r && r.apply_95_5_rule));
	});
}

function _mice_consolidation_refresh_unit_rate_control(frm, cdt, cdn) {
	if (logistics.charge_type_cleanup && logistics.charge_type_cleanup.refresh_charge_row_field_controls) {
		logistics.charge_type_cleanup.refresh_charge_row_field_controls(
			frm, cdt, cdn, ["unit_rate"], "consolidation_charges"
		);
	}
}

function mice_consolidation_sync_charges_category_apply_95_5(frm) {
	const rows = frm.doc.consolidation_charges || [];
	if (!rows.length) {
		return;
	}
	const cats = [...new Set(rows.map((r) => r.charge_category).filter(Boolean))];
	const apply_map = (map) => {
		let changed = false;
		rows.forEach((r) => {
			const next = r.charge_category ? cint(map[r.charge_category]) : 0;
			if (cint(r.category_apply_95_5_rule) !== next) {
				r.category_apply_95_5_rule = next;
				changed = true;
			}
		});
		if (changed) {
			frm.refresh_field("consolidation_charges");
		}
	};
	if (!cats.length) {
		apply_map({});
		return;
	}
	frappe.db.get_list("Charge Category", {
		filters: { name: ["in", cats] },
		fields: ["name", "apply_95_5_rule"],
		limit: cats.length,
	}).then((list) => {
		const map = {};
		(list || []).forEach((d) => {
			map[d.name] = cint(d.apply_95_5_rule);
		});
		apply_map(map);
	});
}

frappe.ui.form.on("MICE Project Consolidation Charges", {
	form_render: function (frm, cdt, cdn) {
		mice_consolidation_charge_sync_category_apply_95_5(frm, cdt, cdn);
		_mice_consolidation_refresh_unit_rate_control(frm, cdt, cdn);
		_fetch_mice_consolidation_cost_tariff(frm, cdt, cdn);
	},
	charge_category: function (frm, cdt, cdn) {
		mice_consolidation_charge_sync_category_apply_95_5(frm, cdt, cdn);
	},
	pay_to_exchange_rate_source: function (frm, cdt, cdn) {
		mice_consolidation_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn);
	},
	pay_to_exchange_rate: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	currency: function (frm, cdt, cdn) {
		mice_consolidation_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn);
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	revenue_calculation_method: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	unit_rate: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	quantity: function (frm, cdt, cdn) {
		_maybe_resolve_mice_consolidation_unit_break_rate(frm, cdt, cdn, function () {
			_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
		});
	},
	cost_use_unit_breaks: function (frm, cdt, cdn) {
		_maybe_resolve_mice_consolidation_unit_break_rate(frm, cdt, cdn, function () {
			_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
		});
	},
	discount_percentage: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	surcharge_amount: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	allocation_percentage: function (frm, cdt, cdn) {
		_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
	},
	service_type: function (frm, cdt, cdn) {
		_mice_refresh_consolidation_item_code_link(frm, cdt, cdn);
		_fetch_mice_consolidation_cost_tariff(frm, cdt, cdn);
	},
	use_tariff_in_cost: function (frm, cdt, cdn) {
		_mice_consolidation_refresh_unit_rate_control(frm, cdt, cdn);
		_fetch_mice_consolidation_cost_tariff(frm, cdt, cdn);
	},
	cost_tariff: function (frm, cdt, cdn) {
		_fetch_mice_consolidation_cost_tariff(frm, cdt, cdn);
	},
	item_code: function (frm, cdt, cdn) {
		_fetch_mice_consolidation_cost_tariff(frm, cdt, cdn);
	},
});

frappe.ui.form.on("MICE Project", {
	refresh: function (frm) {
		mice_consolidation_sync_charges_category_apply_95_5(frm);
	},
	start_date: function (frm) {
		mice_consolidation_charge_refresh_exchange_rates(frm);
	},
});

/** Re-apply item_code Link query after service_type changes (grid row or expanded child form). */
function _mice_refresh_consolidation_item_code_link(frm, cdt, cdn) {
	const grid = frm.fields_dict.consolidation_charges && frm.fields_dict.consolidation_charges.grid;
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

var _MICE_CONSOLIDATION_CALC_METHODS = {
	"Per Unit": 1,
	"Fixed Amount": 1,
	"Flat Rate": 1,
	"Base Plus Additional": 1,
	"First Plus Additional": 1,
	Percentage: 1,
	"Location-based": 1,
	"Weight Break": 1,
	"Qty Break": 1,
	"Percentage Break": 1,
};

function _resolve_unit_break_tier(unit_breaks, quantity) {
	var qty = frappe.utils.flt(quantity);
	var rows = (unit_breaks || []).slice().sort(function (a, b) {
		return frappe.utils.flt(b.unit_break) - frappe.utils.flt(a.unit_break);
	});
	for (var i = 0; i < rows.length; i++) {
		if (qty >= frappe.utils.flt(rows[i].unit_break)) {
			return rows[i];
		}
	}
	if (!(unit_breaks || []).length) {
		return null;
	}
	return (unit_breaks || []).slice().sort(function (a, b) {
		return frappe.utils.flt(a.unit_break) - frappe.utils.flt(b.unit_break);
	})[0];
}

function _cache_mice_consolidation_unit_breaks(row, unit_breaks) {
	row.__cost_unit_breaks = unit_breaks || [];
}

function _apply_mice_consolidation_unit_break_rate(cdt, cdn, unit_breaks, fallback_rate, fallback_currency) {
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	_cache_mice_consolidation_unit_breaks(row, unit_breaks);
	var tier = _resolve_unit_break_tier(unit_breaks, row.quantity);
	if (tier) {
		frappe.model.set_value(cdt, cdn, "unit_rate", tier.unit_rate || 0);
		if (tier.currency) {
			frappe.model.set_value(cdt, cdn, "currency", tier.currency);
		}
		return;
	}
	if (fallback_rate != null) {
		frappe.model.set_value(cdt, cdn, "unit_rate", fallback_rate || 0);
	}
	if (fallback_currency) {
		frappe.model.set_value(cdt, cdn, "currency", fallback_currency);
	}
}

function _maybe_resolve_mice_consolidation_unit_break_rate(frm, cdt, cdn, done) {
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row || !row.cost_use_unit_breaks) {
		if (done) {
			done();
		}
		return;
	}

	if (row.__cost_unit_breaks && row.__cost_unit_breaks.length) {
		_apply_mice_consolidation_unit_break_rate(cdt, cdn, row.__cost_unit_breaks);
		if (done) {
			done();
		}
		return;
	}

	if (!row.name || String(row.name).indexOf("new") === 0) {
		if (done) {
			done();
		}
		return;
	}

	frappe.call({
		method: "logistics.pricing_center.doctype.charge_unit_break.charge_unit_break.get_unit_breaks",
		args: {
			reference_doctype: cdt,
			reference_no: row.name,
			record_type: "Cost",
		},
		callback: function (r) {
			var unit_breaks = (r.message && r.message.unit_breaks) || [];
			_apply_mice_consolidation_unit_break_rate(cdt, cdn, unit_breaks);
			if (done) {
				done();
			}
		},
	});
}

function _fetch_mice_consolidation_cost_tariff(frm, cdt, cdn) {
	if (!cdn) {
		return;
	}
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	if (!row.use_tariff_in_cost || !row.cost_tariff || !row.item_code) {
		return;
	}

	frappe.call({
		method:
			"logistics.mice.doctype.mice_project_consolidation_charges.mice_project_consolidation_charges.fetch_cost_tariff_rate",
		args: {
			tariff_name: row.cost_tariff,
			item_code: row.item_code,
			service_type: row.service_type,
		},
		callback: function (r) {
			var rate_data = r.message;
			if (!rate_data) {
				frappe.msgprint(
					__("No matching rate found for item {0} in tariff {1}", [
						row.item_code,
						row.cost_tariff,
					])
				);
				return;
			}

			var method = rate_data.calculation_method;
			if (method && _MICE_CONSOLIDATION_CALC_METHODS[method]) {
				frappe.model.set_value(cdt, cdn, "revenue_calculation_method", method);
			}
			if (rate_data.quantity != null) {
				frappe.model.set_value(cdt, cdn, "quantity", rate_data.quantity || 0);
			}
			if (rate_data.has_cost_unit_breaks) {
				frappe.model.set_value(cdt, cdn, "cost_use_unit_breaks", 1);
				_apply_mice_consolidation_unit_break_rate(
					cdt,
					cdn,
					rate_data.unit_breaks || [],
					rate_data.rate || 0,
					rate_data.currency
				);
			} else {
				_cache_mice_consolidation_unit_breaks(row, []);
				frappe.model.set_value(cdt, cdn, "unit_rate", rate_data.rate || 0);
				if (rate_data.currency) {
					frappe.model.set_value(cdt, cdn, "currency", rate_data.currency);
				}
			}
			var unit_type_df = frappe.meta.get_docfield(cdt, "unit_type");
			var unit_type_opts = (unit_type_df && unit_type_df.options
				? unit_type_df.options.split("\n")
				: []
			).filter(Boolean);
			if (
				rate_data.unit_type &&
				(!unit_type_opts.length || unit_type_opts.indexOf(rate_data.unit_type) >= 0)
			) {
				frappe.model.set_value(cdt, cdn, "unit_type", rate_data.unit_type);
			}
			var uom_df = frappe.meta.get_docfield(cdt, "unit_of_measure");
			if (rate_data.uom) {
				// Select fields gate on option membership; Link→UOM always accepts tariff UOM.
				if (uom_df && uom_df.fieldtype === "Select") {
					var uom_opts = (uom_df.options ? uom_df.options.split("\n") : []).filter(Boolean);
					if (uom_opts.length && uom_opts.indexOf(rate_data.uom) < 0) {
						rate_data.uom = null;
					}
				}
				if (rate_data.uom) {
					frappe.model.set_value(cdt, cdn, "unit_of_measure", rate_data.uom);
				}
			}

			_calculate_mice_consolidation_charge_row(frm, cdt, cdn);
		},
	});
}

function _calculate_mice_consolidation_charge_row(frm, cdt, cdn) {
	if (!cdn) {
		return;
	}
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}

	var rate = frappe.utils.flt(row.unit_rate);
	var qty = frappe.utils.flt(row.quantity);
	var base = 0;

	if (row.revenue_calculation_method === "Per Unit") {
		base = rate * qty;
	} else if (
		row.revenue_calculation_method === "Flat Rate" ||
		row.revenue_calculation_method === "Fixed Amount"
	) {
		base = rate;
	} else if (row.revenue_calculation_method === "Percentage") {
		base = qty ? rate * (qty * 0.01) : 0;
	} else {
		base = frappe.utils.flt(row.base_amount);
	}

	var discount = 0;
	if (row.discount_percentage && base) {
		discount = base * (frappe.utils.flt(row.discount_percentage) / 100.0);
	}

	var total =
		frappe.utils.flt(base) -
		frappe.utils.flt(discount) +
		frappe.utils.flt(row.surcharge_amount);

	var allocated = 0;
	var pct = frappe.utils.flt(row.allocation_percentage);
	if (pct > 0) {
		allocated = total * (pct / 100.0);
	}

	var fxRate = frappe.utils.flt(row.pay_to_exchange_rate);
	var baseTotal = fxRate > 0 ? total * fxRate : 0;

	frappe.model.set_value(cdt, cdn, "base_amount", base);
	frappe.model.set_value(cdt, cdn, "discount_amount", discount);
	frappe.model.set_value(cdt, cdn, "total_amount", total);
	frappe.model.set_value(cdt, cdn, "base_total_amount", baseTotal);
	frappe.model.set_value(cdt, cdn, "allocated_amount", allocated);

	if (frm && frm.refresh_field) {
		frm.refresh_field("consolidation_charges");
	}
}
