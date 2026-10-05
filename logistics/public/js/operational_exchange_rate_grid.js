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

const EXCHANGE_RATE_OVERRIDE_SIDES = [
	{ source_field: 'bill_to_exchange_rate_source', flag_field: 'bill_to_allow_rate_override' },
	{ source_field: 'pay_to_exchange_rate_source', flag_field: 'pay_to_allow_rate_override' },
	{ source_field: 'exchange_rate_source', flag_field: 'allow_rate_override' },
];

logistics.operational_exchange_rate.sync_allow_rate_override_flag = function (cdt, cdn, source_field, flag_field) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row || !frappe.meta.has_field(cdt, flag_field)) {
		return;
	}
	const source = row[source_field];
	if (!source) {
		frappe.model.set_value(cdt, cdn, flag_field, 0);
		return;
	}
	frappe.db.get_value('Exchange Rate Source', source, 'allow_rate_override', (r) => {
		frappe.model.set_value(cdt, cdn, flag_field, cint(r && r.allow_rate_override));
	});
};

logistics.operational_exchange_rate.refresh_allow_rate_override_flags = function (frm) {
	if (!frm || !frm.doc || !frm.meta) {
		return;
	}
	const pending = [];
	const grids = [];
	let changed = false;
	(frm.meta.fields || []).forEach((df) => {
		if (df.fieldtype !== 'Table' || !df.options) {
			return;
		}
		const rows = frm.doc[df.fieldname] || [];
		let used = false;
		rows.forEach((row) => {
			EXCHANGE_RATE_OVERRIDE_SIDES.forEach((side) => {
				if (!frappe.meta.has_field(df.options, side.source_field)) {
					return;
				}
				if (!frappe.meta.has_field(df.options, side.flag_field)) {
					return;
				}
				used = true;
				const source = row[side.source_field];
				if (!source) {
					if (cint(row[side.flag_field])) {
						row[side.flag_field] = 0;
						changed = true;
					}
					return;
				}
				pending.push({ row, source, flag_field: side.flag_field });
			});
		});
		if (used) {
			grids.push(df.fieldname);
		}
	});
	const refresh_grids = () => {
		grids.forEach((fieldname) => frm.refresh_field(fieldname));
	};
	const sources = [...new Set(pending.map((item) => item.source))];
	if (!sources.length) {
		if (changed) {
			refresh_grids();
		}
		return;
	}
	frappe.db.get_list('Exchange Rate Source', {
		filters: { name: ['in', sources] },
		fields: ['name', 'allow_rate_override'],
		limit: sources.length,
	}).then((list) => {
		const map = {};
		(list || []).forEach((doc) => {
			map[doc.name] = cint(doc.allow_rate_override);
		});
		pending.forEach((item) => {
			const next = cint(map[item.source]);
			if (cint(item.row[item.flag_field]) !== next) {
				item.row[item.flag_field] = next;
				changed = true;
			}
		});
		if (changed) {
			refresh_grids();
		}
	});
};

if (!logistics.operational_exchange_rate._allow_override_bound) {
	logistics.operational_exchange_rate._allow_override_bound = true;
	[
		'Time Sensitive Case',
		'Sales Quote',
		'Air Booking',
		'Air Shipment',
		'Sea Booking',
		'Sea Shipment',
		'Project Job',
		'MICE Project',
		'Tariff',
		'Special Project',
		'Project Order',
		'Exhibit Order',
		'MICE Order',
		'Docket',
	].forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				logistics.operational_exchange_rate.refresh_allow_rate_override_flags(frm);
			},
		});
	});
	[
		'Sales Quote Charge',
		'Tariff Charge',
		'Air Booking Charges',
		'Air Shipment Charges',
		'Sea Booking Charges',
		'Sea Shipment Charges',
		'Special Project Charges',
		'Time Sensitive Case Charge',
		'MICE Project Charges',
		'Exhibit Charges',
		'MICE Project Consolidation Charges',
		'Operational Exchange Rate',
	].forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			bill_to_exchange_rate_source(frm, cdt, cdn) {
				logistics.operational_exchange_rate.sync_allow_rate_override_flag(
					cdt,
					cdn,
					'bill_to_exchange_rate_source',
					'bill_to_allow_rate_override'
				);
			},
			pay_to_exchange_rate_source(frm, cdt, cdn) {
				logistics.operational_exchange_rate.sync_allow_rate_override_flag(
					cdt,
					cdn,
					'pay_to_exchange_rate_source',
					'pay_to_allow_rate_override'
				);
			},
			exchange_rate_source(frm, cdt, cdn) {
				logistics.operational_exchange_rate.sync_allow_rate_override_flag(
					cdt,
					cdn,
					'exchange_rate_source',
					'allow_rate_override'
				);
			},
		});
	});
}

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
