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

function _is_milestone_tracking_enabled(frm) {
	if (frm._milestone_tracking_enabled !== undefined) {
		return Promise.resolve(frm._milestone_tracking_enabled);
	}
	return frappe.db.get_single_value("Sea Freight Settings", "enable_milestone_tracking")
		.then(function(value) {
			// Match doctype default (1): NULL/legacy unset rows must not hide the tab.
			if (value === undefined || value === null || value === "") {
				frm._milestone_tracking_enabled = true;
			} else {
				frm._milestone_tracking_enabled = Number(value) === 1;
			}
			return frm._milestone_tracking_enabled;
		})
		.catch(function() {
			// Fail open to avoid hiding milestones when settings lookup fails.
			frm._milestone_tracking_enabled = true;
			return true;
		});
}

function _apply_milestone_tracking_visibility(frm, enabled) {
	var show = !!enabled;
	var hidden = show ? 0 : 1;
	["milestones_tab", "section_break_milestones", "milestone_html", "milestone_template", "milestones"].forEach(function(fieldname) {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "hidden", hidden);
		}
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

/** Virtual MBL read-only fields: filled from Master Bill via server (no DB columns on Sea Shipment). */
function _apply_master_bill_virtuals(frm) {
	frappe.call({
		method: 'logistics.sea_freight.doctype.sea_shipment.sea_shipment.get_master_bill_virtuals',
		args: { master_bill: frm.doc.master_bill || '' },
		callback: function(r) {
			if (!r.message) {
				return;
			}
			Object.keys(r.message).forEach(function(fieldname) {
				frm.set_value(fieldname, r.message[fieldname]);
			});
		},
	});
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

/** Table flags for charges: `cannot_add_rows` / `allow_bulk_edit` may not match client meta; set on the docfield so the grid hides Add / Upload / Download as intended. */
function _logistics_set_charges_cannot_add_rows(frm) {
	if (!frm.get_docfield || !frm.get_docfield("charges")) {
		return;
	}
	frm.set_df_property("charges", "cannot_add_rows", 1);
	frm.set_df_property("charges", "allow_bulk_edit", 0);
}

frappe.ui.form.on('Sea Shipment', {
	onload: function(frm) {
		if (window.logistics && logistics.apply_one_off_route_options_onload) {
			logistics.apply_one_off_route_options_onload(frm);
		}
		_logistics_set_charges_cannot_add_rows(frm);
		if (frm.doc.master_bill) {
			_apply_master_bill_virtuals(frm);
		}
	},
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
		frm.set_query('shipper', function() {
			return { filters: { is_active: 1 } };
		});
		frm.set_query('consignee', function() {
			return { filters: { is_active: 1 } };
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
		frm.set_query('sales_quote', function() {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Sea',
					reference_doctype: 'Sea Shipment',
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

	master_bill: function(frm) {
		_apply_master_bill_virtuals(frm);
	},

	company: function(frm) {
		if (window.logistics_apply_sea_freight_settings_accounting_defaults) {
			window.logistics_apply_sea_freight_settings_accounting_defaults(frm);
		}
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
		if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
			logistics.apply_one_off_sales_quote_order_standard(frm);
		}
		_logistics_set_charges_cannot_add_rows(frm);
		setTimeout(function () {
			if (window.logistics_hide_cannot_add_rows_buttons) {
				window.logistics_hide_cannot_add_rows_buttons(frm, "charges");
			}
		}, 0);
		if (window.logistics_apply_sea_freight_settings_accounting_defaults) {
			window.logistics_apply_sea_freight_settings_accounting_defaults(frm);
		}
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

		_is_milestone_tracking_enabled(frm).then(function(enabled) {
			_apply_milestone_tracking_visibility(frm, enabled);
			if (enabled) {
				_load_milestone_html(frm);
				if (frm.layout && frm.layout.wrapper) {
					frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
						_load_milestone_html(frm);
					});
				}
			} else if (frm.layout && frm.layout.wrapper) {
				frm.layout.wrapper.off('click.milestone_html');
			}
		});

		// --- Actions menu ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			_is_milestone_tracking_enabled(frm).then(function(enabled) {
				if (!enabled) return;
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
				}, __('Action'));
			});
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
			}, __('Action'));
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
				}, __('Action'));
			}
			if (typeof logistics_additional_charges_show_sales_quote_dialog === 'function') {
				frm.add_custom_button(__('Get Additional Charges from Quote'), function() {
					logistics_additional_charges_show_sales_quote_dialog(frm, 'Sea Shipment');
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
				if (!(cint(frm.doc.is_internal_job) && frm.doc.main_job_type && frm.doc.main_job)) {
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
							frappe.require('/assets/logistics/js/internal_job_create_from_source.js?v=17', _openInternalJobDlg);
						}
					}, __('Create'));
				}
				var _do_from_ij = _declaration_order_name_from_internal_job_details(frm);
				if (_do_from_ij) {
					frm.add_custom_button(__('View Declaration Order'), function() {
						frappe.set_route('Form', 'Declaration Order', _do_from_ij);
					}, __('View'));
				}
				frm.add_custom_button(__('Create Change Request'), function() {
					frappe.call({
						method: 'logistics.pricing_center.doctype.change_request.change_request.create_change_request',
						args: { job_type: 'Sea Shipment', job_name: frm.doc.name },
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
				// WIP & Accrual recognition (Post > WIP and Accrual; Recognition: adjust/close)
				_sea_shipment_add_recognition_buttons(frm);
				// Reopen/Close Job (charges) must run after this deferred block — avoids toolbar races with Action menu
				if (window.logistics && logistics.job_charge_reopen && logistics.job_charge_reopen.setup) {
					logistics.job_charge_reopen.setup(frm);
				}
			}, 100);
		}
	},
});

/**
 * Add WIP & Accrual recognition buttons to Sea Shipment (Post: WIP and Accrual; Recognition: adjust/close).
 * Inline here so buttons show even when recognition_client.js is not loaded.
 */
function _sea_shipment_add_recognition_buttons(frm) {
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
