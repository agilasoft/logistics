frappe.ui.form.on('IATA Settings', {
	connection_mode(frm) {
		_toggle_connection_fields(frm);
	},
	cargo_xml_enabled(frm) {
		_toggle_connection_fields(frm);
	},
});

function _toggle_connection_fields(frm) {
	const enabled = frm.doc.cargo_xml_enabled;
	const is_ccs = enabled && frm.doc.connection_mode === 'CCS Hub';
	frm.toggle_reqd('cargo_xml_endpoint', enabled && frm.doc.connection_mode === 'Direct' && !frm.doc.test_mode);
	frm.toggle_reqd('ccs_provider', is_ccs && !frm.doc.test_mode);
	frm.toggle_reqd('ccs_participant_code', is_ccs && !frm.doc.test_mode);
}
