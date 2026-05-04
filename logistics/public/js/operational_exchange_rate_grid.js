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
