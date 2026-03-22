// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Air Booking', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	}).always(function() {
		setTimeout(function() { frm._milestone_html_called = false; }, 2000);
	});
}

function _load_documents_html(frm) {
	if (!frm.fields_dict.documents_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._documents_html_called) return;
	frm._documents_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_document_alerts_html',
		args: { doctype: 'Air Booking', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.documents_html) {
				frm.fields_dict.documents_html.$wrapper.html(r.message);
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.documents_html.$wrapper);
				}
			}
		}
	}).always(() => {
		setTimeout(() => { frm._documents_html_called = false; }, 2000);
	});
}

frappe.ui.form.on('Air Booking', {
	packages_on_form_rendered: function(frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(frm, 'Air Booking Packages', 'packages', 'air_booking_volume');
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
	setup: function(frm) {
		frm.set_query('milestone_template', function() {
			return frappe.call('logistics.document_management.api.get_milestone_template_filters', { doctype: frm.doctype })
				.then(function(r) { return r.message || { filters: [] }; });
		});
		// Suppress "Air Booking ... not found" when it refers to this form's doc (race after create/save)
		if (!window._air_booking_msgprint_suppress_patched) {
			window._air_booking_msgprint_suppress_patched = true;
			var _msgprint = frappe.msgprint;
			frappe.msgprint = function(opts) {
				var msg = (opts && (typeof opts === 'string' ? opts : opts.message)) || '';
				var cur = cur_frm;
				if (msg && msg.indexOf('Air Booking') !== -1 && msg.indexOf('not found') !== -1 &&
						cur && cur.doctype === 'Air Booking' && cur.doc && cur.doc.name &&
						msg.indexOf(cur.doc.name) !== -1) {
					return;
				}
				return _msgprint.apply(this, arguments);
			};
		}

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
		// Sales Quote: main Air OR Air charges; exclude used One-off quotes (server-side in link search).
		_setup_sales_quote_query(frm);
	},

	shipper: function(frm) {
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
						var c = r.message;
						var txt = [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name;
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
						var c = r.message;
						var txt = [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name;
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
			// Re-aggregate when override is turned off (no freeze)
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				freeze: false,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.total_volume !== undefined) {
							frm.set_value('volume', r.message.total_volume);
							frm.set_value('total_volume', r.message.total_volume);
						}
						if (r.message.total_weight !== undefined) {
							frm.set_value('weight', r.message.total_weight);
							frm.set_value('total_weight', r.message.total_weight);
						}
						if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
					}
				}
			});
		}
	},

	refresh: function(frm) {
		_update_measurement_fields_readonly(frm);
		// Tab click handlers (safe to bind immediately)
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.documents_html').on('click.documents_html', '[data-fieldname="documents_tab"]', function() {
				_load_documents_html(frm);
			});
			frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
				_load_milestone_html(frm);
			});
		}

		// Defer HTML field loading so the new doc is visible on the server (avoids "Air Booking ... not found")
		var docname = frm.doc.name;
		var isNew = !docname || frm.doc.__islocal;
		if (isNew) return;

		function load_html_fields() {
			if (!frm || frm.doc.name !== docname || frm.doc.__islocal) return;

			// Load dashboard HTML via module API (never throws 'not found' — returns placeholder instead)
			if (frm.fields_dict.dashboard_html && !frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frappe.call({
					method: 'logistics.air_freight.doctype.air_booking.air_booking.get_air_booking_dashboard_html',
					args: { docname: docname },
					callback: function(r) {
						if (frm && frm.doc.name === docname && r.message && frm.fields_dict.dashboard_html) {
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
					},
					error: function() {
						if (frm && frm.fields_dict.dashboard_html) {
							frm.fields_dict.dashboard_html.$wrapper.html('<div class="alert alert-warning">Dashboard could not be loaded.</div>');
						}
					}
				});
				setTimeout(function() { if (frm) frm._dashboard_html_called = false; }, 2000);
			}

			_load_documents_html(frm);
			_load_milestone_html(frm);
		}

		setTimeout(load_html_fields, 400);

		// Recalculate package volumes from dimensions (fixes stale/wrong values on load)
		if (frm.doc.packages && frm.doc.packages.length > 0) {
			frm.call({
				method: 'recalculate_package_volumes_api',
				doc: frm.doc,
				freeze: false,
				callback: function(r) {
					if (r && !r.exc && r.message && Array.isArray(r.message)) {
						r.message.forEach(function(item) {
							if (item.name && item.volume !== undefined) {
								var pkg = frm.doc.packages.find(function(p) { return p.name === item.name; });
								if (pkg && parseFloat(pkg.volume || 0) !== parseFloat(item.volume || 0)) {
									frappe.model.set_value('Air Booking Packages', item.name, 'volume', item.volume);
									if (frm.fields_dict.packages && frm.fields_dict.packages.grid && frm.fields_dict.packages.grid.grid_rows_by_docname && frm.fields_dict.packages.grid.grid_rows_by_docname[item.name]) {
										frm.fields_dict.packages.grid.grid_rows_by_docname[item.name].refresh_field('volume');
									}
								}
							}
						});
						// Re-aggregate header totals
						frm.call({
							method: 'aggregate_volume_from_packages_api',
							doc: frm.doc,
							freeze: false,
							callback: function(agg) {
								if (agg && !agg.exc && agg.message) {
									if (agg.message.total_volume !== undefined) frm.set_value('volume', agg.message.total_volume);
									if (agg.message.total_weight !== undefined) frm.set_value('total_weight', agg.message.total_weight);
									if (agg.message.chargeable !== undefined) frm.set_value('chargeable', agg.message.chargeable);
								}
							}
						});
					}
				}
			});
		}

		// --- Actions menu ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Air Booking', docname: frm.doc.name },
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
					args: { doctype: 'Air Booking', docname: frm.doc.name },
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
						method: 'logistics.air_freight.doctype.air_booking.air_booking.recalculate_all_charges',
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
							// Show additional info if no charges were fetched
							if (r.message.charges_count === 0) {
								frappe.show_alert({
									message: __('No charges were fetched. Please check the Sales Quote Air Freight records.'),
									indicator: 'orange'
								}, 5);
							}
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
				// Check if Air Shipment already exists
				frappe.db.get_value("Air Shipment", {"air_booking": frm.doc.name}, "name", function(r) {
					if (r && r.name) {
						// Air Shipment exists - show view button
						frm.add_custom_button(__('View Air Shipment'), function() {
							frappe.set_route('Form', 'Air Shipment', r.name);
						}, __('Create'));
					} else {
						// No Air Shipment exists - show convert button
						frm.add_custom_button(__('Shipment'), function() {
							frappe.confirm(
								__('Are you sure you want to convert this Air Booking to an Air Shipment?'),
								function() {
									frm.call({
										method: 'convert_to_shipment',
										doc: frm.doc,
										callback: function(r) {
											if (r.exc) return;
											if (r.message && r.message.success && r.message.air_shipment) {
												frm.reload_doc();
												frappe.show_alert({
													message: __('Air Shipment {0} created', [r.message.air_shipment]),
													indicator: 'green'
												}, 3);
												frappe.set_route('Form', 'Air Shipment', r.message.air_shipment);
											}
										}
									});
								}
							);
						}, __('Create'));
					}
				});
			}, 100);
		}
	}
});

function _setup_sales_quote_query(frm) {
	frm.set_query('sales_quote', function() {
		return {
			query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
			filters: {
				service_type: 'Air',
				reference_doctype: 'Air Booking',
				reference_name: frm.doc.name || ''
			}
		};
	});
}

// Setup query filter for quote field based on quote_type
function _setup_quote_query(frm) {
	frm.set_query('quote', function() {
		var quote_type = frm.doc.quote_type;
		if (quote_type === 'Sales Quote') {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Air',
					reference_doctype: 'Air Booking',
					reference_name: frm.doc.name || ''
				}
			};
		} else if (quote_type === 'One-Off Quote') {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Air',
					reference_doctype: 'Air Booking',
					reference_name: frm.doc.name || '',
					dialog_one_off: 1
				}
			};
		}
		return {};
	});
}

// Populate charges from quote (handles both Sales Quote and One-Off Quote)
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
				message: __("Failed to populate charges."),
				indicator: 'red'
			});
		}
	});
}

// Debounced aggregation when Air Booking Packages volume/weight change (e.g. from dimension edits).
// Prevents freeze-message-container and repeated async calls during length/width/height edits.
function _air_booking_debounced_aggregate_packages(frm) {
	if (frm.is_new() || frm.doc.__islocal) return;
	if (frm.doc.override_volume_weight) return;

	if (frm._packages_aggregate_timer) clearTimeout(frm._packages_aggregate_timer);
	frm._packages_aggregate_timer = setTimeout(function() {
		frm._packages_aggregate_timer = null;
		if (frm.is_new() || frm.doc.__islocal) return;
		// Use frappe.call with freeze: false so dimension edits never show freeze-message-container
		frappe.call({
			method: 'logistics.air_freight.doctype.air_booking.air_booking.aggregate_volume_from_packages_api',
			args: { doc: frm.doc },
			freeze: false,
			callback: function(r) {
				if (r && !r.exc && r.message && frm.doc) {
					if (r.message.total_volume !== undefined) {
						frm.set_value('volume', r.message.total_volume);
						frm.set_value('total_volume', r.message.total_volume);
					}
					if (r.message.total_weight !== undefined) {
						frm.set_value('weight', r.message.total_weight);
						frm.set_value('total_weight', r.message.total_weight);
					}
					if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
				}
			}
		});
	}, 300);
}

function _update_measurement_fields_readonly(frm) {
	var readonly = !frm.doc.override_volume_weight;
	if (frm.fields_dict.total_volume) frm.set_df_property('total_volume', 'read_only', readonly);
	if (frm.fields_dict.total_weight) frm.set_df_property('total_weight', 'read_only', readonly);
	if (frm.fields_dict.chargeable) frm.set_df_property('chargeable', 'read_only', readonly);
}

function _air_booking_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, grid_row, 'packages');
}

// Air Booking Packages: handlers in parent so frm is always parent form when using cdt/cdn (incl. grid form)
frappe.ui.form.on('Air Booking Packages', {
	form_render: function(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger('packages_on_form_rendered');
		setTimeout(function() {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === 'function') {
				fn_immediate(frm, cdt, cdn);
			} else if (typeof fn_debounced === 'function') {
				fn_debounced(frm, cdt, cdn);
			} else {
				var grid_row = frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form();
				_air_booking_volume_fallback(frm, cdt, cdn, grid_row);
			}
		}, 50);
	},
	refresh: function(frm) {
		// When grid form is open, frm is child form; get parent for cdt/cdn handlers
		var get_parent = window.logistics_get_parent_form;
		var parent_frm = (frm.doctype === 'Air Booking Packages' && typeof get_parent === 'function')
			? get_parent('Air Booking Packages', frm.doc && frm.doc.name)
			: frm;
		if (!parent_frm) parent_frm = frm;
		setTimeout(function() {
			if (frm.doc && frm.doc.length && frm.doc.width && frm.doc.height) {
				var cdt = frm.doctype || 'Air Booking Packages';
				var cdn = frm.doc.name || frm.doc.__temporary_name || null;
				var fn = window.logistics_calculate_volume_from_dimensions;
				if (cdn && typeof fn === 'function') fn(parent_frm, cdt, cdn);
				else if (cdn) _air_booking_volume_fallback(parent_frm, cdt, cdn, null);
			}
			// Chargeable weight is computed on parent from aggregated packages
		}, 100);
	},
	length: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	width: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	height: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	dimension_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	volume_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	volume: function(frm, cdt, cdn) {
		var row = (cdt && cdn && locals[cdt] && locals[cdt][cdn]) ? locals[cdt][cdn] : (frm && frm.doc ? frm.doc : null);
		if (		row && (!row.volume || row.volume === 0) && row.length && row.width && row.height) {
			var fn = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn === 'function') fn(frm, cdt, cdn);
			else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		}
		_air_booking_debounced_aggregate_packages(frm);
	},
	weight: function(frm, cdt, cdn) {
		_air_booking_debounced_aggregate_packages(frm);
	},
	weight_uom: function(frm, cdt, cdn) {
		_air_booking_debounced_aggregate_packages(frm);
	}
});

