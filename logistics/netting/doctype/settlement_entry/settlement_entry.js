// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Settlement Entry', {
	refresh: function(frm) {
		// Clear existing custom buttons to avoid duplicates
		frm.clear_custom_buttons();
		
		// Add Get Outstanding Transactions button under Actions menu only
		if (frm.doc.settlement_group && frm.doc.company) {
			frm.add_custom_button(__('Get Outstanding Transactions'), function() {
				frappe.confirm(
					__('This will clear existing references and add all outstanding transactions. Continue?'),
					function() {
						// Yes, continue
						// Save the document first if it's new
						if (frm.is_new()) {
							frm.save().then(function() {
								call_get_outstanding_transactions(frm);
							});
						} else {
							call_get_outstanding_transactions(frm);
						}
					},
					function() {
						// No, cancel
					}
				);
			}, __('Actions'));
		} else {
			// Show button even if fields not set, but disable it with a message
			frm.add_custom_button(__('Get Outstanding Transactions'), function() {
				frappe.msgprint({
					message: __('Please select Settlement Group and Company first.'),
					indicator: 'orange',
					title: __('Information')
				});
			}, __('Actions'));
		}
	},
	
	settlement_group: function(frm) {
		// Refresh to update button state
		frm.refresh();
	},
	
	company: function(frm) {
		// Refresh to update button state
		frm.refresh();
	}
});

// Helper function to call get_outstanding_transactions
function call_get_outstanding_transactions(frm) {
	// Use frappe.call() with full path and docname
	if (!frm.doc.name || frm.is_new()) {
		frappe.msgprint({
			message: __('Please save the document first.'),
			indicator: 'orange',
			title: __('Information')
		});
		return;
	}
	
	frappe.call({
		method: 'logistics.netting.doctype.settlement_entry.settlement_entry.get_outstanding_transactions',
		args: {
			docname: frm.doc.name,
			clear_existing: 1
		},
		freeze: true,
		freeze_message: __('Fetching outstanding transactions...'),
		callback: function(r) {
			if (!r.exc) {
				if (r.message !== undefined && r.message !== null) {
					frappe.show_alert({
						message: __('{0} transactions added', [r.message || 0]),
						indicator: 'green'
					}, 5);
				}
				frm.reload_doc();
			}
		}
	});
}

