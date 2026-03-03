// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Air Booking', {
	setup: function(frm) {
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

	override_volume_weight: function(frm) {
		if (frm.is_new() || frm.doc.__islocal) return;
		if (!frm.doc.override_volume_weight) {
			// Re-aggregate when override is turned off
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
						if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
						if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
					}
				}
			});
		}
	},

	refresh: function(frm) {
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

// Air Booking Packages: trigger header aggregation when package volume/weight changes
frappe.ui.form.on('Air Booking Packages', {
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
					}
				}
			});
		}
	},
	// Trigger aggregation when dimensions change (which will update volume)
	length: function(frm, cdt, cdn) {
		// Volume calculation will be triggered by the global logistics_calculate_volume_from_dimensions
		// After volume is calculated, it will trigger the volume handler above
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
	}
});
