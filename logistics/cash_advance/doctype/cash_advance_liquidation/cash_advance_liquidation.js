frappe.ui.form.on('Cash Advance Liquidation', {
	refresh: function(frm) {
		logistics_cash_advance_liquidation_set_fund_source_query(frm);
		logistics_cash_advance_liquidation_set_item_query(frm);

		frm.add_custom_button(__('Calculate'), function() {
			calculate_liquidation_totals(frm);
		}, __('Actions'));

		frm.add_custom_button(__('Reload from Cash Advance'), function() {
			logistics_cash_advance_liquidation_pull_from_request(frm, false);
		}, __('Actions'));

		if (frm.doc.items && frm.doc.items.length > 0) {
			calculate_liquidation_totals(frm);
		}
	},

	company: function(frm) {
		logistics_cash_advance_liquidation_set_fund_source_query(frm);
	},

	cash_advance_request: function(frm) {
		logistics_cash_advance_liquidation_pull_from_request(frm, true);
	},

	total_requested: function(frm) {
		calculate_liquidation_totals(frm);
	},

	items: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	},

	items_remove: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	},

	calculate: function(frm) {
		calculate_liquidation_totals(frm);
	}
});

function logistics_cash_advance_liquidation_set_fund_source_query(frm) {
	if (!frm.doc.company) {
		return;
	}
	frm.set_query('fund_source', function() {
		return {
			filters: {
				company: frm.doc.company,
				is_group: 0,
				disabled: 0,
				account_type: ['in', ['Bank', 'Cash']]
			}
		};
	});
}

function logistics_cash_advance_liquidation_set_item_query(frm) {
	frm.set_query('item_code', 'items', function() {
		var job_number = frm.doc.job_number;
		if (!job_number) {
			return { filters: [['Item', 'name', '=', '__no_job_number__']] };
		}
		return {
			query: 'logistics.cash_advance.job_charge_items.item_query',
			filters: { job_number: job_number }
		};
	});
}

function logistics_cash_advance_liquidation_pull_from_request(frm, silent) {
	if (!frm.doc.cash_advance_request) {
		if (!silent) {
			frappe.msgprint(__('Select a Cash Advance Request first.'));
		}
		return;
	}
	return frappe.db.get_doc('Cash Advance Request', frm.doc.cash_advance_request).then(function(ca) {
		var p = Promise.resolve();
		p = p.then(function() { return frm.set_value('company', ca.company); });
		p = p.then(function() { return frm.set_value('branch', ca.branch); });
		p = p.then(function() { return frm.set_value('cost_center', ca.cost_center); });
		p = p.then(function() { return frm.set_value('profit_center', ca.profit_center); });
		p = p.then(function() { return frm.set_value('job_number', ca.job_number); });
		p = p.then(function() { return frm.set_value('fund_source', ca.fund_source); });
		p = p.then(function() { return frm.set_value('payee', ca.payee); });
		p = p.then(function() { return frm.set_value('payee_name', ca.payee_name); });
		p = p.then(function() { return frm.set_value('request_date', ca.date); });
		p = p.then(function() { return frm.set_value('liquidation_due_date', ca.liquidation_due_date); });
		p = p.then(function() { return frm.set_value('liquidation_date', ca.liquidation_date); });
		return p.then(function() {
			frm.clear_table('items');
			$.each(ca.items || [], function(i, r) {
				var row = frm.add_child('items');
				row.item_code = r.item_code;
				row.description = r.description;
				row.amount_requested = r.amount_requested;
				row.reference_no = r.reference_no;
				row.date = r.date;
				row.amount_liquidated = r.amount_liquidated;
				row.attachment = r.attachment;
				row.particulars = r.particulars;
			});
			frm.refresh_field('items');
			logistics_cash_advance_liquidation_set_fund_source_query(frm);
			logistics_cash_advance_liquidation_set_item_query(frm);
			calculate_liquidation_totals(frm);
		});
	});
}

function calculate_liquidation_totals(frm) {
	let total_requested = 0;
	let total_liquidated = 0;

	if (frm.doc.items && frm.doc.items.length > 0) {
		frm.doc.items.forEach(function(row) {
			if (row.amount_requested) {
				total_requested += parseFloat(row.amount_requested) || 0;
			}
			if (row.amount_liquidated) {
				total_liquidated += parseFloat(row.amount_liquidated) || 0;
			}
		});
	}

	frm.set_value('total_requested', total_requested);
	frm.set_value('total_liquidated', total_liquidated);
	frm.set_value('unliquidated', total_requested - total_liquidated);

	frm.refresh_field('total_requested');
	frm.refresh_field('total_liquidated');
	frm.refresh_field('unliquidated');
}

frappe.ui.form.on('Cash Advance Liquidation Item', {
	item_code: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	},

	amount_requested: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	},

	amount_liquidated: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	}
});
