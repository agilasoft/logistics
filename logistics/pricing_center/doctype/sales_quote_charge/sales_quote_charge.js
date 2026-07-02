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

frappe.ui.form.on("Sales Quote Charge", {
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
