// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _declaration_order_name_from_internal_job_details(frm) {
	var rows = frm.doc.internal_job_details || [];
	for (var i = 0; i < rows.length; i++) {
		var r = rows[i];
		var st = String(r.service_type || "").trim();
		var jt = String(r.job_type || "").trim();
		var isDecl =
			st === "Customs" ||
			jt === "Declaration Order";
		if (isDecl && String(r.job_no || "").trim()) {
			return String(r.job_no).trim();
		}
	}
	return "";
}

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
	if (!frm.doc.job_number || !frm.doc.company) {
		set_html("<p class=\"text-muted\">" + __("Set Job Number and Company to load profitability from General Ledger.") + "</p>");
		return;
	}
	set_html("<p class=\"text-muted\"><i class=\"fa fa-spinner fa-spin\"></i> " + __("Loading profitability...") + "</p>");
	frappe.call({
		method: 'logistics.job_management.api.get_job_profitability_html',
		args: {
			job_number: frm.doc.job_number,
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

function _show_create_from_shipment_review_dialog(frm, target_label, on_continue) {
	var is_internal = !!frm.doc.is_internal_job;
	var message = is_internal
		? __("This source is an Internal Job. The new {0} will also be created as an Internal Job linked to this source.", [target_label])
		: __("Review source data that will be passed to {0}.", [target_label]);
	var dialog = new frappe.ui.Dialog({
		title: __("Create > {0}", [target_label]),
		fields: [
			{ fieldtype: "HTML", fieldname: "info_html" },
			{ fieldtype: "Section Break", label: __("Source Context") },
			{ fieldtype: "Data", fieldname: "source_doc", label: __("Source Document"), read_only: 1, default: frm.doc.name || "" },
			{ fieldtype: "Data", fieldname: "customer", label: __("Customer"), read_only: 1, default: frm.doc.local_customer || "" },
			{ fieldtype: "Data", fieldname: "company", label: __("Company"), read_only: 1, default: frm.doc.company || "" },
			{ fieldtype: "Check", fieldname: "is_internal_job", label: __("Internal Job"), read_only: 1, default: is_internal ? 1 : 0 },
			{ fieldtype: "Data", fieldname: "main_job_type", label: __("Main Job Type"), read_only: 1, default: frm.doc.main_job_type || "" },
			{ fieldtype: "Data", fieldname: "main_job", label: __("Main Job"), read_only: 1, default: frm.doc.main_job || "" },
		],
		primary_action_label: __("Continue"),
		primary_action: function() {
			dialog.hide();
			if (typeof on_continue === "function") {
				on_continue();
			}
		},
	});
	dialog.fields_dict.info_html.$wrapper.html('<div class="text-muted">' + message + "</div>");
	dialog.show();
}

var _AIR_SHIPMENT_MAWB_VIRTUAL_FIELDS = [
	'mawb_airline',
	'mawb_flight_no',
	'mawb_flight_date',
	'mawb_flight_status',
	'mawb_booking_reference_no',
	'mawb_agent_reference',
	'mawb_origin_airport',
	'mawb_destination_airport',
	'mawb_scheduled_departure',
	'mawb_scheduled_arrival',
	'mawb_etd_local',
	'mawb_eta_local'
];

function _set_mawb_virtual_values(frm, values) {
	var payload = {};
	_AIR_SHIPMENT_MAWB_VIRTUAL_FIELDS.forEach(function(fieldname) {
		payload[fieldname] = values && Object.prototype.hasOwnProperty.call(values, fieldname)
			? values[fieldname]
			: null;
	});
	frm.set_value(payload);
}

function _refresh_mawb_virtuals(frm) {
	if (!frm.doc.master_awb) {
		_set_mawb_virtual_values(frm, null);
		return;
	}
	if (frm._refreshing_mawb_virtuals) return;
	frm._refreshing_mawb_virtuals = true;
	frappe.call({
		method: 'logistics.air_freight.doctype.air_shipment.air_shipment.get_master_awb_virtuals',
		args: { master_awb: frm.doc.master_awb },
		callback: function(r) {
			_set_mawb_virtual_values(frm, (r && r.message) || {});
		}
	}).always(function() {
		frm._refreshing_mawb_virtuals = false;
	});
}

/** Table flags for charges: `cannot_add_rows` / `allow_bulk_edit` may not match client meta; set on the docfield so the grid hides Add / Upload / Download as intended. */
function _logistics_set_charges_cannot_add_rows(frm) {
	if (!frm.get_docfield || !frm.get_docfield("charges")) {
		return;
	}
	frm.set_df_property("charges", "cannot_add_rows", 1);
	frm.set_df_property("charges", "allow_bulk_edit", 0);
}

frappe.ui.form.on('Air Shipment', {
	onload: function(frm) {
		if (window.logistics && logistics.apply_one_off_route_options_onload) {
			logistics.apply_one_off_route_options_onload(frm);
		}
		_logistics_set_charges_cannot_add_rows(frm);
	},
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
		frm.set_query('sales_quote', function() {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Air',
					reference_doctype: 'Air Shipment',
					reference_name: frm.doc.name || ''
				}
			};
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

	master_awb: function(frm) {
		_refresh_mawb_virtuals(frm);
	},

	refresh: function(frm) {
		if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
			logistics.apply_one_off_sales_quote_order_standard(frm);
		}
		_logistics_set_charges_cannot_add_rows(frm);
		setTimeout(function () {
			if (window.logistics_hide_cannot_add_rows_buttons) {
				window.logistics_hide_cannot_add_rows_buttons(frm, "charges");
			}
		}, 0);
		_update_measurement_fields_readonly(frm);
		_refresh_mawb_virtuals(frm);
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
			if (frappe.model.can_create('Air Shipment IATA Transaction')) {
				frm.add_custom_button(__('IATA / e-AWB'), function() {
					function open_or_create_iata(txName) {
						if (txName) {
							frappe.set_route('Form', 'Air Shipment IATA Transaction', txName);
							return;
						}
						frappe.confirm(
							__('Create an IATA Transaction for IATA status, e-AWB, CASSLink, and TACT?'),
							function() {
								frappe.call({
									method: 'logistics.air_freight.doctype.air_shipment.air_shipment.create_air_shipment_iata_transaction',
									args: { air_shipment: frm.doc.name },
									freeze: true,
									freeze_message: __('Creating IATA Transaction...'),
								}).then(function(r) {
									if (r.message) {
										frappe.set_route('Form', 'Air Shipment IATA Transaction', r.message);
									}
								});
							}
						);
					}
					frappe.db.get_value(
						'Air Shipment IATA Transaction',
						{ air_shipment: frm.doc.name },
						'name'
					).then(function(r) {
						open_or_create_iata(r && r.name);
					});
				}, __('Integrations'));
			}
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
			}, __('Action'));
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
			}, __('Action'));
			if (frm.doc.charges && frm.doc.charges.length > 0) {
				frm.add_custom_button(__('Calculate Charges'), function() {
					frm.call('recalculate_all_charges').then(function(r) {
						if (r && r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'green' }, 3);
						}
					});
				}, __('Action'));
			}
			if (typeof logistics_additional_charges_show_sales_quote_dialog === 'function') {
				frm.add_custom_button(__('Get Additional Charges from Quote'), function() {
					logistics_additional_charges_show_sales_quote_dialog(frm, 'Air Shipment');
				}, __('Action'));
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
				frm.add_custom_button(__('Internal Job'), function() {
					function _openInternalJobDlg() {
						if (window.logistics_show_create_internal_job_dialog) {
							window.logistics_show_create_internal_job_dialog(frm);
						} else {
							frappe.msgprint({
								title: __('Not available'),
								message: __(
									'The internal job dialog could not load. Refresh the page or contact your administrator if this continues.'
								),
								indicator: 'red',
							});
						}
					}
					if (window.logistics_show_create_internal_job_dialog) {
						_openInternalJobDlg();
					} else {
						frappe.require('/assets/logistics/js/internal_job_create_from_source.js?v=15', _openInternalJobDlg);
					}
				}, __('Create'));
				var _do_from_ij = _declaration_order_name_from_internal_job_details(frm);
				if (_do_from_ij) {
					frm.add_custom_button(__('View Declaration Order'), function() {
						frappe.set_route('Form', 'Declaration Order', _do_from_ij);
					}, __('View'));
				}
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
					frm.add_custom_button(__('Internal Billing'), function() {
						frappe.call({
							method: 'logistics.billing.internal_billing.create_internal_billing_for_quote',
							args: {
								sales_quote_name: frm.doc.sales_quote,
								posting_date: frappe.datetime.get_today()
							},
							callback: function(r) {
								if (r.message) {
									var msg = r.message.message || __('Internal billing processed');
									if (r.message.journal_entries && r.message.journal_entries.length) {
										msg = __('Created Journal Entries: {0}.', [r.message.journal_entries.join(', ')]);
									} else if (r.message.journal_entry) {
										msg = __('Created Journal Entry {0}.', [r.message.journal_entry]);
									}
									frappe.show_alert({ message: msg, indicator: 'blue' }, 5);
									frm.reload_doc();
								}
							}
						});
					}, __('Post'));
				}
				// WIP & Accrual recognition (Post > WIP and Accrual; Recognition: adjust/close)
				_air_shipment_add_recognition_buttons(frm);
				// Reopen/Close Job (charges) after deferred Post/Recognition — same ordering concern as Sea Shipment
				if (window.logistics && logistics.job_charge_reopen && logistics.job_charge_reopen.setup) {
					logistics.job_charge_reopen.setup(frm);
				}
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
 * Add WIP & Accrual recognition buttons to Air Shipment (Post: WIP and Accrual; Recognition: adjust/close).
 * Inline here so buttons show even when recognition_client.js is not loaded.
 */
function _air_shipment_add_recognition_buttons(frm) {
	var d = frm.doc;
	var needs_wip = (typeof logistics !== 'undefined' && logistics.recognition && logistics.recognition.needs_wip_recognition)
		? logistics.recognition.needs_wip_recognition(d)
		: ((function() {
			var rows = d.charges || [];
			for (var iw = 0; iw < rows.length; iw++) {
				var rw = rows[iw];
				if ((rw.charge_type || '').toLowerCase() === 'disbursement') continue;
				var erw = flt(rw.estimated_revenue) || flt(rw.base_amount) || flt(rw.actual_revenue) || flt(rw.amount) || flt(rw.total) || 0;
				if (erw > 0 && !rw.wip_recognition_journal_entry) return true;
			}
			return flt(d.estimated_revenue) > flt(d.wip_amount);
		})());
	var needs_accrual = (typeof logistics !== 'undefined' && logistics.recognition && logistics.recognition.needs_accrual_recognition)
		? logistics.recognition.needs_accrual_recognition(d)
		: ((function() {
			var rowsa = d.charges || [];
			for (var ia = 0; ia < rowsa.length; ia++) {
				var ra = rowsa[ia];
				if ((ra.charge_type || '').toLowerCase() === 'disbursement') continue;
				var ca = flt(ra.estimated_cost) || flt(ra.cost_base_amount) || flt(ra.actual_cost) || flt(ra.cost) || 0;
				if (ca > 0 && !ra.accrual_recognition_journal_entry) return true;
			}
			return flt(d.estimated_costs) > flt(d.accrual_amount);
		})());
	if (needs_wip || needs_accrual) {
		frm.add_custom_button(__('WIP and Accrual'), function() {
			frappe.call({
				method: 'logistics.job_management.recognition_engine.recognize',
				args: { doctype: d.doctype, docname: d.name },
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
		}, __('Post'));
	}
	if (d.wip_amount > 0) {
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
	if (d.accrual_amount > 0) {
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
	if (d.wip_amount > 0 || d.accrual_amount > 0) {
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
