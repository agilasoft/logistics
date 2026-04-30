// Clear Dynamic Link when Entity Type changes on Operational Exchange Rate child rows.
frappe.ui.form.on('Operational Exchange Rate', {
	entity_type(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, 'entity', null);
	},
});
