// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Lalamove Integration - Client-side Utilities
 * 
 * Provides reusable functions for Lalamove integration UI components
 */

frappe.provide('logistics.lalamove');

logistics.lalamove = {
	
	/**
	 * Get quotation for a document
	 */
	getQuotation: function(doctype, docname, callback) {
		frappe.call({
			method: 'logistics.api.lalamove_api.get_lalamove_quotation',
			args: {
				doctype: doctype,
				docname: docname
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					if (callback) callback(r.message.data);
				} else {
					frappe.show_alert({
						message: r.message?.error || 'Failed to get quotation',
						indicator: 'red'
					}, 5);
				}
			},
			error: function(r) {
				frappe.show_alert({
					message: 'Error getting quotation: ' + (r.message || 'Unknown error'),
					indicator: 'red'
				}, 5);
			}
		});
	},
	
	/**
	 * Create order from quotation
	 */
	createOrder: function(doctype, docname, quotationId, callback) {
		frappe.call({
			method: 'logistics.api.lalamove_api.create_lalamove_order',
			args: {
				doctype: doctype,
				docname: docname,
				quotation_id: quotationId
			},
			freeze: true,
			freeze_message: __('Creating Lalamove order...'),
			callback: function(r) {
				if (r.message && r.message.success) {
					frappe.show_alert({
						message: r.message.message || 'Order created successfully',
						indicator: 'green'
					}, 5);
					if (callback) callback(r.message.data);
					// Refresh the form to show the order link
					if (cur_frm) cur_frm.reload_doc();
				} else {
					frappe.show_alert({
						message: r.message?.error || 'Failed to create order',
						indicator: 'red'
					}, 5);
				}
			},
			error: function(r) {
				frappe.show_alert({
					message: 'Error creating order: ' + (r.message || 'Unknown error'),
					indicator: 'red'
				}, 5);
			}
		});
	},
	
	/**
	 * Display quotation details in a dialog
	 */
	showQuotationDialog: function(quotationData) {
		if (!quotationData || !quotationData.data) {
			frappe.msgprint(__('Invalid quotation data'));
			return;
		}
		
		const data = quotationData.data;
		const priceBreakdown = data.priceBreakdown || {};
		const stops = data.stops || [];
		
		let html = `
			<div class="lalamove-quotation-dialog">
				<div class="quotation-header">
					<h4>${__('Lalamove Quotation')}</h4>
					<div class="quotation-id">${__('Quotation ID')}: <strong>${data.quotationId || 'N/A'}</strong></div>
				</div>
				
				<div class="quotation-details">
					<div class="row">
						<div class="col-md-6">
							<h5>${__('Price Information')}</h5>
							<table class="table table-bordered">
								<tr>
									<td><strong>${__('Total Price')}</strong></td>
									<td>${priceBreakdown.currency || 'HKD'} ${parseFloat(priceBreakdown.total || 0).toFixed(2)}</td>
								</tr>
								<tr>
									<td><strong>${__('Base Price')}</strong></td>
									<td>${priceBreakdown.currency || 'HKD'} ${parseFloat(priceBreakdown.base || 0).toFixed(2)}</td>
								</tr>
								${priceBreakdown.surcharge ? `
								<tr>
									<td><strong>${__('Surcharge')}</strong></td>
									<td>${priceBreakdown.currency || 'HKD'} ${parseFloat(priceBreakdown.surcharge).toFixed(2)}</td>
								</tr>
								` : ''}
							</table>
						</div>
						<div class="col-md-6">
							<h5>${__('Delivery Information')}</h5>
							<table class="table table-bordered">
								<tr>
									<td><strong>${__('Service Type')}</strong></td>
									<td>${data.serviceType || 'N/A'}</td>
								</tr>
								<tr>
									<td><strong>${__('Distance')}</strong></td>
									<td>${parseFloat(data.distance || 0).toFixed(2)} km</td>
								</tr>
								<tr>
									<td><strong>${__('Stops')}</strong></td>
									<td>${stops.length}</td>
								</tr>
								${data.expiresAt ? `
								<tr>
									<td><strong>${__('Valid Until')}</strong></td>
									<td>${frappe.datetime.str_to_user(data.expiresAt)}</td>
								</tr>
								` : ''}
							</table>
						</div>
					</div>
					
					<div class="stops-section">
						<h5>${__('Delivery Stops')}</h5>
						<div class="stops-list">
							${stops.map((stop, index) => `
								<div class="stop-item">
									<strong>${index === 0 ? __('Pick-up') : __('Drop-off')} ${index > 0 ? index : ''}</strong>
									<div>${stop.address || 'N/A'}</div>
									${stop.coordinates ? `
									<div class="text-muted small">
										${__('Coordinates')}: ${stop.coordinates.lat}, ${stop.coordinates.lng}
									</div>
									` : ''}
								</div>
							`).join('')}
						</div>
					</div>
				</div>
			</div>
		`;
		
		const dialog = new frappe.ui.Dialog({
			title: __('Lalamove Quotation Details'),
			fields: [
				{
					fieldtype: 'HTML',
					options: html
				}
			],
			primary_action_label: __('Create Order'),
			primary_action: function() {
				dialog.hide();
				// This will be handled by the calling function
			}
		});
		
		// Store quotation data for use in primary action
		dialog.quotationData = quotationData;
		
		dialog.show();
		return dialog;
	},
	
	/**
	 * Check if quotation is valid (not expired)
	 */
	isQuotationValid: function(expiresAt) {
		if (!expiresAt) return false;
		
		const expiryTime = new Date(expiresAt);
		const now = new Date();
		return now < expiryTime;
	},
	
	/**
	 * Format quotation expiry message
	 */
	getExpiryMessage: function(expiresAt) {
		if (!expiresAt) return __('Quotation expiry time not available');
		
		const expiryTime = new Date(expiresAt);
		const now = new Date();
		const diffMs = expiryTime - now;
		
		if (diffMs <= 0) {
			return __('Quotation has expired');
		}
		
		const diffMins = Math.floor(diffMs / 60000);
		return __('Valid for {0} more minutes', [diffMins]);
	},
	
	/**
	 * Sync order status
	 */
	syncOrderStatus: function(lalamoveOrderId, callback) {
		frappe.call({
			method: 'logistics.api.lalamove_api.sync_lalamove_order_status',
			args: {
				lalamove_order_id: lalamoveOrderId
			},
			freeze: true,
			freeze_message: __('Syncing order status...'),
			callback: function(r) {
				if (r.message && r.message.success) {
					frappe.show_alert({
						message: r.message.message || 'Status synced successfully',
						indicator: 'green'
					}, 3);
					if (callback) callback(r.message.data);
					if (cur_frm) cur_frm.reload_doc();
				} else {
					frappe.show_alert({
						message: r.message?.error || 'Failed to sync status',
						indicator: 'red'
					}, 5);
				}
			}
		});
	},
	
	/**
	 * Cancel order
	 */
	cancelOrder: function(lalamoveOrderId, callback) {
		frappe.confirm(
			__('Are you sure you want to cancel this Lalamove order?'),
			function() {
				frappe.call({
					method: 'logistics.api.lalamove_api.cancel_lalamove_order',
					args: {
						lalamove_order_id: lalamoveOrderId
					},
					freeze: true,
					freeze_message: __('Cancelling order...'),
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: r.message.message || 'Order cancelled successfully',
								indicator: 'green'
							}, 5);
							if (callback) callback();
							if (cur_frm) cur_frm.reload_doc();
						} else {
							frappe.show_alert({
								message: r.message?.error || 'Failed to cancel order',
								indicator: 'red'
							}, 5);
						}
					}
				});
			}
		);
	},
	
	/**
	 * Show order status dialog
	 */
	showOrderStatus: function(lalamoveOrderId) {
		frappe.call({
			method: 'logistics.api.lalamove_api.get_lalamove_order_status',
			args: {
				lalamove_order_id: lalamoveOrderId
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					const data = r.message.data.data || {};
					const driver = data.driver || {};
					const vehicle = data.vehicle || {};
					
					let html = `
						<div class="lalamove-order-status">
							<div class="order-header">
								<h4>${__('Lalamove Order Status')}</h4>
								<div class="order-id">${__('Order ID')}: <strong>${lalamoveOrderId}</strong></div>
							</div>
							
							<div class="order-details">
								<div class="row">
									<div class="col-md-6">
										<h5>${__('Order Information')}</h5>
										<table class="table table-bordered">
											<tr>
												<td><strong>${__('Status')}</strong></td>
												<td><span class="badge badge-primary">${data.status || 'N/A'}</span></td>
											</tr>
											<tr>
												<td><strong>${__('Price')}</strong></td>
												<td>${data.currency || 'HKD'} ${parseFloat(data.price || 0).toFixed(2)}</td>
											</tr>
											<tr>
												<td><strong>${__('Distance')}</strong></td>
												<td>${parseFloat(data.distance || 0).toFixed(2)} km</td>
											</tr>
										</table>
									</div>
									<div class="col-md-6">
										<h5>${__('Driver Information')}</h5>
										${driver.name ? `
										<table class="table table-bordered">
											<tr>
												<td><strong>${__('Name')}</strong></td>
												<td>${driver.name}</td>
											</tr>
											${driver.phone ? `
											<tr>
												<td><strong>${__('Phone')}</strong></td>
												<td>${driver.phone}</td>
											</tr>
											` : ''}
											${vehicle.type ? `
											<tr>
												<td><strong>${__('Vehicle Type')}</strong></td>
												<td>${vehicle.type}</td>
											</tr>
											` : ''}
											${vehicle.vehicleNumber ? `
											<tr>
												<td><strong>${__('Vehicle Number')}</strong></td>
												<td>${vehicle.vehicleNumber}</td>
											</tr>
											` : ''}
										</table>
										` : '<p class="text-muted">' + __('Driver not assigned yet') + '</p>'}
									</div>
								</div>
							</div>
						</div>
					`;
					
					const dialog = new frappe.ui.Dialog({
						title: __('Lalamove Order Status'),
						fields: [
							{
								fieldtype: 'HTML',
								options: html
							}
						]
					});
					
					dialog.show();
				} else {
					frappe.show_alert({
						message: r.message?.error || 'Failed to get order status',
						indicator: 'red'
					}, 5);
				}
			}
		});
	}
};

