// Copyright (c) 2026, www.agilasoft.com and contributors
// Sales Quote Charge - calculation events are in sales_quote.js (parent form)
// Weight Break / Qty Break handlers in charge_break_buttons.js
// Item Code filtering by Service Type is handled in sales_quote.js

/** Revenue side is editable when charge_type is not Cost or Disbursement (read_only_depends_on on revenue_calculation_method). */
function sales_quote_charge_needs_revenue_calculation_method(row) {
	if (!row) {
		return false;
	}
	const ct = row.charge_type;
	return ct && !["Cost", "Disbursement"].includes(ct);
}

frappe.provide("logistics.operational_exchange_rate");

function sales_quote_charge_fetch_bill_to_exchange_rate(frm, cdt, cdn) {
	logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate(frm, cdt, cdn, {
		source_field: "bill_to_exchange_rate_source",
		currency_field: "currency",
		rate_field: "bill_to_exchange_rate",
	});
}

function sales_quote_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn) {
	logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate(frm, cdt, cdn, {
		source_field: "pay_to_exchange_rate_source",
		currency_field: "cost_currency",
		rate_field: "pay_to_exchange_rate",
	});
}

function sales_quote_charge_sync_category_apply_95_5(frm, cdt, cdn) {
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

function sales_quote_sync_charges_category_apply_95_5(frm) {
	const rows = frm.doc.charges || [];
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
			frm.refresh_field("charges");
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

frappe.ui.form.on("Sales Quote Charge", {
	charge_category(frm, cdt, cdn) {
		sales_quote_charge_sync_category_apply_95_5(frm, cdt, cdn);
	},
	bill_to_exchange_rate_source(frm, cdt, cdn) {
		sales_quote_charge_fetch_bill_to_exchange_rate(frm, cdt, cdn);
	},
	currency(frm, cdt, cdn) {
		sales_quote_charge_fetch_bill_to_exchange_rate(frm, cdt, cdn);
	},
	pay_to_exchange_rate_source(frm, cdt, cdn) {
		sales_quote_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn);
	},
	cost_currency(frm, cdt, cdn) {
		sales_quote_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Sales Quote", {
	refresh(frm) {
		sales_quote_sync_charges_category_apply_95_5(frm);
	},
	date(frm) {
		logistics.operational_exchange_rate.refresh_sales_quote_charge_exchange_rates(frm);
	},
	validate(frm) {
		const charges = frm.doc.charges || [];
		for (const row of charges) {
			const method = (row.revenue_calculation_method || "").trim();
			if (sales_quote_charge_needs_revenue_calculation_method(row) && !method) {
				frappe.throw(
					__("Charges row {0}: Calculation Method is required for charge type \"{1}\".", [
						row.idx || "?",
						row.charge_type || "",
					])
				);
			}
		}
	},
});
