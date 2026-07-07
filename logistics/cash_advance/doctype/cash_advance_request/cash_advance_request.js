frappe.ui.form.on('Cash Advance Request', {
	refresh: function(frm) {
		logistics_cash_advance_set_fund_source_query(frm);
		logistics_cash_advance_set_employee_advance_query(frm);
		logistics_cash_advance_set_dimension_queries(frm);
		logistics_cash_advance_set_item_query(frm);
		logistics_cash_advance_toggle_item_job_number(frm);

		if (
			!frm.is_new() &&
			!frm.doc.__islocal &&
			frm.doc.docstatus === 1 &&
			flt(frm.doc.unliquidated) > 0 &&
			frm.has_perm('write')
		) {
			frm.add_custom_button(__('Extend Due Date'), function() {
				logistics_cash_advance_extend_due_date(frm);
			}, __('Actions'));
		}

		if (frm.doc.items && frm.doc.items.length > 0) {
			calculate_totals(frm);
		}
	},

	company: function(frm) {
		logistics_cash_advance_set_fund_source_query(frm);
		logistics_cash_advance_set_employee_advance_query(frm);
		logistics_cash_advance_set_dimension_queries(frm);
		logistics_cash_advance_clear_mismatched_dimensions(frm);
	},

	fund_source: function(frm) {
		if (!frm.doc.fund_source) {
			frm.set_value('fund_type', null);
			return;
		}
		frappe.db.get_value('Account', frm.doc.fund_source, ['fund_type', 'cash_advance_request_limit'], function(r) {
			if (r) {
				frm.set_value('fund_type', r.fund_type || null);
			}
		});
		logistics_cash_advance_set_item_query(frm);
	},

	fund_type: function(frm) {
		logistics_cash_advance_toggle_item_job_number(frm);
		logistics_cash_advance_set_item_query(frm);
		logistics_cash_advance_clear_invalid_items(frm);
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

function logistics_cash_advance_set_dimension_queries(frm) {
	if (!frm.doc.company) {
		return;
	}
	var pc_meta = frappe.get_meta('Profit Center');
	if (!pc_meta.has_field('company') && pc_meta.has_field('custom_company')) {
		frm.set_query('profit_center', function() {
			return {
				filters: { custom_company: frm.doc.company }
			};
		});
	}
}

function logistics_cash_advance_clear_mismatched_dimensions(frm) {
	if (!frm.doc.company) {
		return;
	}
	var company = frm.doc.company;

	if (frm.doc.cost_center) {
		frappe.db.get_value('Cost Center', frm.doc.cost_center, 'company', function(r) {
			if (r && r.company && r.company !== company) {
				frm.set_value('cost_center', null);
			}
		});
	}

	var pc_meta = frappe.get_meta('Profit Center');
	var pc_company_fn = pc_meta.has_field('company') ? 'company'
		: (pc_meta.has_field('custom_company') ? 'custom_company' : null);
	if (pc_company_fn && frm.doc.profit_center) {
		frappe.db.get_value('Profit Center', frm.doc.profit_center, pc_company_fn, function(r) {
			var pc_company = r && r[pc_company_fn];
			if (pc_company && pc_company !== company) {
				frm.set_value('profit_center', null);
			}
		});
	}

	if (frm.doc.fund_source) {
		frappe.db.get_value('Account', frm.doc.fund_source, 'company', function(r) {
			if (r && r.company && r.company !== company) {
				frm.set_value('fund_source', null);
				frm.set_value('fund_type', null);
			}
		});
	}
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
				account_type: ['in', ['Bank', 'Cash']],
				fund_type: ['in', ['Bank', 'Petty Cash', 'Revolving Fund']]
			}
		};
	});
}

function logistics_cash_advance_toggle_item_job_number(frm) {
	var revolving = frm.doc.fund_type === 'Revolving Fund';
	frm.fields_dict.items.grid.update_docfield_property(
		'job_number', 'reqd', revolving ? 1 : 0
	);
	frm.fields_dict.items.grid.update_docfield_property(
		'job_number', 'hidden', revolving ? 0 : 1
	);
	frm.refresh_field('items');
}

function logistics_cash_advance_header_job_number_required(frm) {
	return frm.doc.fund_type && frm.doc.fund_type !== 'Revolving Fund';
}

function logistics_cash_advance_row_job_number_required(frm) {
	return frm.doc.fund_type === 'Revolving Fund';
}

function logistics_cash_advance_item_job_number_required(frm, row) {
	if (logistics_cash_advance_row_job_number_required(frm)) {
		return true;
	}
	return logistics_cash_advance_header_job_number_required(frm);
}

function logistics_cash_advance_no_charge_items_filter() {
	return { filters: [['Item', 'name', '=', '__no_job_number__']] };
}

function logistics_cash_advance_resolve_item_job_number(frm, row) {
	if (frm.doc.fund_type === 'Revolving Fund') {
		return row && row.job_number;
	}
	return frm.doc.job_number;
}

function logistics_cash_advance_set_item_query(frm) {
	frm.set_query('item_code', 'items', function(doc, cdt, cdn) {
		var row = locals[cdt][cdn];
		var job_number = logistics_cash_advance_resolve_item_job_number(frm, row);
		if (!job_number) {
			if (logistics_cash_advance_item_job_number_required(frm, row)) {
				return logistics_cash_advance_no_charge_items_filter();
			}
			return {};
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
	if (!frm.doc.items || !frm.doc.items.length) {
		return;
	}
	if (logistics_cash_advance_row_job_number_required(frm)) {
		var tasks = [];
		$.each(frm.doc.items || [], function(i, row) {
			if (!row.job_number) {
				if (row.item_code) {
					frappe.model.set_value(row.doctype, row.name, 'item_code', null);
				}
				return;
			}
			if (!row.item_code) {
				return;
			}
			tasks.push(new Promise(function(resolve) {
				frappe.call({
					method: 'logistics.cash_advance.job_charge_items.get_charge_item_codes',
					args: { job_number: row.job_number },
					callback: function(r) {
						var allowed = r.message || [];
						if (row.item_code && allowed.indexOf(row.item_code) === -1) {
							frappe.model.set_value(row.doctype, row.name, 'item_code', null);
						}
						resolve();
					}
				});
			}));
		});
		Promise.all(tasks).then(function() {
			frm.refresh_field('items');
			calculate_totals(frm);
		});
		return;
	}
	if (!frm.doc.job_number) {
		if (logistics_cash_advance_header_job_number_required(frm)) {
			$.each(frm.doc.items || [], function(i, row) {
				if (row.item_code) {
					frappe.model.set_value(row.doctype, row.name, 'item_code', null);
				}
			});
			frm.refresh_field('items');
			calculate_totals(frm);
		}
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

function logistics_cash_advance_extend_due_date(frm) {
	var base = frm.doc.liquidation_due_date || frappe.datetime.get_today();
	var default_date = frappe.datetime.add_days(base, 30);
	frappe.prompt(
		[
			{
				fieldname: 'liquidation_due_date',
				fieldtype: 'Date',
				label: __('New Liquidation Due Date'),
				reqd: 1,
				default: default_date,
				description: __('Must be after the current due date and not before today.')
			},
			{
				fieldname: 'reason',
				fieldtype: 'Small Text',
				label: __('Reason')
			}
		],
		function(values) {
			frappe.call({
				method: 'logistics.cash_advance.doctype.cash_advance_request.cash_advance_request.extend_liquidation_due_date',
				args: {
					cash_advance_request: frm.doc.name,
					liquidation_due_date: values.liquidation_due_date,
					reason: values.reason
				},
				freeze: true,
				freeze_message: __('Extending due date...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frm.reload_doc();
						frappe.show_alert({
							message: r.message.message || __('Due date updated.'),
							indicator: 'green'
						}, 5);
					}
				}
			});
		},
		__('Extend Due Date'),
		__('Update')
	);
}

function calculate_totals(frm) {
	let total_requested = 0;

	if (frm.doc.items && frm.doc.items.length > 0) {
		frm.doc.items.forEach(function(row) {
			if (row.amount_requested) {
				total_requested += parseFloat(row.amount_requested) || 0;
			}
		});
	}

	frm.set_value('total_requested', total_requested);
	frm.refresh_field('total_requested');
}

frappe.ui.form.on('Cash Advance Request Item', {
	job_number: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!logistics_cash_advance_row_job_number_required(frm)) {
			return;
		}
		if (!row.job_number) {
			if (row.item_code) {
				frappe.model.set_value(cdt, cdn, 'item_code', null);
			}
			return;
		}
		if (!row.item_code) {
			return;
		}
		frappe.call({
			method: 'logistics.cash_advance.job_charge_items.get_charge_item_codes',
			args: { job_number: row.job_number },
			callback: function(r) {
				var allowed = r.message || [];
				if (row.item_code && allowed.indexOf(row.item_code) === -1) {
					frappe.model.set_value(cdt, cdn, 'item_code', null);
				}
			}
		});
	},

	item_code: function(frm, cdt, cdn) {
		calculate_totals(frm);
	},

	amount_requested: function(frm, cdt, cdn) {
		calculate_totals(frm);
	}
});
