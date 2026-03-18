// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Air Shipment', docname: frm.doc.name },
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
		args: { doctype: 'Air Shipment', docname: frm.doc.name },
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

function _load_profitability_html(frm) {
	var control = frm.fields_dict.profitability_section_html;
	if (!control || !control.$wrapper) return;
	function set_html(html) {
		if (control.$wrapper && control.$wrapper.length) {
			control.$wrapper.html(html || '');
		}
	}
	if (!frm.doc.job_costing_number || !frm.doc.company) {
		set_html("<p class=\"text-muted\">" + __("Set Job Costing Number and Company to load profitability from General Ledger.") + "</p>");
		return;
	}
	set_html("<p class=\"text-muted\"><i class=\"fa fa-spinner fa-spin\"></i> " + __("Loading profitability...") + "</p>");
	frappe.call({
		method: 'logistics.job_management.api.get_job_profitability_html',
		args: {
			job_costing_number: frm.doc.job_costing_number,
			company: frm.doc.company
		},
		callback: function(r) {
			if (r.exc) {
				var msg = r.exc;
				try {
					if (r._server_messages) msg = JSON.parse(r._server_messages).message || msg;
				} catch (e) {}
				set_html("<p class=\"text-danger\">" + __("Error loading profitability: ") + msg + "</p>");
			} else {
				set_html(r.message != null ? String(r.message) : '');
			}
		}
	});
}

function _air_shipment_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, grid_row, 'packages');
}

frappe.ui.form.on('Air Shipment', {
	packages_on_form_rendered: function(frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(frm, 'Air Shipment Packages', 'packages', 'air_shipment_volume');
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
		frm.set_query('consignee_address', function() {
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
			return;
		}
		frappe.db.get_value('Shipper', frm.doc.shipper, ['pick_address', 'shipper_primary_address'], function(r) {
			if (r && (r.pick_address || r.shipper_primary_address)) {
				frm.set_value('shipper_address', r.pick_address || r.shipper_primary_address);
				frm.trigger('shipper_address');
			}
		});
	},

	consignee: function(frm) {
		if (!frm.doc.consignee) {
			frm.set_value('consignee_address', '');
			frm.set_value('consignee_address_display', '');
			return;
		}
		frappe.db.get_value('Consignee', frm.doc.consignee, ['delivery_address', 'consignee_primary_address'], function(r) {
			if (r && (r.delivery_address || r.consignee_primary_address)) {
				frm.set_value('consignee_address', r.delivery_address || r.consignee_primary_address);
				frm.trigger('consignee_address');
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

	refresh: function(frm) {
		_update_measurement_fields_readonly(frm);
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

		// Profitability (from GL) section in Charges tab
		setTimeout(function() { _load_profitability_html(frm); }, 100);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.profitability_html').on('click.profitability_html', '[data-fieldname="charges_tab"]', function() {
				setTimeout(function() { _load_profitability_html(frm); }, 50);
			});
		}

		// --- Actions menu ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Air Shipment', docname: frm.doc.name },
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
					args: { doctype: 'Air Shipment', docname: frm.doc.name },
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
					frm.call('recalculate_all_charges').then(function(r) {
						if (r && r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'green' }, 3);
						}
					});
				}, __('Actions'));
			}
			if (typeof logistics_additional_charges_show_sales_quote_dialog === 'function') {
				frm.add_custom_button(__('Get Additional Charges from Quote'), function() {
					logistics_additional_charges_show_sales_quote_dialog(frm, 'Air Shipment');
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
						_create_sales_invoice_from_air_shipment(frm);
					}
				}, __('Create'));
				if (typeof show_create_purchase_invoice_dialog === 'function') {
					frm.add_custom_button(__('Purchase Invoice'), function() {
						show_create_purchase_invoice_dialog(frm);
					}, __('Create'));
				}
				frm.add_custom_button(__('Inbound Order'), function() {
					// Check if warehouse_items is empty
					const warehouse_items = frm.doc.warehouse_items || [];
					if (warehouse_items.length === 0) {
						frappe.confirm(
							__('No warehouse items specified. Using default warehouse item. Do you want to continue?'),
							function() {
								// User confirmed - proceed with conversion
								frappe.call({
									method: 'logistics.utils.module_integration.create_inbound_order_from_air_shipment',
									args: { air_shipment_name: frm.doc.name },
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
							method: 'logistics.utils.module_integration.create_inbound_order_from_air_shipment',
							args: { air_shipment_name: frm.doc.name },
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
						method: 'logistics.utils.module_integration.create_transport_order_from_air_shipment',
						args: { air_shipment_name: frm.doc.name },
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
					frappe.new_doc('Declaration Order', { air_shipment: frm.doc.name });
				}, __('Create'));
				frm.add_custom_button(__('Create Change Request'), function() {
					frappe.call({
						method: 'logistics.pricing_center.doctype.change_request.change_request.create_change_request',
						args: { job_type: 'Air Shipment', job_name: frm.doc.name },
						callback: function(r) {
							if (r.message) {
								frappe.set_route('Form', 'Change Request', r.message);
							}
						}
					});
				}, __('Create'));
				frm.add_custom_button(__('Sea Booking'), function() {
					frappe.new_doc('Sea Booking');
				}, __('Create'));

				// Post menu
				frm.add_custom_button(__('Standard Costs'), function() {
					frappe.call({
						method: 'logistics.air_freight.doctype.air_shipment.air_shipment.post_standard_costs',
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
				_air_shipment_add_recognition_buttons(frm);
			}, 100);
		}
	},
});

function _create_sales_invoice_from_air_shipment(frm) {
	frappe.prompt([
		{ fieldname: 'posting_date', fieldtype: 'Date', label: __('Posting Date'), default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: 'customer', fieldtype: 'Link', label: __('Customer'), options: 'Customer', default: frm.doc.local_customer, reqd: 1 }
	], function(values) {
		frappe.call({
			method: 'logistics.air_freight.doctype.air_shipment.air_shipment.create_sales_invoice_from_air_shipment',
			args: {
				shipment_name: frm.doc.name,
				posting_date: values.posting_date,
				customer: values.customer
			},
			freeze: true,
			freeze_message: __('Creating Sales Invoice...'),
			callback: function(r) {
				if (r.message && r.message.sales_invoice) {
					frappe.set_route('Form', 'Sales Invoice', r.message.sales_invoice);
					frm.reload_doc();
				}
			}
		});
	}, __('Create Sales Invoice'));
}

function _update_measurement_fields_readonly(frm) {
	var readonly = !frm.doc.override_volume_weight;
	if (frm.fields_dict.total_volume) frm.set_df_property('total_volume', 'read_only', readonly);
	if (frm.fields_dict.total_weight) frm.set_df_property('total_weight', 'read_only', readonly);
	if (frm.fields_dict.chargeable) frm.set_df_property('chargeable', 'read_only', readonly);
}

/**
 * Add WIP & Accrual recognition buttons to Air Shipment (Post and Recognition menus).
 * Inline here so buttons show even when recognition_client.js is not loaded.
 */
function _air_shipment_add_recognition_buttons(frm) {
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
