// Sync Revenue & Cost Recognition from policy (read-only except Recognition Date when User Specified).
frappe.provide('logistics.recognition_policy');

logistics.recognition_policy._apply = function (frm, m) {
	if (!frm || !m) return;
	var basis = m.recognition_date_basis || 'Job Booking Date';
	frm.doc.wip_recognition_enabled = m.wip_recognition_enabled;
	frm.doc.accrual_recognition_enabled = m.accrual_recognition_enabled;
	frm.doc.recognition_date_basis = basis;
	frm.doc.recognition_policy_reference = m.recognition_policy_reference || '';
	frm.refresh_field('wip_recognition_enabled');
	frm.refresh_field('accrual_recognition_enabled');
	frm.refresh_field('recognition_date_basis');
	frm.refresh_field('recognition_policy_reference');

	var userSpecified = basis === 'User Specified';
	if (frm.fields_dict.recognition_date) {
		frm.set_df_property('recognition_date', 'read_only', userSpecified ? 0 : 1);
	}
	if (m.recognition_date) {
		frm.doc.recognition_date = m.recognition_date;
		frm.refresh_field('recognition_date');
	}
};

logistics.recognition_policy.sync_from_policy = function (frm) {
	if (!frm || !frm.doc) return;
	var d = frm.doc;
	if (!d.company) {
		logistics.recognition_policy._apply(frm, {
			wip_recognition_enabled: 0,
			accrual_recognition_enabled: 0,
			recognition_date_basis: 'Job Booking Date',
			recognition_policy_reference: '',
			recognition_date: null,
		});
		return;
	}
	var args = {
		company: d.company,
		cost_center: d.cost_center || '',
		profit_center: d.profit_center || '',
		branch: d.branch || '',
		job_costing_number: d.job_costing_number || '',
	};
	if (d.recognition_date && d.recognition_date_basis === 'User Specified') {
		args.recognition_date_override = d.recognition_date;
	}
	if (d.name && !d.__islocal && !String(d.name).startsWith('new-')) {
		args.doctype = frm.doctype;
		args.docname = d.name;
	}
	frappe.call({
		method: 'logistics.job_management.recognition_engine.get_recognition_policy_display',
		args: args,
		callback: function (r) {
			if (r && r.message) {
				logistics.recognition_policy._apply(frm, r.message);
			}
		},
	});
};

(function () {
	var DOCTYPES = [
		'Air Shipment',
		'Sea Shipment',
		'Declaration',
		'Transport Job',
		'Warehouse Job',
		'General Job',
	];
	var DIM = [
		'company',
		'cost_center',
		'profit_center',
		'branch',
		'job_costing_number',
		'direction',
		'transport_mode',
		'recognition_date',
	];
	DOCTYPES.forEach(function (dt) {
		frappe.ui.form.on(dt, {
			refresh: function (frm) {
				logistics.recognition_policy.sync_from_policy(frm);
			},
		});
		DIM.forEach(function (fieldname) {
			frappe.ui.form.on(dt, fieldname, function (frm) {
				if (fieldname === 'recognition_date') {
					var b = frm.doc.recognition_date_basis;
					if (b === 'User Specified') {
						return;
					}
				}
				logistics.recognition_policy.sync_from_policy(frm);
			});
		});
	});
})();
