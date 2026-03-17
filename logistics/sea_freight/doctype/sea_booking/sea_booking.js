// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Sea Booking', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	}).always(function() {
		setTimeout(function() { frm._milestone_html_called = false; }, 2000);
	});
}

function _sea_booking_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, grid_row, 'packages');
}

// Suppress "Sea Booking X not found" when form is new/unsaved (e.g. package grid triggers API before save)
frappe.ui.form.on('Sea Booking', {
	packages_on_form_rendered: function(frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(frm, 'Sea Booking Packages', 'packages', 'sea_booking_volume');
		}
	},
	document_list_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_documents_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				}
			});
		});
	},
	milestone_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_milestones_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				}
			});
		});
	},
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
		frm.set_query('milestone_template', function() {
			return frappe.call('logistics.document_management.api.get_milestone_template_filters', { doctype: frm.doctype })
				.then(function(r) { return r.message || { filters: [] }; });
		});
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
		frappe.db.get_value('Shipper', frm.doc.shipper, ['pick_address', 'shipper_primary_address', 'shipper_primary_contact'], function(r) {
			if (r && (r.pick_address || r.shipper_primary_address)) {
				frm.set_value('shipper_address', r.pick_address || r.shipper_primary_address);
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
		frappe.db.get_value('Consignee', frm.doc.consignee, ['delivery_address', 'consignee_primary_address', 'consignee_primary_contact'], function(r) {
			if (r && (r.delivery_address || r.consignee_primary_address)) {
				frm.set_value('consignee_address', r.delivery_address || r.consignee_primary_address);
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
		// Don't repopulate charges if we're in the middle of fetching quotations
		// or if charges already exist (to prevent clearing them on form reload)
		if (frm._fetching_quotations) {
			return;
		}
		// Only populate if sales_quote changed and we don't have charges yet
		// This prevents clearing charges when form reloads after fetch_quotations
		if (!frm.doc.charges || frm.doc.charges.length === 0) {
			_populate_charges_from_quote(frm);
		} else {
			// If charges exist, only populate if sales_quote actually changed
			// (not just on form load)
			var previous_sales_quote = frm._previous_sales_quote;
			if (previous_sales_quote !== frm.doc.sales_quote && frm.doc.sales_quote) {
				_populate_charges_from_quote(frm);
			}
		}
		frm._previous_sales_quote = frm.doc.sales_quote;
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
				freeze: false,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.total_volume !== undefined) frm.set_value('total_volume', r.message.total_volume);
						if (r.message.total_weight !== undefined) frm.set_value('total_weight', r.message.total_weight);
						if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
						_set_packing_summary_from_response(frm, r.message);
					}
				}
			});
		}
	},
	
	refresh: function(frm) {
		// Load dashboard HTML in Dashboard tab (only when doc is saved)
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frm.call('get_dashboard_html').then(r => {
					if (r.message && frm.fields_dict.dashboard_html) {
						frm.fields_dict.dashboard_html.$wrapper.html(r.message);
						if (window.logistics_group_and_collapse_dash_alerts) {
							setTimeout(function() {
								window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
							}, 100);
						}
						if (window.logistics_bind_document_alert_cards) {
							window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
						}
					}
				});
				setTimeout(() => { frm._dashboard_html_called = false; }, 2000);
			}
		}

		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
				_load_milestone_html(frm);
			});
		}

		// Load documents summary HTML in Documents tab
		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, "Sea Booking");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				if (window.logistics_load_documents_html) {
					window.logistics_load_documents_html(frm, "Sea Booking");
				}
			});
		}

		// --- Actions menu ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Sea Booking', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Actions'));
			frm.add_custom_button(__('Get Documents'), function() {
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
			}, __('Actions'));
			if (frm.doc.charges && frm.doc.charges.length > 0) {
				frm.add_custom_button(__('Calculate Charges'), function() {
					frappe.call({
						method: 'logistics.sea_freight.doctype.sea_booking.sea_booking.recalculate_all_charges',
						args: { docname: frm.doc.name },
						callback: function(r) {
							if (r.message && r.message.success) {
								frm.reload_doc();
								frappe.show_alert({ message: __(r.message.message), indicator: 'green' }, 3);
							}
						}
					});
				}, __('Actions'));
			}
		}

		// Add button to fetch quotations
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__('Fetch Quotations'), function() {
				// Set flag to prevent sales_quote handler from clearing charges
				frm._fetching_quotations = true;
				frm.call({
					method: 'fetch_quotations',
					doc: frm.doc,
					callback: function(r) {
						if (r.message && r.message.success) {
							// Reload the document to show the updated charges and other fields
							// Use reload_doc with callback to ensure charges are visible
							frm.reload_doc().then(function() {
								// Refresh charges field to ensure it's displayed
								if (frm.fields_dict.charges) {
									frm.refresh_field('charges');
								}
								// Clear flag after reload
								setTimeout(function() {
									frm._fetching_quotations = false;
								}, 1000);
							});
						} else {
							frm._fetching_quotations = false;
						}
					},
					error: function(r) {
						frm._fetching_quotations = false;
					}
				});
			}, __('Actions'));
		}

		// --- Create menu ---
		if (frm.doc.name && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			setTimeout(function() {
				frm.add_custom_button(__('Shipment'), function() {
					frappe.confirm(
						__('Are you sure you want to convert this Sea Booking to a Sea Shipment?'),
						function() {
							frm.call({
								method: 'convert_to_shipment',
								doc: frm.doc,
								callback: function(r) {
									if (r.exc) return;
									if (r.message && r.message.success && r.message.sea_shipment) {
										frm.reload_doc();
										frappe.show_alert({
											message: __('Sea Shipment {0} created', [r.message.sea_shipment]),
											indicator: 'green'
										}, 3);
										
										// Poll until doc is visible on server, then navigate (avoids "Sea Shipment ... not found" on form load)
										var sea_shipment_name = r.message.sea_shipment;
										function try_navigate(attempt) {
											var max_attempts = 15;
											if (attempt > max_attempts) {
												frappe.set_route('Form', 'Sea Shipment', sea_shipment_name);
												return;
											}
											frappe.call({
												method: "logistics.sea_freight.doctype.sea_shipment.sea_shipment.sea_shipment_exists",
												args: { docname: sea_shipment_name },
												callback: function(res) {
													if (res.message === true) {
														frappe.set_route('Form', 'Sea Shipment', sea_shipment_name);
													} else {
														setTimeout(function() { try_navigate(attempt + 1); }, 300);
													}
												},
												error: function() {
													setTimeout(function() { try_navigate(attempt + 1); }, 300);
												}
											});
										}
										try_navigate(1);
									}
								}
							});
						}
					);
				}, __('Create'));
			}, 100);
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

// Setup query filter for quote field to exclude already-used One-Off Quotes and filter by main_service
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
		// For Sales Quote, filter by main_service = "Sea" and exclude converted One-off quotes
		frm.set_query('quote', function() {
			return { 
				filters: {
					main_service: "Sea",
					_or: [
						["quotation_type", "!=", "One-off"],
						["quotation_type", "=", "One-off", "status", "!=", "Converted"]
					]
				}
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
	// Skip when quote is a temporary name (unsaved document)
	if (String(target_quote).startsWith('new-')) {
		frappe.msgprint({
			title: __("Save Required"),
			message: __("Please save the Sales Quote or One-Off Quote first before selecting it here."),
			indicator: 'orange'
		});
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

// Debounced aggregation for Sea Booking Packages: volume/weight changes update totals and packing summary
// without UI freeze, document reload, or blocking. Skips when grid row dialog is open.
// Exposed for sea_booking_packages.js to trigger parent aggregation.
function _debounced_aggregate_packages(frm) {
	if (frm.is_new() || frm.doc.__islocal) return;
	if (frm.doc.override_volume_weight) return;
	if (_is_grid_dialog_open()) return;

	if (frm._packages_aggregate_timer) clearTimeout(frm._packages_aggregate_timer);
	frm._packages_aggregate_timer = setTimeout(function() {
		frm._packages_aggregate_timer = null;
		if (frm.is_new() || frm.doc.__islocal || _is_grid_dialog_open()) return;
		frm.call({
			method: 'aggregate_volume_from_packages_api',
			doc: frm.doc,
			freeze: false,
			callback: function(r) {
				if (r && !r.exc && r.message && !_is_grid_dialog_open()) {
					if (r.message.total_volume !== undefined) frm.set_value('total_volume', r.message.total_volume);
					if (r.message.total_weight !== undefined) frm.set_value('total_weight', r.message.total_weight);
					if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
					_set_packing_summary_from_response(frm, r.message);
				}
			}
		});
	}, 300);
}
window._sea_booking_debounced_aggregate_packages = _debounced_aggregate_packages;

// Sea Booking Packages: volume-from-dimensions (change-only on blur), fallback when grid form open
frappe.ui.form.on('Sea Booking Packages', {
	form_render: function(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger('packages_on_form_rendered');
		setTimeout(function() {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === 'function') fn_immediate(frm, cdt, cdn);
			else if (typeof fn_debounced === 'function') fn_debounced(frm, cdt, cdn);
			else _sea_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		}, 50);
	},
	volume: function(frm) {
		_debounced_aggregate_packages(frm);
	},
	weight: function(frm) {
		_debounced_aggregate_packages(frm);
	},
	length: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	width: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	height: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	dimension_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	volume_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	}
});

// Helper to check if grid form dialog/row editor is open
function _is_grid_dialog_open() {
	// Check for cur_dialog (Frappe's dialog state)
	if (typeof cur_dialog !== 'undefined' && cur_dialog && cur_dialog.display) {
		return true;
	}
	
	// Check for open grid row (most reliable way to detect grid form is open)
	if ($('.grid-row-open').length > 0) return true;
	
	// Check for grid form dialog
	if ($('.grid-form-dialog:visible').length > 0) return true;
	
	// Check for grid row form wrapper visible
	if ($('.grid-row-form:visible, .grid-form-body:visible').length > 0) return true;
	
	// Check for modal dialogs
	if ($('.modal:visible, .form-dialog:visible').length > 0) {
		// Additional check: if it's a grid row dialog
		if ($('.modal:visible .grid-row-form, .form-dialog:visible .grid-row-form').length > 0) {
			return true;
		}
	}
	
	return false;
}

// Sea Booking Containers: refresh packing summary (total_containers, total_teus, etc.) when containers change
function _refresh_packing_summary_api(frm) {
	// Don't call API for new/unsaved documents
	if (frm.is_new() || frm.doc.__islocal) return;
	
	// Don't call API if a grid dialog/row editor is open (prevents freeze and row editor closing)
	if (_is_grid_dialog_open()) return;
	
	frm.call({
		method: 'aggregate_volume_from_packages_api',
		doc: frm.doc,
		freeze: false, // Don't show freeze message
		callback: function(r) {
			if (r && !r.exc && r.message) {
				// Only update fields if dialog is not open (prevents row editor from closing)
				if (!_is_grid_dialog_open()) {
					if (r.message.total_volume !== undefined) frm.set_value('total_volume', r.message.total_volume);
					if (r.message.total_weight !== undefined) frm.set_value('total_weight', r.message.total_weight);
					if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
					_set_packing_summary_from_response(frm, r.message);
				}
			}
		}
	});
}

frappe.ui.form.on('Sea Booking Containers', {
	type: function(frm) {
		// Only refresh if row editor is not open
		if (!_is_grid_dialog_open()) {
			_refresh_packing_summary_api(frm);
		}
	},
	form_render: function(frm) {
		// Skip if a grid dialog/row editor is open (prevents freeze and row editor closing)
		if (_is_grid_dialog_open()) return;
		
		// Debounce so add/remove row doesn't trigger multiple calls
		if (frm._packing_summary_refresh_timer) clearTimeout(frm._packing_summary_refresh_timer);
		frm._packing_summary_refresh_timer = setTimeout(function() {
			frm._packing_summary_refresh_timer = null;
			// Double-check dialog is still not open before making API call
			if (!_is_grid_dialog_open()) {
				_refresh_packing_summary_api(frm);
			}
		}, 300);
	}
});

// Set packing summary fields (total_containers, total_teus, total_packages) from API response
function _set_packing_summary_from_response(frm, message) {
	if (!message) return;
	// Only update if dialog is not open (prevents row editor from closing)
	if (_is_grid_dialog_open()) return;
	
	var keys = ['total_containers', 'total_teus', 'total_packages', 'total_volume', 'total_weight'];
	keys.forEach(function(key) {
		if (message[key] !== undefined) {
			frm.set_value(key, message[key]);
		}
	});
}

// Update read-only status of measurement fields based on override_volume_weight
function _update_measurement_fields_readonly(frm) {
	var readonly = !frm.doc.override_volume_weight;
	frm.set_df_property('total_volume', 'read_only', readonly);
	frm.set_df_property('total_weight', 'read_only', readonly);
	frm.set_df_property('chargeable', 'read_only', readonly);
}
