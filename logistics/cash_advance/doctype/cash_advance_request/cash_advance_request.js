frappe.ui.form.on('Cash Advance Request', {
	refresh: function(frm) {
		logistics_cash_advance_set_fund_source_query(frm);
		logistics_cash_advance_set_employee_advance_query(frm);
		logistics_cash_advance_set_item_query(frm);

		frm.add_custom_button(__('Calculate'), function() {
			calculate_totals(frm);
		}, __('Actions'));

		if (frm.doc.items && frm.doc.items.length > 0) {
			calculate_totals(frm);
		}
	},

	company: function(frm) {
		logistics_cash_advance_set_fund_source_query(frm);
		logistics_cash_advance_set_employee_advance_query(frm);
	},

	job_number: function(frm) {
		logistics_cash_advance_apply_job_number_dimensions(frm).then(function() {
			logistics_cash_advance_set_item_query(frm);
			logistics_cash_advance_clear_invalid_items(frm);
		});
	},

	total_requested: function(frm) {
		calculate_totals(frm);
	},

	items: function(frm, cdt, cdn) {
		calculate_totals(frm);
	},

	items_remove: function(frm, cdt, cdn) {
		calculate_totals(frm);
	},

	calculate: function(frm) {
		calculate_totals(frm);
	}
});

function logistics_cash_advance_set_employee_advance_query(frm) {
	if (!frappe.model.can_read('Employee Advance')) {
		return;
	}
	if (!frm.doc.company) {
		return;
	}
	frm.set_query('employee_advance', function() {
		return {
			filters: { company: frm.doc.company }
		};
	});
}

function logistics_cash_advance_set_fund_source_query(frm) {
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

function logistics_cash_advance_set_item_query(frm) {
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

function logistics_cash_advance_apply_job_number_dimensions(frm) {
	if (!frm.doc.job_number) {
		return Promise.resolve();
	}
	return frappe.db.get_doc('Job Number', frm.doc.job_number).then(function(jn) {
		var chain = Promise.resolve();
		if (jn.company) {
			chain = chain.then(function() { return frm.set_value('company', jn.company); });
		}
		if (jn.branch) {
			chain = chain.then(function() { return frm.set_value('branch', jn.branch); });
		}
		if (jn.cost_center) {
			chain = chain.then(function() { return frm.set_value('cost_center', jn.cost_center); });
		}
		if (jn.profit_center) {
			chain = chain.then(function() { return frm.set_value('profit_center', jn.profit_center); });
		}
		return chain;
	});
}

function logistics_cash_advance_clear_invalid_items(frm) {
	if (!frm.doc.job_number || !frm.doc.items || !frm.doc.items.length) {
		return;
	}
	frappe.call({
		method: 'logistics.cash_advance.job_charge_items.get_charge_item_codes',
		args: { job_number: frm.doc.job_number },
		callback: function(r) {
			var allowed = r.message || [];
			var set = {};
			allowed.forEach(function(name) { set[name] = 1; });
			$.each(frm.doc.items || [], function(i, row) {
				if (row.item_code && !set[row.item_code]) {
					frappe.model.set_value(row.doctype, row.name, 'item_code', null);
				}
			});
			frm.refresh_field('items');
			calculate_totals(frm);
		}
	});
}

function calculate_totals(frm) {
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

frappe.ui.form.on('Cash Advance Request Item', {
	item_code: function(frm, cdt, cdn) {
		calculate_totals(frm);
	},

	amount_requested: function(frm, cdt, cdn) {
		calculate_totals(frm);
	},

	amount_liquidated: function(frm, cdt, cdn) {
		calculate_totals(frm);
	}
});
