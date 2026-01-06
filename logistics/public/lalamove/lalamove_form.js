// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Lalamove Integration - Form Script Utilities
 * 
 * Common form script functions for Lalamove integration
 * Can be included in any doctype form that needs Lalamove integration
 */

frappe.provide('logistics.lalamove.form');

logistics.lalamove.form = {
	
	/**
	 * Setup Lalamove section in form
	 * Call this in the form's refresh event
	 */
	setupLalamoveSection: function(frm) {
		if (!frm.doc.use_lalamove) {
			return;
		}
		
		// Add Lalamove section if not exists
		if (!frm.fields_dict.lalamove_section) {
			frm.add_custom_button(__('Lalamove Integration'), function() {
				logistics.lalamove.form.showLalamoveDialog(frm);
			}, __('Actions'));
		}
	},
	
	/**
	 * Show Lalamove integration dialog
	 */
	showLalamoveDialog: function(frm) {
		const doctype = frm.doctype;
		const docname = frm.doc.name;
		
		if (!docname || frm.is_new()) {
			frappe.msgprint(__('Please save the document first'));
			return;
		}
		
		// Check if order already exists
		if (frm.doc.lalamove_order) {
			// Show order management options
			logistics.lalamove.form.showOrderManagementDialog(frm);
		} else {
			// Show quotation/order creation options
			logistics.lalamove.form.showQuotationDialog(frm);
		}
	},
	
	/**
	 * Show quotation dialog
	 */
	showQuotationDialog: function(frm) {
		const doctype = frm.doctype;
		const docname = frm.doc.name;
		
		const dialog = new frappe.ui.Dialog({
			title: __('Lalamove Integration'),
			fields: [
				{
					fieldtype: 'Section Break',
					label: __('Get Quotation')
				},
				{
					fieldtype: 'HTML',
					options: `
						<div class="alert alert-info">
							${__('Get a price quotation for this delivery. Quotations are valid for 5 minutes.')}
						</div>
					`
				},
				{
					fieldtype: 'Button',
					label: __('Get Quotation'),
					click: function() {
						dialog.hide();
						logistics.lalamove.form.getQuotation(frm);
					}
				},
				{
					fieldtype: 'Section Break',
					label: __('Existing Quotation')
				},
				{
					fieldtype: 'Link',
					fieldname: 'quotation',
					label: __('Quotation'),
					options: 'Lalamove Quotation',
					get_query: function() {
						return {
							filters: {
								source_doctype: doctype,
								source_docname: docname
							}
						};
					}
				},
				{
					fieldtype: 'Button',
					label: __('View Quotation Details'),
					depends_on: 'quotation',
					click: function() {
						const quotation = dialog.get_value('quotation');
						if (quotation) {
							frappe.set_route('Form', 'Lalamove Quotation', quotation);
						}
					}
				},
				{
					fieldtype: 'Button',
					label: __('Create Order from Quotation'),
					depends_on: 'quotation',
					click: function() {
						const quotation = dialog.get_value('quotation');
						if (quotation) {
							dialog.hide();
							logistics.lalamove.form.createOrderFromQuotation(frm, quotation);
						}
					}
				}
			]
		});
		
		// Pre-fill quotation if exists
		if (frm.doc.lalamove_quotation) {
			dialog.set_value('quotation', frm.doc.lalamove_quotation);
		}
		
		dialog.show();
	},
	
	/**
	 * Get quotation for form
	 */
	getQuotation: function(frm) {
		const doctype = frm.doctype;
		const docname = frm.doc.name;
		
		frappe.call({
			method: 'logistics.api.lalamove_api.get_lalamove_quotation',
			args: {
				doctype: doctype,
				docname: docname
			},
			freeze: true,
			freeze_message: __('Getting quotation from Lalamove...'),
			callback: function(r) {
				if (r.message && r.message.success) {
					const quotationData = r.message.data;
					const dialog = logistics.lalamove.showQuotationDialog(quotationData);
					
					// Update primary action to create order
					dialog.set_primary_action(__('Create Order'), function() {
						const quotationId = quotationData.data.quotationId;
						dialog.hide();
						logistics.lalamove.createOrder(doctype, docname, quotationId, function() {
							frm.reload_doc();
						});
					});
				} else {
					frappe.msgprint({
						title: __('Error'),
						message: r.message?.error || __('Failed to get quotation'),
						indicator: 'red'
					});
				}
			}
		});
	},
	
	/**
	 * Create order from quotation
	 */
	createOrderFromQuotation: function(frm, quotationName) {
		// Get quotation ID
		frappe.db.get_value('Lalamove Quotation', quotationName, 'quotation_id', (r) => {
			if (r && r.quotation_id) {
				logistics.lalamove.createOrder(
					frm.doctype,
					frm.doc.name,
					r.quotation_id,
					function() {
						frm.reload_doc();
					}
				);
			} else {
				frappe.msgprint(__('Quotation ID not found'));
			}
		});
	},
	
	/**
	 * Show order management dialog
	 */
	showOrderManagementDialog: function(frm) {
		if (!frm.doc.lalamove_order) {
			return;
		}
		
		// Get Lalamove Order details
		frappe.db.get_value('Lalamove Order', frm.doc.lalamove_order, ['lalamove_order_id', 'status'], (r) => {
			if (!r || !r.lalamove_order_id) {
				return;
			}
			
			const orderId = r.lalamove_order_id;
			const status = r.status;
			
			const dialog = new frappe.ui.Dialog({
				title: __('Lalamove Order Management'),
				fields: [
					{
						fieldtype: 'Section Break',
						label: __('Order Information')
					},
					{
						fieldtype: 'HTML',
						options: `
							<div class="alert alert-info">
								<strong>${__('Order ID')}:</strong> ${orderId}<br>
								<strong>${__('Status')}:</strong> ${status}
							</div>
						`
					},
					{
						fieldtype: 'Button',
						label: __('View Order Details'),
						click: function() {
							dialog.hide();
							logistics.lalamove.showOrderStatus(orderId);
						}
					},
					{
						fieldtype: 'Button',
						label: __('Sync Status'),
						click: function() {
							dialog.hide();
							logistics.lalamove.syncOrderStatus(orderId, function() {
								frm.reload_doc();
							});
						}
					},
					{
						fieldtype: 'Section Break',
						label: __('Actions')
					},
					{
						fieldtype: 'Button',
						label: __('Change Driver'),
						click: function() {
							dialog.hide();
							logistics.lalamove.form.changeDriver(orderId, frm);
						}
					},
					{
						fieldtype: 'Button',
						label: __('Add Priority Fee'),
						click: function() {
							dialog.hide();
							logistics.lalamove.form.addPriorityFee(orderId, frm);
						}
					},
					{
						fieldtype: 'Button',
						label: __('Cancel Order'),
						click: function() {
							dialog.hide();
							logistics.lalamove.cancelOrder(orderId, function() {
								frm.reload_doc();
							});
						}
					},
					{
						fieldtype: 'Button',
						label: __('Open Lalamove Order'),
						click: function() {
							frappe.set_route('Form', 'Lalamove Order', frm.doc.lalamove_order);
						}
					}
				]
			});
			
			dialog.show();
		});
	},
	
	/**
	 * Change driver
	 */
	changeDriver: function(orderId, frm) {
		frappe.call({
			method: 'logistics.api.lalamove_api.change_lalamove_driver',
			args: {
				lalamove_order_id: orderId
			},
			freeze: true,
			freeze_message: __('Requesting driver change...'),
			callback: function(r) {
				if (r.message && r.message.success) {
					frappe.show_alert({
						message: r.message.message || __('Driver change requested successfully'),
						indicator: 'green'
					}, 5);
					if (frm) frm.reload_doc();
				} else {
					frappe.show_alert({
						message: r.message?.error || __('Failed to request driver change'),
						indicator: 'red'
					}, 5);
				}
			}
		});
	},
	
	/**
	 * Add priority fee
	 */
	addPriorityFee: function(orderId, frm) {
		frappe.confirm(
			__('Add priority fee to expedite delivery? This will incur additional charges.'),
			function() {
				frappe.call({
					method: 'logistics.api.lalamove_api.add_lalamove_priority_fee',
					args: {
						lalamove_order_id: orderId
					},
					freeze: true,
					freeze_message: __('Adding priority fee...'),
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: r.message.message || __('Priority fee added successfully'),
								indicator: 'green'
							}, 5);
							if (frm) frm.reload_doc();
						} else {
							frappe.show_alert({
								message: r.message?.error || __('Failed to add priority fee'),
								indicator: 'red'
							}, 5);
						}
					}
				});
			}
		);
	}
};

