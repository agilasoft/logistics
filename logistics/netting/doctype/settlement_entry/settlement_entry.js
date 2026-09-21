// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Settlement Entry', {
	refresh: function(frm) {
		frm.clear_custom_buttons();

		if (frm.doc.company_currency && !frm.doc.settlement_currency) {
			frm.set_value('settlement_currency', frm.doc.company_currency);
		}
		if (frm.doc.settlement_currency && frm.doc.company_currency
			&& frm.doc.settlement_currency === frm.doc.company_currency
			&& flt(frm.doc.conversion_rate) !== 1) {
			frm.set_value('conversion_rate', 1);
		}

		if (frm.doc.settlement_group && frm.doc.company) {
			frm.add_custom_button(__('Get Outstanding Transactions'), function() {
				frappe.confirm(
					__('This will clear existing references and add all outstanding transactions. Continue?'),
					function() {
						if (frm.is_new()) {
							frm.save().then(function() {
								call_get_outstanding_transactions(frm);
							});
						} else {
							call_get_outstanding_transactions(frm);
						}
					},
					function() {}
				);
			}, __('Action'));
		} else {
			frm.add_custom_button(__('Get Outstanding Transactions'), function() {
				frappe.msgprint({
					message: __('Please select Settlement Group and Company first.'),
					indicator: 'orange',
					title: __('Information')
				});
			}, __('Action'));
		}
	},

	settlement_group: function(frm) {
		frm.refresh();
	},

	company: function(frm) {
		if (!frm.doc.company) {
			frm.refresh();
			return;
		}
		frappe.db.get_value('Company', frm.doc.company, 'default_currency', function(r) {
			if (!r) {
				frm.refresh();
				return;
			}
			frm.set_value('company_currency', r.default_currency);
			if (!frm.doc.settlement_currency) {
				frm.set_value('settlement_currency', r.default_currency);
			}
			set_conversion_rate(frm).then(function() {
				refresh_row_exchange_rates(frm);
			});
			frm.refresh();
		});
	},

	settlement_currency: function(frm) {
		set_conversion_rate(frm).then(function() {
			refresh_row_exchange_rates(frm);
		});
	},

	posting_date: function(frm) {
		set_conversion_rate(frm).then(function() {
			refresh_row_exchange_rates(frm);
		});
	},

	conversion_rate: function(frm) {
		recalculate_totals(frm);
	}
});

frappe.ui.form.on('Settlement Entry Transaction', {
	allocated_amount: function(frm, cdt, cdn) {
		recalculate_row(frm, cdt, cdn);
	},

	exchange_rate: function(frm, cdt, cdn) {
		recalculate_row(frm, cdt, cdn);
	},

	currency: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		fetch_row_exchange_rate(frm, row).then(function() {
			recalculate_row(frm, cdt, cdn);
		});
	}
});

function call_get_outstanding_transactions(frm) {
	if (!frm.doc.name || frm.is_new()) {
		frappe.msgprint({
			message: __('Please save the document first.'),
			indicator: 'orange',
			title: __('Information')
		});
		return;
	}

	frappe.call({
		method: 'logistics.netting.doctype.settlement_entry.settlement_entry.get_outstanding_transactions',
		args: {
			docname: frm.doc.name,
			clear_existing: 1
		},
		freeze: true,
		freeze_message: __('Fetching outstanding transactions...'),
		callback: function(r) {
			if (!r.exc) {
				if (r.message !== undefined && r.message !== null) {
					frappe.show_alert({
						message: __('{0} transactions added', [r.message || 0]),
						indicator: 'green'
					}, 5);
				}
				frm.reload_doc();
			}
		}
	});
}

function get_exchange_rate(from_currency, to_currency, transaction_date, args) {
	if (!from_currency || !to_currency || from_currency === to_currency) {
		return Promise.resolve(1);
	}
	return frappe.call({
		method: 'logistics.netting.doctype.settlement_entry.settlement_entry.get_settlement_exchange_rate',
		args: {
			from_currency: from_currency,
			to_currency: to_currency,
			transaction_date: transaction_date,
			args: args || null
		}
	}).then(function(r) {
		return flt(r.message) || 0;
	});
}

function set_conversion_rate(frm) {
	if (!frm.doc.settlement_currency || !frm.doc.company_currency) {
		return Promise.resolve();
	}
	if (frm.doc.settlement_currency === frm.doc.company_currency) {
		frm.set_value('conversion_rate', 1);
		return Promise.resolve();
	}
	return get_exchange_rate(
		frm.doc.settlement_currency,
		frm.doc.company_currency,
		frm.doc.posting_date
	).then(function(rate) {
		if (rate) {
			frm.set_value('conversion_rate', rate);
		}
	});
}

function fetch_row_exchange_rate(frm, row) {
	let from_currency = row.currency || frm.doc.settlement_currency;
	let args = row.party_type === 'Customer' ? 'for_selling' : 'for_buying';
	return get_exchange_rate(
		from_currency,
		frm.doc.settlement_currency,
		frm.doc.posting_date,
		args
	).then(function(rate) {
		if (rate) {
			frappe.model.set_value(row.doctype, row.name, 'exchange_rate', rate);
		}
	});
}

function refresh_row_exchange_rates(frm) {
	let rows = frm.doc.references || [];
	if (!rows.length) {
		recalculate_totals(frm);
		return;
	}
	let chain = Promise.resolve();
	rows.forEach(function(row) {
		chain = chain.then(function() {
			return fetch_row_exchange_rate(frm, row);
		});
	});
	chain.then(function() {
		recalculate_totals(frm);
	});
}

function recalculate_row(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let allocated_settlement = flt(row.allocated_amount) * flt(row.exchange_rate);
	frappe.model.set_value(cdt, cdn, 'allocated_amount_in_settlement_currency', allocated_settlement);

	let book = flt(row.allocated_amount) * flt(row.invoice_conversion_rate || 1);
	let settled_base = allocated_settlement * flt(frm.doc.conversion_rate || 1);
	let fx = settled_base - book;
	if (row.party_type === 'Supplier') {
		fx = book - settled_base;
	}
	frappe.model.set_value(cdt, cdn, 'exchange_gain_loss', fx);
	recalculate_totals(frm);
}

function recalculate_totals(frm) {
	let total_receivable = 0;
	let total_payable = 0;
	let total_fx = 0;
	(frm.doc.references || []).forEach(function(row) {
		if (!flt(row.allocated_amount)) {
			return;
		}
		let amount = flt(row.allocated_amount_in_settlement_currency);
		if (row.party_type === 'Customer') {
			total_receivable += amount;
		} else if (row.party_type === 'Supplier') {
			total_payable += amount;
		}
		total_fx += flt(row.exchange_gain_loss);
	});
	let conversion_rate = flt(frm.doc.conversion_rate) || 1;
	frm.set_value('total_receivable', total_receivable);
	frm.set_value('total_payable', total_payable);
	frm.set_value('net_amount', total_receivable - total_payable);
	frm.set_value('base_total_receivable', total_receivable * conversion_rate);
	frm.set_value('base_total_payable', total_payable * conversion_rate);
	frm.set_value('base_net_amount', (total_receivable - total_payable) * conversion_rate);
	frm.set_value('total_exchange_gain_loss', total_fx);
}
