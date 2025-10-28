// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Job Charges', {
	item_code: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item_code) {
			validate_charge_against_contract(frm, row);
		}
	},
	
	refresh: function(frm) {
		// Add custom button to validate all charges
		if (frm.doc.warehouse_contract) {
			frm.add_custom_button(__('Validate All Charges'), function() {
				validate_all_charges(frm);
			}, __('Actions'));
		}
	}
});

function validate_charge_against_contract(frm, row) {
	if (!row.item_code || !frm.doc.warehouse_contract) {
		return;
	}
	
	frappe.call({
		method: 'logistics.warehousing.api.get_contract_charge',
		args: {
			contract: frm.doc.warehouse_contract,
			item_code: row.item_code,
			context: frm.doc.type || 'storage'
		},
		callback: function(r) {
			if (r.message && Object.keys(r.message).length > 0) {
				// Charge is valid in contract - auto-fill rate and currency if available
				if (r.message.rate) {
					frappe.model.set_value(row.doctype, row.name, 'rate', r.message.rate);
				}
				if (r.message.currency) {
					frappe.model.set_value(row.doctype, row.name, 'currency', r.message.currency);
				}
				if (r.message.uom) {
					frappe.model.set_value(row.doctype, row.name, 'uom', r.message.uom);
				}
				
				frappe.show_alert({
					message: __('Charge item is valid in contract'),
					indicator: 'green'
				});
			} else {
				// Charge is not valid, show error with allowed items
				get_allowed_charges_and_show_error(frm, row);
			}
		}
	});
}

function get_allowed_charges_and_show_error(frm, row) {
	frappe.call({
		method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.get_contract_charge_items',
		args: {
			warehouse_contract: frm.doc.warehouse_contract,
			context: frm.doc.type || 'storage'
		},
		callback: function(r) {
			if (r.message && r.message.ok) {
				let allowed_items = r.message.items.map(item => item.item_charge);
				let allowed_items_str = allowed_items.slice(0, 5).join(', ');
				if (allowed_items.length > 5) {
					allowed_items_str += ` and ${allowed_items.length - 5} more`;
				}
				
				frappe.msgprint({
					title: __('Invalid Charge Item'),
					message: __('Charge item "{0}" is not defined in the warehouse contract "{1}".<br><br>Allowed charges: {2}', 
						[row.item_code, frm.doc.warehouse_contract, allowed_items_str]),
					indicator: 'red'
				});
				
				// Clear the invalid item
				frappe.model.set_value(row.doctype, row.name, 'item_code', '');
			} else {
				// Fallback error message
				frappe.msgprint({
					title: __('Invalid Charge Item'),
					message: __('Charge item "{0}" is not defined in the warehouse contract "{1}". Please select a valid charge item.', 
						[row.item_code, frm.doc.warehouse_contract]),
					indicator: 'red'
				});
				
				// Clear the invalid item
				frappe.model.set_value(row.doctype, row.name, 'item_code', '');
			}
		}
	});
}

function validate_all_charges(frm) {
	if (!frm.doc.warehouse_contract) {
		frappe.msgprint({
			title: __('No Warehouse Contract'),
			message: __('Please assign a warehouse contract to this order first.'),
			indicator: 'red'
		});
		return;
	}
	
	if (!frm.doc.charges || frm.doc.charges.length === 0) {
		frappe.msgprint({
			title: __('No Charges'),
			message: __('No charges found to validate.'),
			indicator: 'orange'
		});
		return;
	}
	
	// Get all allowed charges from contract first
	frappe.call({
		method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.get_contract_charge_items',
		args: {
			warehouse_contract: frm.doc.warehouse_contract,
			context: frm.doc.type || 'storage'
		},
		callback: function(r) {
			if (r.message && r.message.ok) {
				let allowed_items = r.message.items.map(item => item.item_charge);
				let invalid_charges = [];
				let valid_count = 0;
				
				frm.doc.charges.forEach(function(charge) {
					if (charge.item_code) {
						if (allowed_items.includes(charge.item_code)) {
							valid_count++;
						} else {
							invalid_charges.push(charge.item_code);
						}
					}
				});
				
				// Show validation results
				if (invalid_charges.length > 0) {
					let allowed_items_str = allowed_items.slice(0, 5).join(', ');
					if (allowed_items.length > 5) {
						allowed_items_str += ` and ${allowed_items.length - 5} more`;
					}
					
					frappe.msgprint({
						title: __('Invalid Charges Found'),
						message: __('The following charge items are not defined in the warehouse contract: {0}<br><br>Allowed charges: {1}', 
							[invalid_charges.join(', '), allowed_items_str]),
						indicator: 'red'
					});
				} else {
					frappe.msgprint({
						title: __('All Charges Valid'),
						message: __('All charge items are valid in the warehouse contract.'),
						indicator: 'green'
					});
				}
			} else {
				frappe.msgprint({
					title: __('Validation Error'),
					message: __('Could not retrieve contract information. Please try again.'),
					indicator: 'red'
				});
			}
		}
	});
}
