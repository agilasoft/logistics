// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt
// Charge-line behaviour aligned with Sales Quote Charge.

frappe.provide("logistics.operational_exchange_rate");

function change_request_charge_fetch_bill_to_exchange_rate(frm, cdt, cdn) {
	if (!logistics.operational_exchange_rate || !logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate) {
		return;
	}
	logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate(frm, cdt, cdn, {
		source_field: "bill_to_exchange_rate_source",
		currency_field: "currency",
		rate_field: "bill_to_exchange_rate",
		as_of_date: (frm.doc && (frm.doc.booking_date || frm.doc.scheduled_date)) || frappe.datetime.get_today(),
	});
}

function change_request_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn) {
	if (!logistics.operational_exchange_rate || !logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate) {
		return;
	}
	logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate(frm, cdt, cdn, {
		source_field: "pay_to_exchange_rate_source",
		currency_field: "cost_currency",
		rate_field: "pay_to_exchange_rate",
		as_of_date: (frm.doc && (frm.doc.booking_date || frm.doc.scheduled_date)) || frappe.datetime.get_today(),
	});
}

function change_request_charge_sync_category_apply_95_5(frm, cdt, cdn) {
	const row = locals[cdt] && locals[cdt][cdn];
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

frappe.ui.form.on("Change Request Charge", {
	charge_category(frm, cdt, cdn) {
		change_request_charge_sync_category_apply_95_5(frm, cdt, cdn);
	},
	bill_to_exchange_rate_source(frm, cdt, cdn) {
		change_request_charge_fetch_bill_to_exchange_rate(frm, cdt, cdn);
	},
	currency(frm, cdt, cdn) {
		change_request_charge_fetch_bill_to_exchange_rate(frm, cdt, cdn);
	},
	pay_to_exchange_rate_source(frm, cdt, cdn) {
		change_request_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn);
	},
	cost_currency(frm, cdt, cdn) {
		change_request_charge_fetch_pay_to_exchange_rate(frm, cdt, cdn);
	},
});
