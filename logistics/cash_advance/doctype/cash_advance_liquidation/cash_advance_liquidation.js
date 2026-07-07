frappe.ui.form.on('Cash Advance Liquidation', {
	refresh: function(frm) {
		logistics_cash_advance_liquidation_load_request_fund_type(frm).then(function() {
			logistics_cash_advance_liquidation_set_item_query(frm);
			logistics_cash_advance_liquidation_toggle_item_job_number(frm);
		});

		frm.add_custom_button(__('Reload from Cash Advance'), function() {
			logistics_cash_advance_liquidation_pull_from_request(frm, false);
		}, __('Actions'));

		if (frm.doc.items && frm.doc.items.length > 0) {
			calculate_liquidation_totals(frm);
		}
	},

	cash_advance_request: function(frm) {
		logistics_cash_advance_liquidation_pull_from_request(frm, true);
		logistics_cash_advance_liquidation_toggle_item_job_number(frm);
	},

	job_number: function(frm) {
		logistics_cash_advance_liquidation_sync_item_job_numbers(frm);
		logistics_cash_advance_liquidation_set_item_query(frm);
	},

	total_requested: function(frm) {
		calculate_liquidation_totals(frm);
	},

	items: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	},

	items_remove: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	}
});

function logistics_cash_advance_liquidation_load_request_fund_type(frm) {
	if (!frm.doc.cash_advance_request) {
		frm._cash_advance_request_fund_type = null;
		return Promise.resolve();
	}
	return frappe.db.get_value(
		'Cash Advance Request',
		frm.doc.cash_advance_request,
		'fund_type'
	).then(function(r) {
		frm._cash_advance_request_fund_type = (r && r.fund_type) || null;
	});
}

function logistics_cash_advance_liquidation_get_fund_type(frm) {
	return frm._cash_advance_request_fund_type || null;
}

function logistics_cash_advance_liquidation_resolve_item_job_number(frm, row) {
	if (logistics_cash_advance_liquidation_get_fund_type(frm) === 'Revolving Fund') {
		return row && row.job_number;
	}
	return frm.doc.job_number || (row && row.job_number);
}

function logistics_cash_advance_liquidation_toggle_item_job_number(frm) {
	var has_request = !!frm.doc.cash_advance_request;
	var revolving = logistics_cash_advance_liquidation_get_fund_type(frm) === 'Revolving Fund';
	frm.toggle_reqd('job_number', has_request && !revolving);
	frm.fields_dict.items.grid.update_docfield_property(
		'job_number', 'reqd', has_request ? 1 : 0
	);
	frm.fields_dict.items.grid.update_docfield_property(
		'job_number', 'hidden', has_request ? 0 : 1
	);
	frm.fields_dict.items.grid.update_docfield_property(
		'job_number', 'read_only', revolving ? 0 : 1
	);
	frm.refresh_field('items');
}

function logistics_cash_advance_liquidation_sync_item_job_numbers(frm) {
	if (logistics_cash_advance_liquidation_get_fund_type(frm) === 'Revolving Fund') {
		return;
	}
	if (!frm.doc.job_number || !frm.doc.items || !frm.doc.items.length) {
		return;
	}
	$.each(frm.doc.items, function(i, row) {
		frappe.model.set_value(row.doctype, row.name, 'job_number', frm.doc.job_number);
	});
}

function logistics_cash_advance_liquidation_set_item_query(frm) {
	frm.set_query('item_code', 'items', function(doc, cdt, cdn) {
		var row = locals[cdt][cdn];
		var job_number = logistics_cash_advance_liquidation_resolve_item_job_number(frm, row);
		if (!job_number) {
			return { filters: [['Item', 'name', '=', '__no_job_number__']] };
		}
		return {
			query: 'logistics.cash_advance.job_charge_items.item_query',
			filters: { job_number: job_number }
		};
	});
	frm.set_query('job_number', 'items', function() {
		if (!frm.doc.company) {
			return {};
		}
		return {
			filters: {
				company: frm.doc.company
			}
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
		frm._cash_advance_request_fund_type = ca.fund_type || null;
		var revolving = ca.fund_type === 'Revolving Fund';
		var p = Promise.resolve();
		p = p.then(function() { return frm.set_value('company', ca.company); });
		p = p.then(function() { return frm.set_value('branch', ca.branch); });
		p = p.then(function() { return frm.set_value('cost_center', ca.cost_center); });
		p = p.then(function() { return frm.set_value('profit_center', ca.profit_center); });
		p = p.then(function() { return frm.set_value('job_number', revolving ? null : ca.job_number); });
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
				row.job_number = revolving ? r.job_number : ca.job_number;
			});
			frm.refresh_field('items');
			logistics_cash_advance_liquidation_set_item_query(frm);
			logistics_cash_advance_liquidation_toggle_item_job_number(frm);
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

	job_number: function(frm, cdt, cdn) {
		logistics_cash_advance_liquidation_set_item_query(frm);
	},

	amount_requested: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	},

	amount_liquidated: function(frm, cdt, cdn) {
		calculate_liquidation_totals(frm);
	}
});
