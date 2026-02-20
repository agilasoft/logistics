// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

// Suppress "Air Booking not found" when form is new/unsaved (e.g. child grid or quote change triggers API before save)
frappe.ui.form.on('Air Booking', {
	onload: function(frm) {
		if (frm.is_new() || frm.doc.__islocal) {
			if (!frappe._original_msgprint_ab) {
				frappe._original_msgprint_ab = frappe.msgprint;
			}
			frappe.msgprint = function(options) {
				const message = typeof options === 'string' ? options : (options && options.message || '');
				if (message && typeof message === 'string' &&
					message.includes('Air Booking') &&
					message.includes('not found')) {
					return;
				}
				return frappe._original_msgprint_ab.apply(this, arguments);
			};
			frm.$wrapper.one('form-refresh', function() {
				if (!frm.is_new() && !frm.doc.__islocal && frappe._original_msgprint_ab) {
					frappe.msgprint = frappe._original_msgprint_ab;
				}
			});
		}
	},
	
	refresh: function(frm) {
		// Add button to fetch quotations (only when doc is saved to avoid "Air Booking not found")
		if (frm.doc.sales_quote && !frm.is_new() && !frm.doc.__islocal) {
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
		
		// Add conversion button when document is submitted
		if (frm.doc.docstatus === 1) {
			frappe.db.get_value('Air Shipment', {'air_booking': frm.doc.name}, 'name', (r) => {
				if (r && r.name) {
					// Air Shipment already exists - show link to view it
					frm.add_custom_button(__('View Air Shipment'), function() {
						frappe.set_route('Form', 'Air Shipment', r.name);
					}, __('Actions'));
				} else {
					// No Air Shipment exists - show convert button
					frm.add_custom_button(__('Convert to Shipment'), function() {
						// Check conversion readiness first
						frm.call({
							method: 'check_conversion_readiness',
							doc: frm.doc,
							callback: function(readiness_r) {
								if (readiness_r.message && !readiness_r.message.is_ready) {
									// Show missing fields
									var missing_fields = readiness_r.message.missing_fields || [];
									var messages = missing_fields.map(function(field) {
										return field.message || field.label;
									});
									frappe.msgprint({
										title: __('Cannot Convert to Air Shipment'),
										message: __('The following issues must be resolved before conversion:<br><ul><li>' + messages.join('</li><li>') + '</li></ul>'),
										indicator: 'red'
									});
									return;
								}
								
								// Proceed with conversion
								frappe.confirm(
									__('Are you sure you want to convert this Air Booking to an Air Shipment?'),
									function() {
										// Yes
										frm.call({
											method: 'convert_to_shipment',
											doc: frm.doc,
											freeze: true,
											freeze_message: __('Converting to Air Shipment...'),
											callback: function(r) {
												if (r.exc) return;
												if (r.message && r.message.success && r.message.air_shipment) {
													frappe.show_alert({
														message: __('Air Shipment {0} created successfully', [r.message.air_shipment]),
														indicator: 'green'
													});
													setTimeout(function() {
														frappe.set_route('Form', 'Air Shipment', r.message.air_shipment);
													}, 100);
												}
											}
										});
									},
									function() {
										// No
									}
								);
							}
						});
					}, __('Actions'));
				}
			});
		}
		
		// Setup query filter for quote field based on quote_type
		_setup_quote_query(frm);
	},
	
	sales_quote: function(frm) {
		_populate_charges_from_quote(frm);
	},
	
	quote_type: function(frm) {
		// Don't clear quote fields if document is already submitted
		if (frm.doc.docstatus === 1) {
			return;
		}
		
		// If changing quote type and there's an existing quote, clear it
		// This ensures users select a new quote of the correct type
		if (frm.doc.quote) {
			frm.set_value('quote', '');
		}
		
		// Setup query filter for quote field based on quote_type
		_setup_quote_query(frm);
		
		if (!frm.doc.quote) {
			frm.clear_table('charges');
			frm.refresh_field('charges');
		} else {
			_populate_charges_from_quote(frm);
		}
	},
	
	quote: function(frm) {
		// Don't clear quote fields if document is already submitted
		if (frm.doc.docstatus === 1) {
			return;
		}
		if (!frm.doc.quote) {
			frm.clear_table('charges');
			frm.refresh_field('charges');
			// Clear sales_quote when quote is cleared
			if (frm.doc.sales_quote) {
				frm.set_value('sales_quote', '');
			}
			return;
		}
		// Sync sales_quote field when quote_type is "Sales Quote"
		if (frm.doc.quote_type === 'Sales Quote' && frm.doc.quote) {
			frm.set_value('sales_quote', frm.doc.quote);
		} else if (frm.doc.quote_type === 'One-Off Quote') {
			// Clear sales_quote for One-Off Quote
			frm.set_value('sales_quote', '');
		}
		_populate_charges_from_quote(frm);
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
	
	override_volume_weight: function(frm) {
		// When unchecked, refresh header volume/weight from package totals (server call skipped when unsaved inside aggregate_volume_from_packages)
		if (!frm.doc.override_volume_weight) {
			frm.trigger('aggregate_volume_from_packages');
		}
	},
	
	aggregate_volume_from_packages: function(frm) {
		// Aggregate volume and weight from all packages and update header
		// This is called when package volumes or weights change
		if (!frm.doc.packages || frm.doc.packages.length === 0) {
			// If no packages, clear volume and weight
			if (frm.doc.volume) {
				frm.set_value('volume', 0);
			}
			if (frm.doc.weight) {
				frm.set_value('weight', 0);
			}
			frm.trigger('calculate_chargeable_weight');
			return;
		}
		
		// Skip server call when doc is unsaved to avoid "Air Booking not found"
		if (frm.doc.__islocal) {
			return;
		}
		
		// Call server-side method to aggregate volumes and weights with proper UOM conversion
		frm.call({
			method: 'aggregate_volume_from_packages_api',
			doc: frm.doc,
			callback: function(r) {
				// After aggregation, update form values
				if (r && !r.exc && r.message) {
					if (r.message.volume !== undefined) {
						frm.set_value('volume', r.message.volume);
					}
					if (r.message.weight !== undefined) {
						frm.set_value('weight', r.message.weight);
					}
					if (r.message.chargeable !== undefined) {
						frm.set_value('chargeable', r.message.chargeable);
					} else {
						// Fallback: recalculate chargeable weight client-side
						frm.trigger('calculate_chargeable_weight');
					}
				}
			}
		});
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
	},
	
	before_submit: function(frm) {
		// Validate quote is not empty before submitting
		if (!frm.doc.quote) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __("Quote is required. Please select a quote before submitting the Air Booking."),
				indicator: 'red'
			});
			return Promise.reject(__("Quote is required. Please select a quote before submitting the Air Booking."));
		}
		
		// Validate charges is not empty before submitting
		var charges = frm.doc.charges || [];
		if (!charges || charges.length === 0) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __("Charges are required. Please add at least one charge before submitting the Air Booking."),
				indicator: 'red'
			});
			return Promise.reject(__("Charges are required. Please add at least one charge before submitting the Air Booking."));
		}
		
		// Validate packages is not empty before submitting
		var packages = frm.doc.packages || [];
		if (!packages || packages.length === 0) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __("Packages are required. Please add at least one package before submitting the Air Booking."),
				indicator: 'red'
			});
			return Promise.reject(__("Packages are required. Please add at least one package before submitting the Air Booking."));
		}
		
		// Validate ETD is required
		if (!frm.doc.etd) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __("ETD (Estimated Time of Departure) is required before submitting the Air Booking."),
				indicator: 'red'
			});
			return Promise.reject(__("ETD (Estimated Time of Departure) is required before submitting the Air Booking."));
		}
		
		// Validate ETA is required
		if (!frm.doc.eta) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __("ETA (Estimated Time of Arrival) is required before submitting the Air Booking."),
				indicator: 'red'
			});
			return Promise.reject(__("ETA (Estimated Time of Arrival) is required before submitting the Air Booking."));
		}
	}
});

// Air Booking Packages child table events
frappe.ui.form.on('Air Booking Packages', {
	commodity: function(frm, cdt, cdn) {
		// Populate HS code from commodity's default_hs_code
		let row = locals[cdt][cdn];
		if (row.commodity) {
			frappe.db.get_value('Commodity', row.commodity, 'default_hs_code', (r) => {
				if (r && r.default_hs_code) {
					frappe.model.set_value(cdt, cdn, 'hs_code', r.default_hs_code);
				} else {
					// Clear HS code if commodity doesn't have a default HS code
					frappe.model.set_value(cdt, cdn, 'hs_code', '');
				}
			});
		} else {
			// Clear HS code if commodity is cleared
			frappe.model.set_value(cdt, cdn, 'hs_code', '');
		}
	},

	// Trigger aggregation when package volume changes
	volume: function(frm, cdt, cdn) {
		frm.trigger('aggregate_volume_from_packages');
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},

	// Trigger aggregation when package weight changes
	weight: function(frm, cdt, cdn) {
		frm.trigger('aggregate_volume_from_packages');
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},

	weight_uom: function(frm, cdt, cdn) {
		setTimeout(function() {
			frm.trigger('aggregate_volume_from_packages');
			_calculate_package_chargeable_weight(frm, cdt, cdn);
		}, 100);
	},

	// Ensure global volume-from-dimensions runs (same as measurements_uom_conversion.js)
	length: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	width: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	height: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	dimension_uom: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	volume_uom: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); }
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

function _calculate_package_chargeable_weight(frm, cdt, cdn) {
	// Calculate chargeable weight for a package row in the child table
	let row = locals[cdt][cdn];
	if (!row) return;
	
	if (!row.weight && !row.volume) {
		frappe.model.set_value(cdt, cdn, 'chargeable_weight', 0);
		return;
	}
	
	// Get divisor from parent Air Booking
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
				_calculate_and_set_package_chargeable_weight(frm, cdt, cdn, divisor);
			});
			return; // Will continue in callback
		}
	}
	
	_calculate_and_set_package_chargeable_weight(frm, cdt, cdn, divisor);
}

function _calculate_and_set_package_chargeable_weight(frm, cdt, cdn, divisor) {
	let row = locals[cdt][cdn];
	if (!row) return;
	
	let volume_weight = 0;
	let chargeable = 0;
	const package_volume = parseFloat(row.volume || 0);
	const package_weight = parseFloat(row.weight || 0);
	
	// Note: Volume should already be in m³ from the conversion system
	// Calculate volume weight: volume (m³) * 1,000,000 / divisor
	if (package_volume > 0 && divisor) {
		volume_weight = package_volume * (1000000.0 / divisor);
	}
	
	// Chargeable weight is higher of actual weight or volume weight
	if (package_weight > 0 && volume_weight > 0) {
		chargeable = Math.max(package_weight, volume_weight);
	} else if (package_weight > 0) {
		chargeable = package_weight;
	} else if (volume_weight > 0) {
		chargeable = volume_weight;
	}
	
	frappe.model.set_value(cdt, cdn, 'chargeable_weight', chargeable);
	
	// Set chargeable_weight_uom to match weight_uom if not set
	if (!row.chargeable_weight_uom && row.weight_uom) {
		frappe.model.set_value(cdt, cdn, 'chargeable_weight_uom', row.weight_uom);
	}
}

// Setup query filter for quote field to exclude already-used One-Off Quotes and filter by is_air
function _setup_quote_query(frm) {
	if (frm.doc.quote_type === 'One-Off Quote') {
		// Load available One-Off Quotes filters
		frappe.call({
			method: 'logistics.air_freight.doctype.air_booking.air_booking.get_available_one_off_quotes',
			args: { air_booking_name: frm.doc.name || null },
			callback: function(r) {
				if (r.message && r.message.filters) {
					frm._available_one_off_quotes_filters = r.message.filters;
				}
			}
		});
		
		// Set query filter for quote field
		frm.set_query('quote', function() {
			// Return cached filters or empty filters
			// If filters not loaded yet, they'll be empty but that's okay
			// The user can still type and select, validation will catch duplicates
			return { 
				filters: frm._available_one_off_quotes_filters || {} 
			};
		});
	} else if (frm.doc.quote_type === 'Sales Quote') {
		// For Sales Quote, filter by is_air = 1
		frm.set_query('quote', function() {
			return { 
				filters: { is_air: 1 } 
			};
		});
	}
}

function _populate_charges_from_quote(frm) {
	var docname = frm.is_new() ? null : frm.doc.name;
	var quote_type = frm.doc.quote_type;
	var quote = frm.doc.quote;
	var sales_quote = frm.doc.sales_quote;
	
	// Determine which quote to use
	var target_quote = null;
	var method_name = null;
	var freeze_message = null;
	var success_message_template = null;
	
	if (quote_type === 'Sales Quote' && quote) {
		target_quote = quote;
		method_name = "logistics.air_freight.doctype.air_booking.air_booking.populate_charges_from_sales_quote";
		freeze_message = __("Fetching charges from Sales Quote...");
		success_message_template = __("Successfully populated {0} charges from Sales Quote: {1}");
	} else if (quote_type === 'One-Off Quote' && quote) {
		target_quote = quote;
		method_name = "logistics.air_freight.doctype.air_booking.air_booking.populate_charges_from_one_off_quote";
		freeze_message = __("Fetching charges from One-Off Quote...");
		success_message_template = __("Successfully populated {0} charges from One-Off Quote: {1}");
	} else if (sales_quote) {
		// Fallback to sales_quote field for backward compatibility
		target_quote = sales_quote;
		method_name = "logistics.air_freight.doctype.air_booking.air_booking.populate_charges_from_sales_quote";
		freeze_message = __("Fetching charges from Sales Quote...");
		success_message_template = __("Successfully populated {0} charges from Sales Quote: {1}");
	}
	
	if (!target_quote || !method_name) {
		frm.clear_table('charges');
		frm.refresh_field('charges');
		return;
	}
	
	// Determine which parameter to pass based on the method being called
	var args = { docname: docname };
	if (method_name.includes('populate_charges_from_sales_quote')) {
		args.sales_quote = target_quote;
	} else if (method_name.includes('populate_charges_from_one_off_quote')) {
		args.one_off_quote = target_quote;
	}
	
	frappe.call({
		method: method_name,
		args: args,
		freeze: true,
		freeze_message: freeze_message,
		callback: function(r) {
			if (r.message) {
				if (r.message.error) {
					frappe.msgprint({
						title: __("Error"),
						message: r.message.error,
						indicator: 'red'
					});
					return;
				}
				if (r.message.message) {
					frappe.msgprint({
						title: __("No Charges Found"),
						message: r.message.message,
						indicator: 'orange'
					});
				}
				// Update charges on the form (works for both new and saved documents)
				// This avoids "document has been modified" errors by not saving on server
				if (r.message.charges && r.message.charges.length > 0) {
					frm.clear_table('charges');
					r.message.charges.forEach(function(charge) {
						var row = frm.add_child('charges');
						Object.keys(charge).forEach(function(key) {
							if (charge[key] !== null && charge[key] !== undefined) {
								row[key] = charge[key];
							}
						});
					});
					frm.refresh_field('charges');
					if (r.message.charges_count > 0) {
						var message = success_message_template;
						if (quote_type === 'One-Off Quote') {
							message = __("Successfully populated {0} charges from One-Off Quote: {1}", [r.message.charges_count, target_quote]);
						} else {
							message = __("Successfully populated {0} charges from Sales Quote: {1}", [r.message.charges_count, target_quote]);
						}
						frappe.msgprint({
							title: __("Charges Updated"),
							message: message,
							indicator: 'green'
						});
					}
				} else {
					frm.clear_table('charges');
					frm.refresh_field('charges');
				}
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to populate charges from quote."),
				indicator: 'red'
			});
		}
	});
}