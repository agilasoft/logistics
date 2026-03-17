// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Sea Shipment', docname: frm.doc.name },
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
		args: { doctype: 'Sea Shipment', docname: frm.doc.name },
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

function _sea_shipment_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, grid_row, 'packages');
}

frappe.ui.form.on('Sea Shipment', {
	packages_on_form_rendered: function(frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(frm, 'Sea Freight Packages', 'packages', 'sea_shipment_volume');
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

	override_volume_weight: function(frm) {
		_update_measurement_fields_readonly(frm);
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

	refresh: function(frm) {
		_update_measurement_fields_readonly(frm);
		_populate_address_contact_displays_if_missing(frm);
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

		// Load documents summary HTML in Documents tab
		_load_documents_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.documents_html').on('click.documents_html', '[data-fieldname="documents_tab"]', function() {
				_load_documents_html(frm);
			});
		}

		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
				_load_milestone_html(frm);
			});
		}

		// --- Actions menu ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Sea Shipment', docname: frm.doc.name },
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
					args: { doctype: 'Sea Shipment', docname: frm.doc.name },
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
						method: 'logistics.sea_freight.doctype.sea_shipment.sea_shipment.recalculate_all_charges',
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
			if (typeof logistics_additional_charges_show_sales_quote_dialog === 'function') {
				frm.add_custom_button(__('Get Additional Charges from Quote'), function() {
					logistics_additional_charges_show_sales_quote_dialog(frm, 'Sea Shipment');
				}, __('Actions'));
			}
		}

		// --- Create and Post menus - use setTimeout so they appear after form ready ---
		if (frm.doc.name && !frm.doc.__islocal) {
			setTimeout(function() {
				// Create menu - Sales Invoice always shown to allow multiple invoices (by bill_to, invoice_type, etc.)
				frm.add_custom_button(__('Sales Invoice'), function() {
					if (typeof show_create_sales_invoice_dialog === 'function') {
						show_create_sales_invoice_dialog(frm);
					} else {
						_create_sales_invoice_from_sea_shipment(frm);
					}
				}, __('Create'));
				frm.add_custom_button(__('Purchase Invoice'), function() {
					if (typeof show_create_purchase_invoice_dialog === 'function') {
						show_create_purchase_invoice_dialog(frm);
					} else {
						frappe.msgprint({ title: __('Error'), message: __('Purchase Invoice feature is not loaded. Please refresh the page.'), indicator: 'red' });
					}
				}, __('Create'));
				frm.add_custom_button(__('Inbound Order'), function() {
					// Check if warehouse_items is empty
					const warehouse_items = frm.doc.warehouse_items || [];
					if (warehouse_items.length === 0) {
						frappe.confirm(
							__('No warehouse items specified. Using default warehouse item. Do you want to continue?'),
							function() {
								// User confirmed - proceed with conversion
								frappe.call({
									method: 'logistics.utils.module_integration.create_inbound_order_from_sea_shipment',
									args: { sea_shipment_name: frm.doc.name },
									freeze: true,
									freeze_message: __('Creating Inbound Order...'),
									callback: function(r) {
										if (r.message && r.message.inbound_order) {
											frappe.set_route('Form', 'Inbound Order', r.message.inbound_order);
										}
									}
								});
							}
							// User cancelled - do nothing
						);
					} else {
						// warehouse_items exist - proceed directly
						frappe.call({
							method: 'logistics.utils.module_integration.create_inbound_order_from_sea_shipment',
							args: { sea_shipment_name: frm.doc.name },
							freeze: true,
							freeze_message: __('Creating Inbound Order...'),
							callback: function(r) {
								if (r.message && r.message.inbound_order) {
									frappe.set_route('Form', 'Inbound Order', r.message.inbound_order);
								}
							}
						});
					}
				}, __('Create'));
				frm.add_custom_button(__('Transport Order'), function() {
					frappe.call({
						method: 'logistics.utils.module_integration.create_transport_order_from_sea_shipment',
						args: { sea_shipment_name: frm.doc.name },
						freeze: true,
						freeze_message: __('Creating Transport Order...'),
						callback: function(r) {
							if (r.message && r.message.transport_order) {
								frappe.set_route('Form', 'Transport Order', r.message.transport_order);
							}
						}
					});
				}, __('Create'));
				frm.add_custom_button(__('Declaration Order'), function() {
					frappe.new_doc('Declaration Order', { sea_shipment: frm.doc.name });
				}, __('Create'));
				frm.add_custom_button(__('Air Booking'), function() {
					frappe.new_doc('Air Booking');
				}, __('Create'));

				// Post menu
				frm.add_custom_button(__('Standard Costs'), function() {
					frappe.call({
						method: 'logistics.sea_freight.doctype.sea_shipment.sea_shipment.post_standard_costs',
						args: { docname: frm.doc.name },
						callback: function(r) {
							if (r.message) frm.reload_doc();
						}
					});
				}, __('Post'));
				if (frm.doc.sales_quote && frm.doc.company) {
					frm.add_custom_button(__('Intercompany Transactions'), function() {
						frappe.call({
							method: 'logistics.intercompany.intercompany_invoice.create_intercompany_invoices_for_quote',
							args: {
								sales_quote_name: frm.doc.sales_quote,
								billing_company: frm.doc.company,
								posting_date: frappe.datetime.get_today()
							},
							callback: function(r) {
								if (r.message) {
									var msg = r.message.message || __('Intercompany invoices processed');
									if (r.message.created !== undefined) {
										msg = __('Created {0} intercompany invoice(s).', [r.message.created]);
									}
									frappe.show_alert({ message: msg, indicator: 'green' }, 5);
									frm.reload_doc();
								}
							}
						});
					}, __('Post'));
				}
				// WIP & Accrual recognition (Post > Recognize WIP & Accrual, Recognition menu)
				_sea_shipment_add_recognition_buttons(frm);
			}, 100);
		}
	},
});

/**
 * Add WIP & Accrual recognition buttons to Sea Shipment (Post and Recognition menus).
 * Inline here so buttons show even when recognition_client.js is not loaded.
 */
function _sea_shipment_add_recognition_buttons(frm) {
	var d = frm.doc;
	var needs_wip = !d.wip_journal_entry && !d.wip_closed;
	var needs_accrual = !d.accrual_journal_entry && !d.accrual_closed;
	if (needs_wip || needs_accrual) {
		frm.add_custom_button(__('Recognize WIP & Accrual'), function() {
			frappe.prompt([
				{ fieldname: 'recognition_date', fieldtype: 'Date', label: __('Recognition Date'), default: frappe.datetime.get_today(), reqd: 1 }
			], function(values) {
				frappe.call({
					method: 'logistics.job_management.recognition_engine.recognize',
					args: { doctype: d.doctype, docname: d.name, recognition_date: values.recognition_date },
					freeze: true,
					freeze_message: __('Recognizing WIP and Accruals...'),
					callback: function(r) {
						if (r.message) {
							var msg = [];
							if (r.message.wip_journal_entry) msg.push(__('WIP: {0}', [r.message.wip_journal_entry]));
							if (r.message.accrual_journal_entry) msg.push(__('Accruals: {0}', [r.message.accrual_journal_entry]));
							if (msg.length) {
								frappe.show_alert({ message: msg.join(' | '), indicator: 'green' });
							} else {
								var reason = r.message.message || __('Nothing to recognize (already recognized or below minimum)');
								frappe.msgprint({ title: __('Recognition'), message: reason, indicator: 'blue' });
							}
							frm.reload_doc();
						}
					}
				});
			}, __('Recognize WIP & Accrual'), __('Create'));
		}, __('Post'));
	}
	if (needs_wip) {
		frm.add_custom_button(__('Recognize WIP'), function() {
			frappe.prompt([
				{ fieldname: 'recognition_date', fieldtype: 'Date', label: __('Recognition Date'), default: frappe.datetime.get_today(), reqd: 1 }
			], function(values) {
				frappe.call({
					method: 'logistics.job_management.recognition_engine.recognize_wip',
					args: { doctype: d.doctype, docname: d.name, recognition_date: values.recognition_date },
					freeze: true,
					freeze_message: __('Creating WIP Recognition...'),
					callback: function(r) { if (r.message) { frappe.show_alert({ message: __('WIP Recognition created: {0}', [r.message]), indicator: 'green' }); frm.reload_doc(); } }
				});
			}, __('Recognize WIP'), __('Create'));
		}, __('Recognition'));
	}
	if (needs_accrual) {
		frm.add_custom_button(__('Recognize Accruals'), function() {
			frappe.prompt([
				{ fieldname: 'recognition_date', fieldtype: 'Date', label: __('Recognition Date'), default: frappe.datetime.get_today(), reqd: 1 }
			], function(values) {
				frappe.call({
					method: 'logistics.job_management.recognition_engine.recognize_accruals',
					args: { doctype: d.doctype, docname: d.name, recognition_date: values.recognition_date },
					freeze: true,
					freeze_message: __('Creating Accrual Recognition...'),
					callback: function(r) { if (r.message) { frappe.show_alert({ message: __('Accrual Recognition created: {0}', [r.message]), indicator: 'green' }); frm.reload_doc(); } }
				});
			}, __('Recognize Accruals'), __('Create'));
		}, __('Recognition'));
	}
	if (d.wip_journal_entry && d.wip_amount > 0 && !d.wip_closed) {
		frm.add_custom_button(__('Adjust WIP'), function() {
			frappe.prompt([
				{ fieldname: 'adjustment_amount', fieldtype: 'Currency', label: __('Adjustment Amount'), description: __('Current WIP: {0}', [d.wip_amount]), reqd: 1 },
				{ fieldname: 'adjustment_date', fieldtype: 'Date', label: __('Adjustment Date'), default: frappe.datetime.get_today(), reqd: 1 }
			], function(values) {
				frappe.call({
					method: 'logistics.job_management.recognition_engine.adjust_wip',
					args: { doctype: d.doctype, docname: d.name, adjustment_amount: values.adjustment_amount, adjustment_date: values.adjustment_date },
					freeze: true,
					freeze_message: __('Creating WIP Adjustment...'),
					callback: function(r) { if (r.message) { frappe.show_alert({ message: __('WIP Adjustment created: {0}', [r.message]), indicator: 'green' }); frm.reload_doc(); } }
				});
			}, __('Adjust WIP'), __('Create'));
		}, __('Recognition'));
	}
	if (d.accrual_journal_entry && d.accrual_amount > 0 && !d.accrual_closed) {
		frm.add_custom_button(__('Adjust Accruals'), function() {
			frappe.prompt([
				{ fieldname: 'adjustment_amount', fieldtype: 'Currency', label: __('Adjustment Amount'), description: __('Current Accrual: {0}', [d.accrual_amount]), reqd: 1 },
				{ fieldname: 'adjustment_date', fieldtype: 'Date', label: __('Adjustment Date'), default: frappe.datetime.get_today(), reqd: 1 }
			], function(values) {
				frappe.call({
					method: 'logistics.job_management.recognition_engine.adjust_accruals',
					args: { doctype: d.doctype, docname: d.name, adjustment_amount: values.adjustment_amount, adjustment_date: values.adjustment_date },
					freeze: true,
					freeze_message: __('Creating Accrual Adjustment...'),
					callback: function(r) { if (r.message) { frappe.show_alert({ message: __('Accrual Adjustment created: {0}', [r.message]), indicator: 'green' }); frm.reload_doc(); } }
				});
			}, __('Adjust Accruals'), __('Create'));
		}, __('Recognition'));
	}
	if ((d.wip_amount > 0 && !d.wip_closed) || (d.accrual_amount > 0 && !d.accrual_closed)) {
		frm.add_custom_button(__('Close Recognition'), function() {
			frappe.confirm(__('This will close all remaining WIP and Accruals. Continue?'), function() {
				frappe.prompt([
					{ fieldname: 'closure_date', fieldtype: 'Date', label: __('Closure Date'), default: frappe.datetime.get_today(), reqd: 1 }
				], function(values) {
					frappe.call({
						method: 'logistics.job_management.recognition_engine.close_job_recognition',
						args: { doctype: d.doctype, docname: d.name, closure_date: values.closure_date },
						freeze: true,
						freeze_message: __('Closing Recognition...'),
						callback: function(r) {
							if (r.message) {
								var msg = [];
								if (r.message.wip_journal_entry) msg.push(__('WIP closed: {0}', [r.message.wip_journal_entry]));
								if (r.message.accrual_journal_entry) msg.push(__('Accrual closed: {0}', [r.message.accrual_journal_entry]));
								if (msg.length) frappe.show_alert({ message: msg.join(' | '), indicator: 'green' });
								frm.reload_doc();
							}
						}
					});
				}, __('Close Recognition'), __('Close'));
			});
		}, __('Recognition'));
	}
}

// Packing summary: total_containers, total_teus, total_packages from packages and containers tables
function _is_grid_dialog_open() {
	if (typeof cur_dialog !== 'undefined' && cur_dialog && cur_dialog.display) return true;
	if ($('.grid-row-open').length > 0) return true;
	if ($('.grid-form-dialog:visible').length > 0) return true;
	if ($('.grid-row-form:visible, .grid-form-body:visible').length > 0) return true;
	if ($('.modal:visible .grid-row-form, .form-dialog:visible .grid-row-form').length > 0) return true;
	return false;
}

function _update_measurement_fields_readonly(frm) {
	var readonly = !frm.doc.override_volume_weight;
	if (frm.fields_dict.total_volume) frm.set_df_property('total_volume', 'read_only', readonly);
	if (frm.fields_dict.total_weight) frm.set_df_property('total_weight', 'read_only', readonly);
	if (frm.fields_dict.chargeable) frm.set_df_property('chargeable', 'read_only', readonly);
}

function _refresh_packing_summary_api(frm) {
	if (frm.is_new() || frm.doc.__islocal) return;
	if (_is_grid_dialog_open()) return;
	if (frm.doc.override_volume_weight) return;
	frm.call({
		method: 'aggregate_volume_from_packages_api',
		doc: frm.doc,
		freeze: false,
		callback: function(r) {
			if (r && !r.exc && r.message && !_is_grid_dialog_open()) {
				var msg = r.message;
				if (msg.total_volume !== undefined) frm.set_value('total_volume', msg.total_volume);
				if (msg.total_weight !== undefined) frm.set_value('total_weight', msg.total_weight);
				if (msg.total_containers !== undefined) frm.set_value('total_containers', msg.total_containers);
				if (msg.total_teus !== undefined) frm.set_value('total_teus', msg.total_teus);
				if (msg.total_packages !== undefined) frm.set_value('total_packages', msg.total_packages);
			}
		}
	});
}

function _refresh_packing_summary_debounced(frm) {
	if (_is_grid_dialog_open()) return;
	if (frm._packing_summary_timer) clearTimeout(frm._packing_summary_timer);
	frm._packing_summary_timer = setTimeout(function() {
		frm._packing_summary_timer = null;
		if (_is_grid_dialog_open()) return;
		if (frm.is_new() || frm.doc.__islocal) {
			_update_packing_summary_client_side(frm);
		} else {
			_refresh_packing_summary_api(frm);
		}
	}, 300);
}

function _update_packing_summary_client_side(frm) {
	var containers = frm.doc.containers || [];
	var packages = frm.doc.packages || [];
	var totalPackages = 0;
	packages.forEach(function(p) { totalPackages += parseFloat(p.no_of_packs) || 0; });
	frm.set_value('total_containers', containers.length);
	frm.set_value('total_packages', totalPackages);
	// total_teus requires Container Type lookup; updated on save (validate) or via API for saved docs
}

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

function _create_sales_invoice_from_sea_shipment(frm) {
	var fields = [
		{ fieldname: 'posting_date', fieldtype: 'Date', label: __('Posting Date'), default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: 'customer', fieldtype: 'Link', label: __('Customer'), options: 'Customer', default: frm.doc.local_customer, reqd: 1 }
	];
	// Add invoice_type if Sea Shipment Charges use it
	if (frm.fields_dict.charges && frm.fields_dict.charges.grid) {
		var meta = frappe.get_meta('Sea Shipment Charges');
		if (meta && meta.get_field('invoice_type')) {
			fields.push({ fieldname: 'invoice_type', fieldtype: 'Link', label: __('Invoice Type'), options: 'Invoice Type' });
		}
	}
	frappe.prompt(fields, function(values) {
		frappe.call({
			method: 'logistics.sea_freight.doctype.sea_shipment.sea_shipment.create_sales_invoice',
			args: {
				shipment_name: frm.doc.name,
				posting_date: values.posting_date,
				customer: values.customer,
				invoice_type: values.invoice_type || null
			},
			freeze: true,
			freeze_message: __('Creating Sales Invoice...'),
			callback: function(r) {
				if (r.message && r.message.name) {
					frappe.set_route('Form', 'Sales Invoice', r.message.name);
					frm.reload_doc();
				}
			}
		});
	}, __('Create Sales Invoice'));
}

// Sea Freight Packages: refresh total_packages (and volume/weight) when packages change
frappe.ui.form.on('Sea Freight Packages', {
	form_render: function(frm) {
		_refresh_packing_summary_debounced(frm);
	},
	no_of_packs: function(frm) {
		_refresh_packing_summary_debounced(frm);
	}
});

// Sea Freight Containers: refresh total_containers and total_teus when containers change
frappe.ui.form.on('Sea Freight Containers', {
	form_render: function(frm) {
		_refresh_packing_summary_debounced(frm);
	},
	type: function(frm) {
		_refresh_packing_summary_debounced(frm);
	}
});
