// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: triggers for volume-from-dimensions (uses global logistics_calculate_volume_from_dimensions).

// Global function to calculate volume from dimensions (if not already defined)
if (typeof logistics_calculate_volume_from_dimensions === 'undefined') {
	logistics_calculate_volume_from_dimensions = function(frm, cdt, cdn) {
		// Get the document row (for child tables) or form doc (for main forms)
		var doc = null;
		if (cdt && cdn) {
			// Child table row
			doc = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
		} else if (frm && frm.doc) {
			// Main form
			doc = frm.doc;
		}
		
		if (!doc) return;
		
		var length = parseFloat(doc.length || 0);
		var width = parseFloat(doc.width || 0);
		var height = parseFloat(doc.height || 0);
		
		// Only calculate if all dimensions are provided and > 0
		if (length > 0 && width > 0 && height > 0) {
			var dimension_uom = doc.dimension_uom;
			var volume_uom = doc.volume_uom;
			var company = null;
			
			// Try to get company from parent Air Booking (works with both saved and unsaved parents)
			if (doc.parenttype === 'Air Booking' && doc.parent) {
				// Skip if parent name is still temporary (starts with "new-")
				if (doc.parent && doc.parent.startsWith && doc.parent.startsWith('new-')) {
					// Parent is unsaved, use form's company or user default
					company = _get_company_from_form_or_defaults(frm, doc);
					_calculate_volume_from_dimensions_api(length, width, height, dimension_uom, volume_uom, company, frm, cdt, cdn);
				} else {
					// Try to get from database first
					frappe.db.get_value('Air Booking', doc.parent, 'company', function(r) {
						if (r && r.company) {
							company = r.company;
						} else {
							// Parent might be unsaved, try form or defaults
							company = _get_company_from_form_or_defaults(frm, doc);
						}
						_calculate_volume_from_dimensions_api(length, width, height, dimension_uom, volume_uom, company, frm, cdt, cdn);
					});
				}
			} else {
				// Try to get company from current form or defaults
				company = _get_company_from_form_or_defaults(frm, doc);
				_calculate_volume_from_dimensions_api(length, width, height, dimension_uom, volume_uom, company, frm, cdt, cdn);
			}
		} else {
			// Set volume to 0 if dimensions are missing
			if (cdt && cdn) {
				frappe.model.set_value(cdt, cdn, 'volume', 0);
			} else if (frm) {
				frm.set_value('volume', 0);
			}
		}
	};
}

// Helper function to get company from form or defaults
function _get_company_from_form_or_defaults(frm, doc) {
	// Try to get from parent form's doc if available (for unsaved parents)
	if (frm && frm.doc && frm.doc.company) {
		return frm.doc.company;
	}
	// Try to get from parent form if this is a child table row
	if (frm && frm.doctype === 'Air Booking' && frm.doc && frm.doc.company) {
		return frm.doc.company;
	}
	// Fallback to user default
	try {
		return frappe.defaults.get_user_default("Company");
	} catch (e) {
		return null;
	}
}

// Helper function to call the server-side API
function _calculate_volume_from_dimensions_api(length, width, height, dimension_uom, volume_uom, company, frm, cdt, cdn) {
	frappe.call({
		method: "logistics.utils.measurements.calculate_volume_from_dimensions_api",
		args: {
			length: length,
			width: width,
			height: height,
			dimension_uom: dimension_uom,
			volume_uom: volume_uom,
			company: company
		},
		freeze: false,
		callback: function(r) {
			if (r && r.message) {
				var volume = r.message.volume;
				var has_error = r.message.error;
				
				// If volume is 0 and there's an error, try fallback calculation
				if ((volume === 0 || volume === undefined) && has_error) {
					console.warn('Volume calculation returned 0 with error:', has_error);
					// Always try fallback when API fails
					_try_fallback_volume_calculation(frm, cdt, cdn);
					return;
				}
				
				// Set volume if we have a valid value
				if (volume !== undefined) {
					if (cdt && cdn) {
						frappe.model.set_value(cdt, cdn, 'volume', volume);
						// Trigger parent aggregation after volume is set (with small delay to ensure value is set)
						if (cdt === 'Air Booking Packages') {
							setTimeout(function() {
								// Get parent form and trigger aggregation
								var parent_frm = frappe.ui.form.get_cur_frm();
								if (parent_frm && parent_frm.doc && !parent_frm.doc.override_volume_weight && !parent_frm.is_new() && !parent_frm.doc.__islocal) {
									parent_frm.call({
										method: 'aggregate_volume_from_packages_api',
										doc: parent_frm.doc,
										callback: function(r) {
											if (r && !r.exc && r.message) {
												if (r.message.volume !== undefined) parent_frm.set_value('volume', r.message.volume);
												if (r.message.weight !== undefined) parent_frm.set_value('weight', r.message.weight);
												if (r.message.chargeable !== undefined) parent_frm.set_value('chargeable', r.message.chargeable);
											}
										}
									});
								}
							}, 100);
						}
					} else if (frm) {
						frm.set_value('volume', volume);
					}
				} else if (has_error) {
					// No volume returned but there's an error - try fallback
					console.warn('Volume calculation error:', has_error);
					_try_fallback_volume_calculation(frm, cdt, cdn);
				}
			} else {
				// No response message - try fallback
				_try_fallback_volume_calculation(frm, cdt, cdn);
			}
		},
		error: function(r) {
			console.error('Volume calculation API error:', r);
			// Always try fallback calculation on error
			_try_fallback_volume_calculation(frm, cdt, cdn);
		}
	});
}

frappe.ui.form.on('Air Booking Packages', {
	refresh: function(frm) {
		// Recompute volume from dimensions when form loads (e.g. child form in dialog)
		if (frm.doc && (frm.doc.length || frm.doc.width || frm.doc.height)) {
			var cdt = frm.doctype || 'Air Booking Packages';
			var cdn = (frm.doc && frm.doc.name) ? frm.doc.name : null;
			if (!cdn) return;
			if (typeof logistics_calculate_volume_from_dimensions === 'function') {
				logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			}
		}
		// Calculate chargeable weight when form loads
		if (frm.doc && (frm.doc.weight || frm.doc.volume)) {
			var cdt = frm.doctype || 'Air Booking Packages';
			var cdn = (frm.doc && frm.doc.name) ? frm.doc.name : null;
			_calculate_package_chargeable_weight(frm, cdt, cdn);
		}
	},
	length: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	width: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	height: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	dimension_uom: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	volume_uom: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	volume: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	weight: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	weight_uom: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	}
});

function _calculate_package_chargeable_weight(frm, cdt, cdn) {
	// Calculate chargeable weight for a package row in the child table
	// For child table rows, cdt and cdn are required
	if (cdt && cdn) {
		// Child table row - use locals to get row data
		var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
		if (!row) {
			return;
		}
		
		var package_volume = parseFloat(row.volume || 0) || 0;
		var package_weight = parseFloat(row.weight || 0) || 0;
		
		// If both volume and weight are zero or missing, set chargeable weight to 0
		if (package_volume <= 0 && package_weight <= 0) {
			frappe.model.set_value(cdt, cdn, 'chargeable_weight', 0);
			return;
		}
		
		// Get parent Air Booking name from row
		var parent_name = row.parent;
		if (!parent_name) {
			// Try to get from form if available
			if (frm && frm.doc && frm.doc.name) {
				parent_name = frm.doc.name;
			} else {
				// Can't get parent name, use default divisor
				var company = _get_company_from_form_or_defaults(frm, row);
				_calculate_and_set_package_chargeable_weight(cdt, cdn, 6000, company);
				return;
			}
		}
		
		// Skip if parent name is still temporary (starts with "new-")
		if (parent_name && parent_name.startsWith && parent_name.startsWith('new-')) {
			// Parent is unsaved, use default divisor and form's company
			var company = _get_company_from_form_or_defaults(frm, row);
			_calculate_and_set_package_chargeable_weight(cdt, cdn, 6000, company);
			return;
		}
		
		// Get divisor from parent Air Booking
		frappe.db.get_value('Air Booking', parent_name, [
			'volume_to_weight_factor_type',
			'custom_volume_to_weight_divisor',
			'airline',
			'company'
		], function(r) {
			// Get latest row state to avoid stale data
			var current_row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
			if (!current_row) return;
			
			var divisor = 6000; // Default IATA
			var company = null;
			
			if (r) {
				var factor_type = r.volume_to_weight_factor_type || 'IATA';
				company = r.company;
				
				if (factor_type === 'IATA') {
					divisor = 6000;
				} else if (factor_type === 'Custom') {
					if (r.custom_volume_to_weight_divisor) {
						divisor = parseFloat(r.custom_volume_to_weight_divisor) || 6000;
					} else if (r.airline) {
						// Fetch airline divisor
						frappe.db.get_value('Airline', r.airline, 'volume_to_weight_divisor', function(airline_r) {
							if (airline_r && airline_r.volume_to_weight_divisor) {
								divisor = parseFloat(airline_r.volume_to_weight_divisor) || 6000;
							}
							if (!company) {
								company = _get_company_from_form_or_defaults(frm, current_row);
							}
							_calculate_and_set_package_chargeable_weight(cdt, cdn, divisor, company);
						});
						return; // Will continue in callback
					}
				}
			} else {
				// Parent doesn't exist (unsaved), use defaults
				company = _get_company_from_form_or_defaults(frm, current_row);
			}
			
			if (!company) {
				company = _get_company_from_form_or_defaults(frm, current_row);
			}
			_calculate_and_set_package_chargeable_weight(cdt, cdn, divisor, company);
		});
	} else if (frm && frm.doc) {
		// Standalone form (not a child table row) - handle differently
		var package_volume = parseFloat(frm.doc.volume || 0) || 0;
		var package_weight = parseFloat(frm.doc.weight || 0) || 0;
		
		if (package_volume <= 0 && package_weight <= 0) {
			frm.set_value('chargeable_weight', 0);
			return;
		}
		
		var parent_name = frm.doc.parent;
		if (!parent_name) {
			return; // Can't calculate without parent
		}
		
		// Get divisor from parent Air Booking
		frappe.db.get_value('Air Booking', parent_name, [
			'volume_to_weight_factor_type',
			'custom_volume_to_weight_divisor',
			'airline',
			'company'
		], function(r) {
			if (!r) return;
			
			var divisor = 6000; // Default IATA
			var factor_type = r.volume_to_weight_factor_type || 'IATA';
			
			if (factor_type === 'IATA') {
				divisor = 6000;
			} else if (factor_type === 'Custom') {
				if (r.custom_volume_to_weight_divisor) {
					divisor = parseFloat(r.custom_volume_to_weight_divisor) || 6000;
				} else if (r.airline) {
					// Fetch airline divisor
					frappe.db.get_value('Airline', r.airline, 'volume_to_weight_divisor', function(airline_r) {
						if (airline_r && airline_r.volume_to_weight_divisor) {
							divisor = parseFloat(airline_r.volume_to_weight_divisor) || 6000;
						}
						_calculate_and_set_package_chargeable_weight_standalone(frm, divisor, r.company);
					});
					return; // Will continue in callback
				}
			}
			
			_calculate_and_set_package_chargeable_weight_standalone(frm, divisor, r.company);
		});
	}
}

function _calculate_and_set_package_chargeable_weight(cdt, cdn, divisor, company) {
	// Get latest row state to avoid stale data
	var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	if (!row) return;
	
	var package_volume = parseFloat(row.volume || 0) || 0;
	var package_weight = parseFloat(row.weight || 0) || 0;
	
	// Convert volume to m³ if needed (matching Python implementation)
	var volume_in_m3 = package_volume;
	if (package_volume > 0 && row.volume_uom) {
		// Get default volume UOM (typically "M³") and convert if needed
		var volume_uom = row.volume_uom;
		
		if (!company) {
			company = frappe.defaults.get_user_default("Company");
		}
		
		_convert_volume_to_m3_and_calculate(package_volume, volume_uom, company, package_weight, divisor, cdt, cdn);
	} else {
		// No volume UOM or no volume, calculate directly assuming m³
		_calculate_chargeable_weight_from_volume_m3(volume_in_m3, package_weight, divisor, cdt, cdn);
	}
}

function _calculate_and_set_package_chargeable_weight_standalone(frm, divisor, company) {
	var package_volume = parseFloat(frm.doc.volume || 0) || 0;
	var package_weight = parseFloat(frm.doc.weight || 0) || 0;
	
	// Convert volume to m³ if needed (matching Python implementation)
	var volume_in_m3 = package_volume;
	if (package_volume > 0 && frm.doc.volume_uom) {
		// Get default volume UOM (typically "M³") and convert if needed
		var volume_uom = frm.doc.volume_uom;
		
		if (!company) {
			company = frappe.defaults.get_user_default("Company");
		}
		
		_convert_volume_to_m3_and_calculate_standalone(package_volume, volume_uom, company, package_weight, divisor, frm);
	} else {
		// No volume UOM or no volume, calculate directly assuming m³
		_calculate_chargeable_weight_from_volume_m3_standalone(volume_in_m3, package_weight, divisor, frm);
	}
}

function _convert_volume_to_m3_and_calculate(package_volume, volume_uom, company, package_weight, divisor, cdt, cdn) {
	// Get default volume UOM (typically "M³")
	frappe.call({
		method: "logistics.warehousing.doctype.warehouse_settings.warehouse_settings.get_default_uoms",
		args: { company: company },
		freeze: false,
		callback: function(r) {
			var target_volume_uom = null;
			if (r && r.message && r.message.volume) {
				target_volume_uom = r.message.volume;
			}
			
			var volume_in_m3 = package_volume;
			
			// Convert to m³ if volume_uom is different from target
			if (volume_uom && target_volume_uom && 
				volume_uom.toString().trim().toUpperCase() !== target_volume_uom.toString().trim().toUpperCase()) {
				// Get conversion factor from UOM Conversion Factor table
				frappe.db.get_value('UOM Conversion Factor', {
					'from_uom': volume_uom,
					'to_uom': target_volume_uom
				}, 'value', function(conv_r) {
					if (conv_r && conv_r.value) {
						volume_in_m3 = package_volume * parseFloat(conv_r.value);
					} else {
						// Try reverse direction
						frappe.db.get_value('UOM Conversion Factor', {
							'from_uom': target_volume_uom,
							'to_uom': volume_uom
						}, 'value', function(rev_conv_r) {
							if (rev_conv_r && rev_conv_r.value) {
								volume_in_m3 = package_volume / parseFloat(rev_conv_r.value);
							}
							_calculate_chargeable_weight_from_volume_m3(volume_in_m3, package_weight, divisor, cdt, cdn);
						});
						return; // Will continue in callback
					}
					_calculate_chargeable_weight_from_volume_m3(volume_in_m3, package_weight, divisor, cdt, cdn);
				});
			} else {
				// Already in m³ or no conversion needed
				_calculate_chargeable_weight_from_volume_m3(volume_in_m3, package_weight, divisor, cdt, cdn);
			}
		},
		error: function() {
			// On error, assume volume is already in m³
			_calculate_chargeable_weight_from_volume_m3(package_volume, package_weight, divisor, cdt, cdn);
		}
	});
}

function _convert_volume_to_m3_and_calculate_standalone(package_volume, volume_uom, company, package_weight, divisor, frm) {
	// Get default volume UOM (typically "M³")
	frappe.call({
		method: "logistics.warehousing.doctype.warehouse_settings.warehouse_settings.get_default_uoms",
		args: { company: company },
		freeze: false,
		callback: function(r) {
			var target_volume_uom = null;
			if (r && r.message && r.message.volume) {
				target_volume_uom = r.message.volume;
			}
			
			var volume_in_m3 = package_volume;
			
			// Convert to m³ if volume_uom is different from target
			if (volume_uom && target_volume_uom && 
				volume_uom.toString().trim().toUpperCase() !== target_volume_uom.toString().trim().toUpperCase()) {
				// Get conversion factor from UOM Conversion Factor table
				frappe.db.get_value('UOM Conversion Factor', {
					'from_uom': volume_uom,
					'to_uom': target_volume_uom
				}, 'value', function(conv_r) {
					if (conv_r && conv_r.value) {
						volume_in_m3 = package_volume * parseFloat(conv_r.value);
					} else {
						// Try reverse direction
						frappe.db.get_value('UOM Conversion Factor', {
							'from_uom': target_volume_uom,
							'to_uom': volume_uom
						}, 'value', function(rev_conv_r) {
							if (rev_conv_r && rev_conv_r.value) {
								volume_in_m3 = package_volume / parseFloat(rev_conv_r.value);
							}
							_calculate_chargeable_weight_from_volume_m3_standalone(volume_in_m3, package_weight, divisor, frm);
						});
						return; // Will continue in callback
					}
					_calculate_chargeable_weight_from_volume_m3_standalone(volume_in_m3, package_weight, divisor, frm);
				});
			} else {
				// Already in m³ or no conversion needed
				_calculate_chargeable_weight_from_volume_m3_standalone(volume_in_m3, package_weight, divisor, frm);
			}
		},
		error: function() {
			// On error, assume volume is already in m³
			_calculate_chargeable_weight_from_volume_m3_standalone(package_volume, package_weight, divisor, frm);
		}
	});
}

function _calculate_chargeable_weight_from_volume_m3(volume_in_m3, package_weight, divisor, cdt, cdn) {
	// Get latest row state to avoid stale data
	var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	if (!row) return;
	
	var volume_weight = 0;
	var chargeable = 0;
	
	// Calculate volume weight: volume (m³) * 1,000,000 / divisor
	if (volume_in_m3 > 0 && divisor && divisor > 0) {
		volume_weight = volume_in_m3 * (1000000.0 / divisor);
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

function _calculate_chargeable_weight_from_volume_m3_standalone(volume_in_m3, package_weight, divisor, frm) {
	var volume_weight = 0;
	var chargeable = 0;
	
	// Calculate volume weight: volume (m³) * 1,000,000 / divisor
	if (volume_in_m3 > 0 && divisor && divisor > 0) {
		volume_weight = volume_in_m3 * (1000000.0 / divisor);
	}
	
	// Chargeable weight is higher of actual weight or volume weight
	if (package_weight > 0 && volume_weight > 0) {
		chargeable = Math.max(package_weight, volume_weight);
	} else if (package_weight > 0) {
		chargeable = package_weight;
	} else if (volume_weight > 0) {
		chargeable = volume_weight;
	}
	
	frm.set_value('chargeable_weight', chargeable);
	
	// Set chargeable_weight_uom to match weight_uom if not set
	if (!frm.doc.chargeable_weight_uom && frm.doc.weight_uom) {
		frm.set_value('chargeable_weight_uom', frm.doc.weight_uom);
	}
}

// Fallback volume calculation when conversion factors are missing
function _try_fallback_volume_calculation(frm, cdt, cdn) {
	// Get latest row state
	var doc = null;
	if (cdt && cdn) {
		doc = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	} else if (frm && frm.doc) {
		doc = frm.doc;
	}
	
	if (!doc) return;
	
	var length = parseFloat(doc.length || 0);
	var width = parseFloat(doc.width || 0);
	var height = parseFloat(doc.height || 0);
	var dimension_uom = doc.dimension_uom;
	var volume_uom = doc.volume_uom;
	
	// Only calculate if all dimensions are provided and > 0
	if (length <= 0 || width <= 0 || height <= 0) {
		return;
	}
	
	// Calculate raw volume
	var raw_volume = length * width * height;
	
	// If dimension and volume UOMs are the same (case-insensitive), use raw volume
	if (dimension_uom && volume_uom) {
		var dim_upper = dimension_uom.toString().trim().toUpperCase();
		var vol_upper = volume_uom.toString().trim().toUpperCase();
		
		if (dim_upper === vol_upper) {
			_set_volume_value(frm, cdt, cdn, raw_volume);
			return;
		}
		
		// Try common conversion heuristics (matching Python implementation)
		var calculated_volume = raw_volume;
		
		// Centimeter to Cubic Meter: 1 cm³ = 0.000001 m³
		if ((dim_upper.indexOf('CENTIMETER') !== -1 || dim_upper === 'CM') && 
			(vol_upper.indexOf('CUBIC METER') !== -1 || vol_upper.indexOf('M³') !== -1 || vol_upper === 'M3')) {
			calculated_volume = raw_volume * 0.000001;
		}
		// Meter to Cubic Meter: 1 m³ = 1 m³ (same)
		else if ((dim_upper.indexOf('METER') !== -1 || dim_upper === 'M') && 
			(vol_upper.indexOf('CUBIC METER') !== -1 || vol_upper.indexOf('M³') !== -1 || vol_upper === 'M3')) {
			calculated_volume = raw_volume;
		}
		// Inch to Cubic Foot: 1 in³ = 0.000578704 ft³
		else if ((dim_upper.indexOf('INCH') !== -1 || dim_upper === 'IN') && 
			(vol_upper.indexOf('CUBIC FOOT') !== -1 || vol_upper.indexOf('FT³') !== -1 || vol_upper === 'CFT')) {
			calculated_volume = raw_volume * 0.000578704;
		}
		// Foot to Cubic Foot: 1 ft³ = 1 ft³ (same)
		else if ((dim_upper.indexOf('FOOT') !== -1 || dim_upper === 'FT') && 
			(vol_upper.indexOf('CUBIC FOOT') !== -1 || vol_upper.indexOf('FT³') !== -1 || vol_upper === 'CFT')) {
			calculated_volume = raw_volume;
		}
		// Otherwise use raw volume (may be incorrect but better than 0)
		else {
			console.warn('Using raw volume as fallback. UOMs may differ: dimension=' + dimension_uom + ', volume=' + volume_uom);
		}
		
		_set_volume_value(frm, cdt, cdn, calculated_volume);
		return;
	}
	
	// No UOMs available - use raw volume
	console.warn('No UOMs available, using raw volume as fallback');
	_set_volume_value(frm, cdt, cdn, raw_volume);
}

// Helper to set volume value
function _set_volume_value(frm, cdt, cdn, volume) {
	if (cdt && cdn) {
		frappe.model.set_value(cdt, cdn, 'volume', volume);
	} else if (frm) {
		frm.set_value('volume', volume);
	}
}
