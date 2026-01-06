// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Air Booking', {
	refresh: function(frm) {
		// Add button to fetch quotations
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__('Fetch Quotations'), function() {
				frm.call({
					method: 'fetch_quotations',
					doc: frm.doc,
					callback: function(r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
						}
					}
				});
			}, __('Actions'));
		}
		
		// Add button to convert to shipment
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Convert to Shipment'), function() {
				frappe.confirm(
					__('Are you sure you want to convert this Air Booking to an Air Shipment?'),
					function() {
						frm.call({
							method: 'convert_to_shipment',
							doc: frm.doc,
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.set_route('Form', 'Air Shipment', r.message.air_shipment);
								}
							}
						});
					}
				);
			}, __('Actions'));
		}
	},
	
	volume: function(frm) {
		// Calculate chargeable weight when volume changes
		frm.trigger('calculate_chargeable_weight');
	},
	
	weight: function(frm) {
		// Calculate chargeable weight when weight changes
		frm.trigger('calculate_chargeable_weight');
	},
	
	volume_to_weight_factor_type: function(frm) {
		// Recalculate when factor type changes
		frm.trigger('calculate_chargeable_weight');
	},
	
	custom_volume_to_weight_divisor: function(frm) {
		// Recalculate when custom divisor changes
		frm.trigger('calculate_chargeable_weight');
	},
	
	airline: function(frm) {
		// Recalculate when airline changes (may affect divisor)
		frm.trigger('calculate_chargeable_weight');
	},
	
	calculate_chargeable_weight: function(frm) {
		// Calculate chargeable weight on client side for immediate feedback
		if (!frm.doc.volume && !frm.doc.weight) {
			frm.set_value('chargeable', 0);
			return;
		}
		
		// Get divisor
		let divisor = 6000; // Default IATA
		
		const factor_type = frm.doc.volume_to_weight_factor_type || 'IATA';
		
		if (factor_type === 'IATA') {
			divisor = 6000;
		} else if (factor_type === 'Custom') {
			if (frm.doc.custom_volume_to_weight_divisor) {
				divisor = parseFloat(frm.doc.custom_volume_to_weight_divisor) || 6000;
			} else if (frm.doc.airline) {
				// Fetch airline divisor
				frappe.db.get_value('Airline', frm.doc.airline, 'volume_to_weight_divisor', (r) => {
					if (r && r.volume_to_weight_divisor) {
						divisor = parseFloat(r.volume_to_weight_divisor) || 6000;
					}
					_calculate_and_set_chargeable_weight(frm, divisor);
				});
				return; // Will continue in callback
			}
		}
		
		_calculate_and_set_chargeable_weight(frm, divisor);
	}
});

function _calculate_and_set_chargeable_weight(frm, divisor) {
	let volume_weight = 0;
	let chargeable = 0;
	
	// Calculate volume weight: volume (m³) * 1,000,000 / divisor
	if (frm.doc.volume && divisor) {
		volume_weight = parseFloat(frm.doc.volume) * (1000000.0 / divisor);
	}
	
	// Chargeable weight is higher of actual weight or volume weight
	if (frm.doc.weight && volume_weight) {
		chargeable = Math.max(parseFloat(frm.doc.weight), volume_weight);
	} else if (frm.doc.weight) {
		chargeable = parseFloat(frm.doc.weight);
	} else if (volume_weight) {
		chargeable = volume_weight;
	}
	
	frm.set_value('chargeable', chargeable);
}

