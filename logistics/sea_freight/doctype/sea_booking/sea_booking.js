// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

// Suppress "Sea Booking X not found" when form is new/unsaved (e.g. package grid triggers API before save)
frappe.ui.form.on('Sea Booking', {
	onload: function(frm) {
		if (frm.is_new() || frm.doc.__islocal) {
			if (!frappe._original_msgprint) {
				frappe._original_msgprint = frappe.msgprint;
			}
			frappe.msgprint = function(options) {
				const message = typeof options === 'string' ? options : (options && options.message || '');
				if (message && typeof message === 'string' &&
					message.includes('Sea Booking') &&
					message.includes('not found')) {
					return;
				}
				return frappe._original_msgprint.apply(this, arguments);
			};
			frm.$wrapper.one('form-refresh', function() {
				if (!frm.is_new() && !frm.doc.__islocal && frappe._original_msgprint) {
					frappe.msgprint = frappe._original_msgprint;
				}
			});
		}
	},
	setup: function(frm) {
		// Filter address/contact by selected shipper/consignee (via Dynamic Link)
		frm.set_query('shipper_address', function() {
			if (frm.doc.shipper) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Shipper'], ['Dynamic Link', 'link_name', '=', frm.doc.shipper]] };
			}
			return {};
		});
		frm.set_query('shipper_contact', function() {
			if (frm.doc.shipper) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Shipper'], ['Dynamic Link', 'link_name', '=', frm.doc.shipper]] };
			}
			return {};
		});
		frm.set_query('consignee_address', function() {
			if (frm.doc.consignee) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Consignee'], ['Dynamic Link', 'link_name', '=', frm.doc.consignee]] };
			}
			return {};
		});
		frm.set_query('consignee_contact', function() {
			if (frm.doc.consignee) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Consignee'], ['Dynamic Link', 'link_name', '=', frm.doc.consignee]] };
			}
			return {};
		});
	},
	
	shipper: function(frm) {
		// Populate address/contact from shipper primary when shipper changes
		if (!frm.doc.shipper) {
			frm.set_value('shipper_address', '');
			frm.set_value('shipper_address_display', '');
			frm.set_value('shipper_contact', '');
			frm.set_value('shipper_contact_display', '');
			return;
		}
		frappe.db.get_value('Shipper', frm.doc.shipper, ['shipper_primary_address', 'shipper_primary_contact'], function(r) {
			if (r && r.shipper_primary_address) {
				frm.set_value('shipper_address', r.shipper_primary_address);
				frm.trigger('shipper_address');
			}
			if (r && r.shipper_primary_contact) {
				frm.set_value('shipper_contact', r.shipper_primary_contact);
				frm.trigger('shipper_contact');
			}
		});
	},
	
	consignee: function(frm) {
		// Populate address/contact from consignee primary when consignee changes
		if (!frm.doc.consignee) {
			frm.set_value('consignee_address', '');
			frm.set_value('consignee_address_display', '');
			frm.set_value('consignee_contact', '');
			frm.set_value('consignee_contact_display', '');
			return;
		}
		frappe.db.get_value('Consignee', frm.doc.consignee, ['consignee_primary_address', 'consignee_primary_contact'], function(r) {
			if (r && r.consignee_primary_address) {
				frm.set_value('consignee_address', r.consignee_primary_address);
				frm.trigger('consignee_address');
			}
			if (r && r.consignee_primary_contact) {
				frm.set_value('consignee_contact', r.consignee_primary_contact);
				frm.trigger('consignee_contact');
			}
		});
	},
	
	shipper_address: function(frm) {
		if (frm.doc.shipper_address) {
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: { address_dict: frm.doc.shipper_address },
				callback: function(r) {
					frm.set_value('shipper_address_display', r.message || '');
				}
			});
		} else {
			frm.set_value('shipper_address_display', '');
		}
	},
	
	consignee_address: function(frm) {
		if (frm.doc.consignee_address) {
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: { address_dict: frm.doc.consignee_address },
				callback: function(r) {
					frm.set_value('consignee_address_display', r.message || '');
				}
			});
		} else {
			frm.set_value('consignee_address_display', '');
		}
	},
	
	shipper_contact: function(frm) {
		if (frm.doc.shipper_contact) {
			frappe.call({
				method: 'frappe.client.get',
				args: { doctype: 'Contact', name: frm.doc.shipper_contact },
				callback: function(r) {
					if (r.message) {
						const c = r.message;
						let txt = [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name;
						if (c.designation) txt += '\n' + c.designation;
						if (c.phone) txt += '\n' + c.phone;
						if (c.mobile_no) txt += '\n' + c.mobile_no;
						if (c.email_id) txt += '\n' + c.email_id;
						frm.set_value('shipper_contact_display', txt);
					} else {
						frm.set_value('shipper_contact_display', '');
					}
				}
			});
		} else {
			frm.set_value('shipper_contact_display', '');
		}
	},
	
	consignee_contact: function(frm) {
		if (frm.doc.consignee_contact) {
			frappe.call({
				method: 'frappe.client.get',
				args: { doctype: 'Contact', name: frm.doc.consignee_contact },
				callback: function(r) {
					if (r.message) {
						const c = r.message;
						let txt = [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name;
						if (c.designation) txt += '\n' + c.designation;
						if (c.phone) txt += '\n' + c.phone;
						if (c.mobile_no) txt += '\n' + c.mobile_no;
						if (c.email_id) txt += '\n' + c.email_id;
						frm.set_value('consignee_contact_display', txt);
					} else {
						frm.set_value('consignee_contact_display', '');
					}
				}
			});
		} else {
			frm.set_value('consignee_contact_display', '');
		}
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
	
	override_volume_weight: function(frm) {
		_update_measurement_fields_readonly(frm);
		if (frm.is_new() || frm.doc.__islocal) return;
		if (!frm.doc.override_volume_weight) {
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
						if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
						if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
						_set_packing_summary_from_response(frm, r.message);
					}
				}
			});
		}
	},
	
	refresh: function(frm) {
		// Populate Documents from Template
		if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
			frm.add_custom_button(__('Populate from Template'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_documents_from_template',
					args: { doctype: 'Sea Booking', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Documents'));
		}

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
					__('Are you sure you want to convert this Sea Booking to a Sea Shipment?'),
					function() {
						frm.call({
							method: 'convert_to_shipment',
							doc: frm.doc,
							callback: function(r) {
								if (r.exc) return;
								if (r.message && r.message.success && r.message.sea_shipment) {
									// Reload form and show link - avoid "not found" by not auto-navigating
									frm.reload_doc();
									frappe.show_alert({
										message: __('Sea Shipment {0} created. <a href="#Form/Sea Shipment/{1}">Open</a>', [r.message.sea_shipment, r.message.sea_shipment]),
										indicator: 'green'
									}, 10);
								}
							}
						});
					}
				);
			}, __('Actions'));
		}
		
		// Setup query filter for quote field based on quote_type
		_setup_quote_query(frm);
		
		// Update read-only status of measurement fields
		_update_measurement_fields_readonly(frm);
		
		// Populate address/contact display fields when missing (e.g. loading older docs)
		_populate_address_contact_displays_if_missing(frm);
	}
});

function _populate_address_contact_displays_if_missing(frm) {
	if (frm.doc.shipper_address && !frm.doc.shipper_address_display) {
		frm.trigger('shipper_address');
	}
	if (frm.doc.consignee_address && !frm.doc.consignee_address_display) {
		frm.trigger('consignee_address');
	}
	if (frm.doc.shipper_contact && !frm.doc.shipper_contact_display) {
		frm.trigger('shipper_contact');
	}
	if (frm.doc.consignee_contact && !frm.doc.consignee_contact_display) {
		frm.trigger('consignee_contact');
	}
}

// Setup query filter for quote field to exclude already-used One-Off Quotes and filter by is_sea
function _setup_quote_query(frm) {
	if (frm.doc.quote_type === 'One-Off Quote') {
		// Load available One-Off Quotes filters
		frappe.call({
			method: 'logistics.sea_freight.doctype.sea_booking.sea_booking.get_available_one_off_quotes',
			args: { sea_booking_name: frm.doc.name || null },
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
		// For Sales Quote, filter by is_sea = 1
		frm.set_query('quote', function() {
			return { 
				filters: { is_sea: 1 } 
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
		method_name = "logistics.sea_freight.doctype.sea_booking.sea_booking.populate_charges_from_sales_quote";
		freeze_message = __("Fetching charges from Sales Quote...");
		success_message_template = __("Successfully populated {0} charges from Sales Quote: {1}");
	} else if (quote_type === 'One-Off Quote' && quote) {
		target_quote = quote;
		method_name = "logistics.sea_freight.doctype.sea_booking.sea_booking.populate_charges_from_one_off_quote";
		freeze_message = __("Fetching charges from One-Off Quote...");
		success_message_template = __("Successfully populated {0} charges from One-Off Quote: {1}");
	} else if (sales_quote) {
		// Fallback to sales_quote field for backward compatibility
		target_quote = sales_quote;
		method_name = "logistics.sea_freight.doctype.sea_booking.sea_booking.populate_charges_from_sales_quote";
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

// Sea Booking Packages: ensure global volume-from-dimensions runs and header aggregates
frappe.ui.form.on('Sea Booking Packages', {
	volume: function(frm) {
		if (frm.is_new() || frm.doc.__islocal) return;
		if (frm.doc && !frm.doc.override_volume_weight) {
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
						if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
						if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
						_set_packing_summary_from_response(frm, r.message);
					}
				}
			});
		}
	},
	weight: function(frm) {
		if (frm.is_new() || frm.doc.__islocal) return;
		if (frm.doc && !frm.doc.override_volume_weight) {
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
						if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
						if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
						_set_packing_summary_from_response(frm, r.message);
					}
				}
			});
		}
	},
	length: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	width: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	height: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	dimension_uom: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	volume_uom: function(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); }
});

// Sea Booking Containers: refresh packing summary (total_containers, total_teus, etc.) when containers change
function _refresh_packing_summary_api(frm) {
	frm.call({
		method: 'aggregate_volume_from_packages_api',
		doc: frm.doc,
		callback: function(r) {
			if (r && !r.exc && r.message) {
				if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
				if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
				if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
				_set_packing_summary_from_response(frm, r.message);
			}
		}
	});
}

frappe.ui.form.on('Sea Booking Containers', {
	type: function(frm) {
		_refresh_packing_summary_api(frm);
	},
	form_render: function(frm) {
		// Debounce so add/remove row doesn't trigger multiple calls
		if (frm._packing_summary_refresh_timer) clearTimeout(frm._packing_summary_refresh_timer);
		frm._packing_summary_refresh_timer = setTimeout(function() {
			frm._packing_summary_refresh_timer = null;
			_refresh_packing_summary_api(frm);
		}, 300);
	}
});

// Set packing summary fields (total_containers, total_teus, total_packages) from API response
function _set_packing_summary_from_response(frm, message) {
	if (!message) return;
	var keys = ['total_containers', 'total_teus', 'total_packages'];
	keys.forEach(function(key) {
		if (message[key] !== undefined) frm.set_value(key, message[key]);
	});
}

// Update read-only status of measurement fields based on override_volume_weight
function _update_measurement_fields_readonly(frm) {
	var readonly = !frm.doc.override_volume_weight;
	frm.set_df_property('volume', 'read_only', readonly);
	frm.set_df_property('weight', 'read_only', readonly);
	frm.set_df_property('chargeable', 'read_only', readonly);
}
