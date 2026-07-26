// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _add_view_linked_declaration_order_button(frm, method) {
	if (!frm.doc.name || frm.doc.__islocal) return;
	frappe.call({
		method: method,
		args: { docname: frm.doc.name },
		callback: function(r) {
			var do_name = String(r.message || "").trim();
			if (!do_name) return;
			frm.add_custom_button(__("View Declaration Order"), function() {
				frappe.set_route("Form", "Declaration Order", do_name);
			}, __("View"));
		},
	});
}

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._logistics_template_populate_busy || frappe.ui.form.is_saving) return;
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
	var company = frm.doc.company || frappe.defaults.get_user_default("Company");
	return frappe.db.get_value("Sea Freight Settings", { company: company }, "enable_milestone_tracking")
		.then(function(r) {
			var value = r && r.message ? r.message.enable_milestone_tracking : undefined;
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
	if (frm._logistics_template_populate_busy || frappe.ui.form.is_saving) return;
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
	var is_internal = (frm.doc.service_role === "Linked" || !!frm.doc.is_internal_job);
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
			{ fieldtype: "Check", fieldname: "is_internal_job", label: __("Linked Service"), read_only: 1, default: is_internal ? 1 : 0 },
			{ fieldtype: "Data", fieldname: "main_job_type", label: __("Main Service Type"), read_only: 1, default: frm.doc.main_service_type || frm.doc.main_job_type || "" },
			{ fieldtype: "Data", fieldname: "main_job", label: __("Main Service"), read_only: 1, default: frm.doc.main_service || frm.doc.main_job || "" },
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

function _logistics_set_linked_services_read_only(frm) {
	if (window.logistics && logistics.setup_virtual_linked_services_grid) {
		logistics.setup_virtual_linked_services_grid(frm);
	}
}

function _sea_shipment_save_then_populate_template(frm, method, freeze_message) {
	if (!frm.doc.name || frm.doc.__islocal) return;
	frm._logistics_template_populate_busy = true;
	frm.save()
		.then(function () {
			frappe.call({
				method: method,
				args: { doctype: frm.doctype, docname: frm.doc.name },
				freeze: true,
				freeze_message: freeze_message,
				callback: function (r) {
					frm._logistics_template_populate_busy = false;
					if (r.exc) return;
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) {
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
						}
					}
				},
				error: function () {
					frm._logistics_template_populate_busy = false;
				},
			});
		})
		.catch(function () {
			frm._logistics_template_populate_busy = false;
		});
}

function _sea_shipment_set_query_shipping_line_cto(frm) {
	frm.set_query("origin_cto", function() {
		if (!frm.doc.shipping_line || !frm.doc.origin_port) {
			return { filters: { name: ["in", []] } };
		}
		return {
			query:
				"logistics.sea_freight.doctype.shipping_line.shipping_line.shipping_line_cto_by_line_and_port_search",
			filters: { shipping_line: frm.doc.shipping_line, port: frm.doc.origin_port },
		};
	});
	frm.set_query("destination_cto", function() {
		if (!frm.doc.shipping_line || !frm.doc.destination_port) {
			return { filters: { name: ["in", []] } };
		}
		return {
			query:
				"logistics.sea_freight.doctype.shipping_line.shipping_line.shipping_line_cto_by_line_and_port_search",
			filters: { shipping_line: frm.doc.shipping_line, port: frm.doc.destination_port },
		};
	});
}

frappe.ui.form.on('Sea Shipment', {
	onload: function(frm) {
		if (window.logistics && logistics.apply_one_off_route_options_onload) {
			logistics.apply_one_off_route_options_onload(frm);
		}
		_logistics_set_charges_cannot_add_rows(frm);
		_logistics_set_linked_services_read_only(frm);
		if (frm.doc.master_bill) {
			_apply_master_bill_virtuals(frm);
		}
	},
	packages_on_form_rendered: function(frm) {
		_sea_shipment_refresh_package_container_options(frm);
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(frm, 'Sea Freight Packages', 'packages', 'sea_shipment_volume');
		}
	},
	containers_add: function(frm) {
		_sea_shipment_refresh_package_container_options(frm);
	},
	containers_remove: function(frm) {
		_sea_shipment_refresh_package_container_options(frm);
	},
	document_list_template: function (frm) {
		_sea_shipment_save_then_populate_template(
			frm,
			"logistics.document_management.api.populate_documents_from_template",
			__("Applying document template...")
		);
	},
	milestone_template: function (frm) {
		_sea_shipment_save_then_populate_template(
			frm,
			"logistics.document_management.api.populate_milestones_from_template",
			__("Applying milestone template...")
		);
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
			return logistics.address.query_for_link('Shipper', frm.doc.shipper);
		});
		frm.set_query('shipper_contact', function() {
			if (frm.doc.shipper) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Shipper'], ['Dynamic Link', 'link_name', '=', frm.doc.shipper]] };
			}
			return {};
		});
		frm.set_query('consignee_address', function() {
			return logistics.address.query_for_link('Consignee', frm.doc.consignee);
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
		_sea_shipment_set_query_shipping_line_cto(frm);
	},

	shipping_line: function(frm) {
		frm.set_value("origin_cto", "");
		frm.set_value("destination_cto", "");
	},

	origin_port: function(frm) {
		frm.set_value("origin_cto", "");
	},

	destination_port: function(frm) {
		frm.set_value("destination_cto", "");
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
		frm._milestone_tracking_enabled = undefined;
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

	before_save: function(frm) {
	},

	refresh: function(frm) {
		if (window.logistics && logistics.job_change_lock) {
			logistics.job_change_lock.apply(frm);
		}
		_sea_shipment_refresh_package_container_options(frm);
		if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
			logistics.apply_one_off_sales_quote_order_standard(frm);
		}
		_logistics_set_charges_cannot_add_rows(frm);
		_logistics_set_linked_services_read_only(frm);
		setTimeout(function () {
			if (window.logistics_hide_cannot_add_rows_buttons) {
				window.logistics_hide_cannot_add_rows_buttons(frm, "charges");
				window.logistics_hide_cannot_add_rows_buttons(frm, "linked_services");
			}
		}, 0);
		if (window.logistics_apply_sea_freight_settings_accounting_defaults) {
			window.logistics_apply_sea_freight_settings_accounting_defaults(frm);
		}
		_update_measurement_fields_readonly(frm);
		_populate_address_contact_displays_if_missing(frm);
		// Load dashboard HTML via module API (not frm.call) to avoid run_doc_method / check_if_latest races.
		if (
			frm.fields_dict.dashboard_html &&
			frm.doc.name &&
			!frm.doc.__islocal &&
			!frm._logistics_template_populate_busy &&
			!frappe.ui.form.is_saving
		) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				var _dash_docname = frm.doc.name;
				frappe.call({
					method: "logistics.sea_freight.doctype.sea_shipment.sea_shipment.fetch_sea_shipment_dashboard_html",
					args: { docname: _dash_docname },
					callback: function (r) {
						if (
							frm.doc.name === _dash_docname &&
							r.message &&
							frm.fields_dict.dashboard_html
						) {
							frm.fields_dict.dashboard_html.$wrapper.html(r.message);
							if (window.logistics_group_and_collapse_dash_alerts) {
								setTimeout(function () {
									window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
								}, 100);
							}
							if (window.logistics_bind_document_alert_cards) {
								window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
							}
						}
					},
				});
				setTimeout(function () {
					if (frm) frm._dashboard_html_called = false;
				}, 2000);
			}
		}

		// Load documents summary HTML in Documents tab
		if (!frm._logistics_template_populate_busy && !frappe.ui.form.is_saving) {
			_load_documents_html(frm);
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.documents_html').on('click.documents_html', '[data-fieldname="documents_tab"]', function() {
				_load_documents_html(frm);
			});
		}

		_is_milestone_tracking_enabled(frm).then(function(enabled) {
			_apply_milestone_tracking_visibility(frm, enabled);
			if (enabled && !frm._logistics_template_populate_busy && !frappe.ui.form.is_saving) {
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
				if (!((frm.doc.service_role === "Linked" || cint(frm.doc.is_internal_job)) && (frm.doc.main_service_type || frm.doc.main_job_type) && (frm.doc.main_service || frm.doc.main_job))) {
					frm.add_custom_button(__('Booking / Order'), function() {
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
							frappe.require('/assets/logistics/js/internal_job_create_from_source.js?v=20', _openInternalJobDlg);
						}
					}, __('Create'));
				}
				_add_view_linked_declaration_order_button(
					frm,
					"logistics.sea_freight.doctype.sea_shipment.sea_shipment.get_linked_declaration_order_name"
				);
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
									if (r.message.created > 0) {
										msg = __('Created {0} intercompany invoice(s).', [r.message.created]);
									} else if (r.message.errors && r.message.errors.length) {
										msg = r.message.errors[0];
									}
									var indicator = (r.message.created > 0) ? 'green' : (r.message.errors && r.message.errors.length ? 'orange' : 'blue');
									frappe.show_alert({ message: msg, indicator: indicator }, 8);
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

// Container cargo rollup from package lines (Issue #919)
function _apply_container_cargo_to_form(frm, container_cargo) {
	if (!container_cargo || !container_cargo.length || !frm.doc.containers) return;
	container_cargo.forEach(function(item) {
		var row = (frm.doc.containers || []).find(function(c) {
			return (item.idx && c.idx === item.idx) || (item.name && c.name === item.name);
		});
		if (!row) return;
		row.packages_in_container = item.packages_in_container;
		row.weight_in_container = item.weight_in_container;
		row.volume_in_container = item.volume_in_container;
		row.max_weight = item.max_weight;
		row.max_volume = item.max_volume;
		row.utilization_percentage = item.utilization_percentage;
	});
	frm.refresh_field('containers');
	var grid = frm.fields_dict.containers && frm.fields_dict.containers.grid;
	if (grid && grid.grid_form && grid.grid_form.doc) {
		var gd = grid.grid_form.doc;
		var match = container_cargo.find(function(item) { return item.idx === gd.idx; });
		if (match) {
			['packages_in_container', 'weight_in_container', 'volume_in_container',
				'max_weight', 'max_volume', 'utilization_percentage'].forEach(function(f) {
				if (match[f] !== undefined) grid.grid_form.set_value(f, match[f]);
			});
		}
	}
}

function _refresh_container_cargo_metrics(frm) {
	frappe.call({
		method: 'logistics.sea_freight.container_row_metrics.compute_container_cargo_metrics',
		args: { doc: frm.doc },
		freeze: false,
		callback: function(r) {
			if (r && !r.exc && r.message && r.message.container_cargo) {
				_apply_container_cargo_to_form(frm, r.message.container_cargo);
			}
		}
	});
}

function _refresh_container_cargo_debounced(frm) {
	if (frm._container_cargo_timer) clearTimeout(frm._container_cargo_timer);
	frm._container_cargo_timer = setTimeout(function() {
		frm._container_cargo_timer = null;
		_refresh_container_cargo_metrics(frm);
	}, 300);
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
	frappe.call({
		method: 'logistics.sea_freight.doctype.sea_shipment.sea_shipment.fetch_packing_summary',
		args: { docname: frm.doc.name },
		freeze: false,
		callback: function(r) {
			if (r && !r.exc && r.message && !_is_grid_dialog_open()) {
				var msg = r.message;
				if (msg.total_volume !== undefined) frm.set_value('total_volume', msg.total_volume);
				if (msg.total_weight !== undefined) frm.set_value('total_weight', msg.total_weight);
				if (msg.total_containers !== undefined) frm.set_value('total_containers', msg.total_containers);
				if (msg.total_teus !== undefined) frm.set_value('total_teus', msg.total_teus);
				if (msg.total_packages !== undefined) frm.set_value('total_packages', msg.total_packages);
				if (msg.container_cargo) _apply_container_cargo_to_form(frm, msg.container_cargo);
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
	function openDialog() {
		if (typeof show_create_sales_invoice_dialog === "function") {
			show_create_sales_invoice_dialog(frm);
			return;
		}
		frappe.msgprint({
			title: __("Error"),
			message: __("Sales Invoice dialog is not loaded. Please refresh the page."),
			indicator: "red"
		});
	}
	if (typeof show_create_sales_invoice_dialog === "function") {
		openDialog();
	} else {
		frappe.require("/assets/logistics/js/sales_invoice_dialog.js", openDialog);
	}
}

function _sea_shipment_package_or_container_changed(frm) {
	_refresh_container_cargo_debounced(frm);
	_refresh_packing_summary_debounced(frm);
}

/**
 * Rebuild Packages.container Select options from Containers table equipment numbers.
 * container_no is a Link (doc name); cargo rollups match on container_number.
 */
function _sea_shipment_refresh_package_container_options(frm) {
	if (!frm || !frm.fields_dict || !frm.fields_dict.packages || !frm.fields_dict.packages.grid) {
		return;
	}
	var grid = frm.fields_dict.packages.grid;
	var names = (frm.doc.containers || [])
		.map(function (c) {
			return c.container_no;
		})
		.filter(Boolean);

	function apply_options(numbers) {
		var unique = [];
		var seen = {};
		(numbers || []).forEach(function (n) {
			var key = String(n || "").trim();
			if (!key || seen[key]) return;
			seen[key] = true;
			unique.push(key);
		});
		grid.update_docfield_property("container", "options", "\n" + unique.join("\n"));
	}

	if (!names.length) {
		apply_options([]);
		return;
	}

	frappe.db
		.get_list("Container", {
			filters: { name: ["in", names] },
			fields: ["name", "container_number"],
			limit: names.length,
		})
		.then(function (rows) {
			var map = {};
			(rows || []).forEach(function (r) {
				if (r && r.name) {
					map[r.name] = r.container_number || r.name;
				}
			});
			apply_options(
				names.map(function (n) {
					return map[n] || n;
				})
			);
		})
		.catch(function () {
			// Legacy / unresolved: use raw container_no values
			apply_options(names);
		});
}

// Sea Freight Packages: refresh totals and per-container cargo when packages change
frappe.ui.form.on('Sea Freight Packages', {
	form_render: function(frm) {
		_sea_shipment_refresh_package_container_options(frm);
		_sea_shipment_package_or_container_changed(frm);
	},
	container: function(frm) {
		_sea_shipment_package_or_container_changed(frm);
	},
	no_of_packs: function(frm) {
		_sea_shipment_package_or_container_changed(frm);
	},
	weight: function(frm) {
		_sea_shipment_package_or_container_changed(frm);
	},
	weight_uom: function(frm) {
		_sea_shipment_package_or_container_changed(frm);
	},
	volume: function(frm) {
		_sea_shipment_package_or_container_changed(frm);
	},
	volume_uom: function(frm) {
		_sea_shipment_package_or_container_changed(frm);
	}
});

// Sea Freight Containers: refresh capacity metrics when container type changes
frappe.ui.form.on('Sea Freight Containers', {
	form_render: function(frm) {
		_sea_shipment_refresh_package_container_options(frm);
		_refresh_container_cargo_debounced(frm);
		if (!_is_grid_dialog_open()) {
			_refresh_packing_summary_debounced(frm);
		}
	},
	container_no: function(frm) {
		_sea_shipment_refresh_package_container_options(frm);
	},
	type: function(frm) {
		_refresh_container_cargo_debounced(frm);
		if (!_is_grid_dialog_open()) {
			_refresh_packing_summary_debounced(frm);
		}
	}
});
