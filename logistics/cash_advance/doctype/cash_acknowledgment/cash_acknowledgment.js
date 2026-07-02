frappe.ui.form.on('Cash Acknowledgment', {
	refresh: function(frm) {
		logistics_cash_acknowledgment_set_fund_source_query(frm);
		frm.dashboard.set_headline_alert('');
	},

	company: function(frm) {
		logistics_cash_acknowledgment_set_fund_source_query(frm);
		logistics_cash_acknowledgment_clear_mismatched_fund_source(frm);
	},

	cash_advance_request: function(frm) {
		logistics_cash_acknowledgment_pull_from_request(frm);
	}
});

function logistics_cash_acknowledgment_clear_mismatched_fund_source(frm) {
	if (!frm.doc.company || !frm.doc.fund_source) {
		return;
	}
	var company = frm.doc.company;
	frappe.db.get_value('Account', frm.doc.fund_source, 'company', function(r) {
		if (r && r.company && r.company !== company) {
			frm.set_value('fund_source', null);
		}
	});
}

function logistics_cash_acknowledgment_set_fund_source_query(frm) {
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

function logistics_cash_acknowledgment_pull_from_request(frm) {
	if (!frm.doc.cash_advance_request) {
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
		return p.then(function() {
			logistics_cash_acknowledgment_set_fund_source_query(frm);
			logistics_cash_acknowledgment_show_settlement_dialog(frm);
		});
	});
}

function logistics_cash_acknowledgment_show_settlement_dialog(frm) {
	if (!frm.doc.cash_advance_request) {
		return;
	}
	frappe.call({
		method: 'logistics.cash_advance.accounting.get_cash_advance_settlement_summary',
		args: {
			cash_advance_request: frm.doc.cash_advance_request,
			exclude_acknowledgment: frm.doc.name
		},
		callback: function(r) {
			if (!r.message) {
				return;
			}
			var s = r.message;
			var currency = frappe.defaults.get_global_default('currency');
			var fmt = function(val) {
				return format_currency(val, currency);
			};
			var guidance = [];
			if (flt(s.cash_to_return) > 0) {
				guidance.push(
					__('Use <b>Receipt</b> to record unused cash returned by the payee (up to {0}).', [fmt(s.cash_to_return)])
				);
			}
			if (flt(s.cash_to_pay) > 0) {
				guidance.push(
					__('Use <b>Payment</b> to record additional cash paid out (up to {0}).', [fmt(s.cash_to_pay)])
				);
			}
			if (!guidance.length) {
				guidance.push(__('This cash advance is fully settled. No receipt or payment is expected.'));
			}
			var message = [
				'<table class="table table-bordered" style="margin-bottom:12px;">',
				'<tr><td>' + __('Advance') + '</td><td class="text-right"><b>' + fmt(s.advance) + '</b></td></tr>',
				'<tr><td>' + __('Liquidated') + '</td><td class="text-right"><b>' + fmt(s.liquidated) + '</b></td></tr>',
				'<tr><td>' + __('Cash to return (Receipt)') + '</td><td class="text-right"><b>' + fmt(s.cash_to_return) + '</b></td></tr>',
				'<tr><td>' + __('Cash to pay (Payment)') + '</td><td class="text-right"><b>' + fmt(s.cash_to_pay) + '</b></td></tr>',
				'</table>',
				guidance.join('<br>')
			].join('');
			frappe.msgprint({
				title: __('Cash Advance Settlement'),
				message: message,
				indicator: 'blue'
			});
		}
	});
}
