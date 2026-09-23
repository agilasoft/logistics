frappe.ui.form.on('CASS File', {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		if (frm.doc.attached_file) {
			frm.add_custom_button(__('Process File'), () => {
				frm.call({
					method: 'process_file',
					doc: frm.doc,
					freeze: true,
					freeze_message: __('Parsing CASS file...'),
				}).then((r) => {
					if (r.exc) {
						return;
					}
					const msg = r.message || {};
					frm.reload_doc().then(() => {
						show_cass_file_result(msg);
					});
				});
			}, __('CASSLink'));
		}
	},
});

function show_cass_file_result(msg) {
	const lines = cint(msg.lines);
	const matched = cint(msg.matched);
	const unmatched = msg.unmatched != null ? cint(msg.unmatched) : lines - matched;
	const errors = msg.errors || [];
	if (msg.status === 'Failed' || !lines) {
		frappe.msgprint({
			title: __('CASS File not imported'),
			indicator: 'red',
			message: errors.join('<br>') || __('No billing lines were found.'),
		});
		return;
	}
	frappe.msgprint({
		title: __('CASS File parsed'),
		indicator: 'green',
		message: __('Imported {0} billing line(s): {1} matched, {2} unmatched. Status Parsed means the file was read. Open the settlement period to create draft Purchase Invoices.',
			[lines, matched, unmatched]),
	});
}
