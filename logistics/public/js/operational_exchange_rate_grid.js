// Clear Dynamic Link when Entity Type changes on Operational Exchange Rate child rows.
// When Source, Currency, and Date are set, load rate from Source Exchange Rate (server + whitelisted API).

frappe.provide('logistics.operational_exchange_rate');

logistics.operational_exchange_rate.fetch_rate = function (frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	if (!row || !row.exchange_rate_source || !row.currency || !row.exchange_rate_date) {
		return;
	}
	frappe.call({
		method: 'logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date',
		args: {
			exchange_rate_source: row.exchange_rate_source,
			currency: row.currency,
			as_of_date: row.exchange_rate_date,
		},
		callback: (r) => {
			if (r.message != null && r.message !== '') {
				frappe.model.set_value(cdt, cdn, 'rate', r.message);
				if (frm && frm.dirty) {
					frm.dirty();
				}
			}
		},
	});
};

logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate = function (
	frm,
	cdt,
	cdn,
	{ source_field, currency_field, rate_field, as_of_date }
) {
	const row = frappe.get_doc(cdt, cdn);
	if (!row || !frm || !frm.doc) {
		return;
	}
	const source = row[source_field];
	const currency = row[currency_field];
	const resolved_as_of_date = as_of_date || frm.doc.date;
	if (!currency || !resolved_as_of_date) {
		return;
	}
	if (!source) {
		return;
	}
	frappe.call({
		method: 'logistics.utils.operational_exchange_rates.get_charge_side_exchange_rate',
		args: {
			company: frm.doc.company,
			exchange_rate_source: source,
			currency,
			as_of_date: resolved_as_of_date,
		},
		callback: (r) => {
			const rate = r.message != null && r.message !== '' ? r.message : 0;
			frappe.model.set_value(cdt, cdn, rate_field, rate);
			frm.dirty();
		},
	});
};

logistics.operational_exchange_rate.refresh_sales_quote_charge_exchange_rates = function (frm) {
	if (!frm || !frm.doc) {
		return;
	}
	const charges = frm.doc.charges || [];
	for (const row of charges) {
		if (!row.name) {
			continue;
		}
		if (row.bill_to_exchange_rate_source && row.currency) {
			logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate(
				frm,
				'Sales Quote Charge',
				row.name,
				{
					source_field: 'bill_to_exchange_rate_source',
					currency_field: 'currency',
					rate_field: 'bill_to_exchange_rate',
				}
			);
		}
		if (row.pay_to_exchange_rate_source && row.cost_currency) {
			logistics.operational_exchange_rate.fetch_sales_quote_charge_side_rate(
				frm,
				'Sales Quote Charge',
				row.name,
				{
					source_field: 'pay_to_exchange_rate_source',
					currency_field: 'cost_currency',
					rate_field: 'pay_to_exchange_rate',
				}
			);
		}
	}
};

frappe.ui.form.on('Operational Exchange Rate', {
	entity_type(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, 'entity', null);
	},
	exchange_rate_source(frm, cdt, cdn) {
		logistics.operational_exchange_rate.fetch_rate(frm, cdt, cdn);
	},
	currency(frm, cdt, cdn) {
		logistics.operational_exchange_rate.fetch_rate(frm, cdt, cdn);
	},
	exchange_rate_date(frm, cdt, cdn) {
		logistics.operational_exchange_rate.fetch_rate(frm, cdt, cdn);
	},
});
