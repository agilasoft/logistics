// Shared: apply Shipper/Consignee master defaults on transaction forms (empty fields only).
frappe.provide('logistics.party_defaults');

logistics.party_defaults = {
	_party_fields(doctype) {
		if (doctype === 'Declaration' || doctype === 'Declaration Order') {
			return { shipper_field: 'exporter_shipper', consignee_field: 'importer_consignee' };
		}
		return { shipper_field: 'shipper', consignee_field: 'consignee' };
	},

	apply_application_party_labels(frm) {
		if (!frm || (frm.doctype !== 'Declaration' && frm.doctype !== 'Declaration Order')) {
			return;
		}
		const application = frm.doc.declaration_type === 'Application';
		frm.set_df_property(
			'exporter_shipper',
			'label',
			application ? __('Shipper') : __('Exporter/Shipper')
		);
		frm.set_df_property(
			'importer_consignee',
			'label',
			application ? __('Consignee') : __('Importer/Consignee')
		);
		frm.set_df_property('exporter_shipper', 'reqd', 0);
		frm.set_df_property('importer_consignee', 'reqd', 0);
	},

	apply(frm) {
		const pf = this._party_fields(frm.doctype);
		const shipper = frm.doc[pf.shipper_field];
		const consignee = frm.doc[pf.consignee_field];
		if (!shipper && !consignee) {
			return;
		}
		frappe.call({
			method: 'logistics.utils.shipper_consignee_defaults.get_applicable_defaults',
			args: {
				target_doctype: frm.doctype,
				shipper: shipper || null,
				consignee: consignee || null,
			},
			callback(r) {
				const msg = r.message || {};
				Object.keys(msg).forEach((field) => {
					const v = msg[field];
					if (v !== undefined && v !== null && v !== '' && !frm.doc[field]) {
						frm.set_value(field, v);
					}
				});
			},
		});
	},
};
