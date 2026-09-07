frappe.ui.form.on('CASS Settlement Period', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__('Create Draft Purchase Invoices'), () => {
			frm.call({
				method: 'create_draft_purchase_invoices',
				doc: frm.doc,
				freeze: true,
				freeze_message: __('Creating draft Purchase Invoices...'),
			}).then((r) => {
				if (!r.exc) {
					frm.reload_doc();
					const msg = r.message || {};
					frappe.msgprint(
						__('Created {0} draft Purchase Invoice(s). {1} line(s) skipped.',
							[msg.purchase_invoices ? msg.purchase_invoices.length : 0, msg.skipped || 0])
					);
				}
			});
		}, __('CASSLink'));
	},
});
