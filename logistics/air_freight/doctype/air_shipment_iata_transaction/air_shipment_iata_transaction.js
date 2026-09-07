frappe.ui.form.on('Air Shipment IATA Transaction', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		if (frm.doc.eawb_enabled) {
			if (!frm.doc.eawb_status || frm.doc.eawb_status === 'Not Created') {
				frm.add_custom_button(__('Create e-AWB'), () => run_method(frm, 'create_eawb'), __('e-AWB'));
			}
			if (frm.doc.eawb_status === 'Created') {
				frm.add_custom_button(__('Sign e-AWB'), () => run_method(frm, 'sign_eawb'), __('e-AWB'));
			}
			if (['Signed', 'Created'].includes(frm.doc.eawb_status)) {
				frm.add_custom_button(__('Submit e-AWB'), () => run_method(frm, 'submit_eawb'), __('e-AWB'));
			}
		}
		if (frm.doc.tact_rate_lookup || frm.doc.eawb_enabled) {
			frm.add_custom_button(__('Lookup TACT Rate'), () => run_method(frm, 'lookup_tact_rate'), __('Integrations'));
		}
		if (frm.doc.cass_participant_code || frm.doc.air_shipment) {
			frm.add_custom_button(__('View CASS Billing'), () => {
				frm.call('get_cass_billing_for_shipment').then((r) => {
					if (r.exc) {
						return;
					}
					const data = r.message || {};
					if (data.period) {
						frappe.set_route('Form', 'CASS Settlement Period', data.period);
						return;
					}
					frappe.msgprint(
						__('No CASS billing lines found for this shipment. Import a CASS File on a CASS Settlement Period.')
					);
					frappe.set_route('List', 'CASS Settlement Period');
				});
			}, __('CASSLink'));
		}
		frm.add_custom_button(__('Validate DG (AutoCheck)'), () => run_method(frm, 'validate_dg_autocheck'), __('Integrations'));
	},
});

function run_method(frm, method) {
	frm.call(method).then((r) => {
		if (!r.exc) {
			frm.reload_doc();
		}
	});
}
