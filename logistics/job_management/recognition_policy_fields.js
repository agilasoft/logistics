// Sync Revenue & Cost Recognition fields from Recognition Policy Settings (read-only on form).
frappe.provide('logistics.recognition_policy');

logistics.recognition_policy._FIELDS = [
	'wip_recognition_enabled',
	'wip_recognition_date_basis',
	'accrual_recognition_enabled',
	'accrual_recognition_date_basis'
];

logistics.recognition_policy._apply = function (frm, m) {
	if (!frm || !m) return;
	logistics.recognition_policy._FIELDS.forEach(function (f) {
		if (!Object.prototype.hasOwnProperty.call(m, f)) return;
		frm.doc[f] = m[f];
		frm.refresh_field(f);
	});
};

logistics.recognition_policy.sync_from_policy = function (frm) {
	if (!frm || !frm.doc) return;
	var d = frm.doc;
	if (!d.company) {
		logistics.recognition_policy._apply(frm, {
			wip_recognition_enabled: 0,
			wip_recognition_date_basis: 'Job Booking Date',
			accrual_recognition_enabled: 0,
			accrual_recognition_date_basis: 'Job Booking Date'
		});
		return;
	}
	frappe.call({
		method: 'logistics.job_management.recognition_engine.get_recognition_policy_display',
		args: {
			company: d.company,
			cost_center: d.cost_center || '',
			profit_center: d.profit_center || '',
			branch: d.branch || '',
			job_costing_number: d.job_costing_number || ''
		},
		callback: function (r) {
			if (r && r.message) {
				logistics.recognition_policy._apply(frm, r.message);
			}
		}
	});
};

(function () {
	var DOCTYPES = [
		'Air Shipment',
		'Sea Shipment',
		'Declaration',
		'Transport Job',
		'Warehouse Job',
		'General Job'
	];
	var DIM = ['company', 'cost_center', 'profit_center', 'branch', 'job_costing_number'];
	DOCTYPES.forEach(function (dt) {
		frappe.ui.form.on(dt, {
			refresh: function (frm) {
				logistics.recognition_policy.sync_from_policy(frm);
			}
		});
		DIM.forEach(function (fieldname) {
			frappe.ui.form.on(dt, fieldname, function (frm) {
				logistics.recognition_policy.sync_from_policy(frm);
			});
		});
	});
})();
