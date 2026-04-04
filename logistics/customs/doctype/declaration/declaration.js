// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _group_and_collapse_dash_alerts($container) {
	if (window.logistics_group_and_collapse_dash_alerts) {
		window.logistics_group_and_collapse_dash_alerts($container);
		return;
	}
	if (!$container || !$container.length) return;
	const $section = $container.find(".dash-alerts-section");
	if (!$section.length) return;
	const $items = $section.find(".dash-alert-item");
	if (!$items.length) return;

	const groups = { danger: [], warning: [], info: [] };
	const order = ["danger", "warning", "info"];
	const labels = {
		danger: __("There are %s critical alerts"),
		warning: __("There are %s warnings"),
		info: __("There are %s information alerts")
	};

	$items.each(function () {
		const $el = $(this);
		const level = $el.hasClass("danger") ? "danger" : $el.hasClass("warning") ? "warning" : "info";
		groups[level].push($el[0].outerHTML);
	});

	let groupsHtml = "";
	order.forEach(function (level) {
		const items = groups[level];
		if (!items || items.length === 0) return;
		const count = items.length;
		const label = labels[level].replace("%s", count);
		const groupClass = "dash-alert-group dash-alert-group-" + level + " collapsed";
		groupsHtml += "<div class=\"" + groupClass + "\">";
		groupsHtml += "<div class=\"dash-alert-group-header\" data-level=\"" + level + "\">";
		groupsHtml += "<i class=\"fa fa-chevron-right dash-alert-group-chevron\"></i>";
		groupsHtml += "<span class=\"dash-alert-group-title\">" + label + "</span>";
		groupsHtml += "</div>";
		groupsHtml += "<div class=\"dash-alert-group-body\">" + items.join("") + "</div>";
		groupsHtml += "</div>";
	});
	$section.html(groupsHtml);

	$section.find(".dash-alert-group-header").on("click", function () {
		const $header = $(this);
		const $group = $header.closest(".dash-alert-group");
		const $body = $group.find(".dash-alert-group-body");
		const $chevron = $header.find(".dash-alert-group-chevron");
		const collapsed = $group.hasClass("collapsed");
		if (collapsed) {
			$body.slideDown(200);
			$group.removeClass("collapsed");
			$chevron.removeClass("fa-chevron-right").addClass("fa-chevron-down");
		} else {
			$body.slideUp(200);
			$group.addClass("collapsed");
			$chevron.removeClass("fa-chevron-down").addClass("fa-chevron-right");
		}
	});
}

/** Documents tab: Total and Exemptions cards are generated in API order; swap so Exemptions sits before Pending Permits and Total last among customs cards. */
function _swap_declaration_documents_exemptions_total_cards($wrapper) {
	var $cards = $wrapper.find(".doc-alerts-cards");
	var $total = $cards.find('[data-category="total"]');
	var $exemptions = $cards.find('[data-category="exemptions"]');
	var $received = $cards.find('[data-category="received"]');
	var $permits = $cards.find('[data-category="pending_permits"]');
	if (!$total.length || !$exemptions.length || !$received.length) {
		return;
	}
	$exemptions.insertAfter($received);
	if ($permits.length) {
		$total.insertAfter($permits);
	} else {
		$total.appendTo($cards);
	}
}

function _load_declaration_documents_html(frm) {
	if (!frm.fields_dict.documents_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._documents_html_called) return;
	frm._documents_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_document_alerts_html",
		args: { doctype: "Declaration", docname: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.documents_html) {
				frm.fields_dict.documents_html.$wrapper.html(r.message);
				_swap_declaration_documents_exemptions_total_cards(frm.fields_dict.documents_html.$wrapper);
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.documents_html.$wrapper);
				}
			}
		},
	}).always(function () {
		setTimeout(function () {
			frm._documents_html_called = false;
		}, 2000);
	});
}

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Declaration', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	}).always(function() {
		setTimeout(function() { frm._milestone_html_called = false; }, 2000);
	});
}

/** Sales / Purchase invoice dialogs live in app assets; if the form bundle fails mid-load, lazy-require fixes missing globals. */
function logistics_declaration_show_sales_invoice_dialog(frm) {
	if (typeof show_create_sales_invoice_dialog === "function") {
		show_create_sales_invoice_dialog(frm);
		return;
	}
	frappe.require("/assets/logistics/js/sales_invoice_dialog.js", function () {
		if (typeof show_create_sales_invoice_dialog === "function") {
			show_create_sales_invoice_dialog(frm);
		} else {
			create_sales_invoice_from_declaration(frm);
		}
	});
}

function logistics_declaration_show_purchase_invoice_dialog(frm) {
	if (typeof show_create_purchase_invoice_dialog === "function") {
		show_create_purchase_invoice_dialog(frm);
		return;
	}
	frappe.require("/assets/logistics/js/purchase_invoice_dialog.js", function () {
		if (typeof show_create_purchase_invoice_dialog === "function") {
			show_create_purchase_invoice_dialog(frm);
		} else {
			frappe.msgprint({
				title: __("Error"),
				message: __("Could not load Purchase Invoice dialog. Try bench build and a hard refresh (Ctrl+Shift+R)."),
				indicator: "red",
			});
		}
	});
}

function _warn_if_missing_service_charges(frm, service_type) {
	var charges = frm.doc.charges || [];
	var has_match = charges.some(function(row) {
		return (row.service_type || '').trim() === service_type;
	});
	if (!has_match) {
		frappe.msgprint({
			title: __("Charges Warning"),
			message: __("No {0} charges found yet. You can continue in draft, but submit will be blocked.", [service_type]),
			indicator: "orange"
		});
	}
}

function _to_num(value) {
	var n = parseFloat(value);
	return isNaN(n) ? 0 : n;
}

function _show_create_from_job_review_dialog(frm, target_label, on_continue) {
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
			{ fieldtype: "Data", fieldname: "customer", label: __("Customer"), read_only: 1, default: frm.doc.customer || "" },
			{ fieldtype: "Data", fieldname: "company", label: __("Company"), read_only: 1, default: frm.doc.company || "" },
			{ fieldtype: "Check", fieldname: "is_internal_job", label: __("Internal Job"), read_only: 1, default: is_internal ? 1 : 0 },
			{ fieldtype: "Data", fieldname: "main_job_type", label: __("Main Job Type"), read_only: 1, default: frm.doc.main_job_type || "" },
			{ fieldtype: "Data", fieldname: "main_job", label: __("Main Job"), read_only: 1, default: frm.doc.main_job || "" }
		],
		primary_action_label: __("Continue"),
		primary_action: function() {
			dialog.hide();
			if (typeof on_continue === "function") on_continue();
		}
	});
	dialog.fields_dict.info_html.$wrapper.html('<div class="text-muted">' + message + '</div>');
	dialog.show();
}

function _auto_set_payment_status(frm) {
	var totalAmount = _to_num(frm.doc.inv_total_amount);
	var paidAmount = _to_num(frm.doc.payment_amount);
	var dueDate = frm.doc.payment_date;
	var todayStr = frappe.datetime.get_today();

	if (totalAmount > 0 && paidAmount >= totalAmount) {
		frm.set_value("payment_status", "Paid");
		return;
	}
	if (paidAmount > 0 && (totalAmount <= 0 || paidAmount < totalAmount)) {
		frm.set_value("payment_status", "Partially Paid");
		return;
	}
	if (paidAmount <= 0 && dueDate && dueDate < todayStr) {
		frm.set_value("payment_status", "Overdue");
		return;
	}
	frm.set_value("payment_status", "Pending");
}

frappe.ui.form.on("Declaration", {
	inv_total_amount(frm) {
		_auto_set_payment_status(frm);
	},
	payment_amount(frm) {
		_auto_set_payment_status(frm);
	},
	payment_date(frm) {
		_auto_set_payment_status(frm);
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
	setup(frm) {
		frm.set_query('milestone_template', function() {
			return frappe.call('logistics.document_management.api.get_milestone_template_filters', { doctype: frm.doctype })
				.then(function(r) { return r.message || { filters: [] }; });
		});
		frm.set_query('sales_quote', function() {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Customs',
					reference_doctype: 'Declaration',
					reference_name: frm.doc.name || ''
				}
			};
		});
	},
	after_save(frm) {
		// After first save (insert), sync renames the doc in locals but the form may still reference the old doc object. Point the form to the new doc so refresh() and run_doc_method (e.g. get_dashboard_html) use the correct modified timestamp and avoid TimestampMismatchError.
		var new_name = frappe.model.new_names && frappe.model.new_names[frm.doc.name];
		if (new_name) {
			frm.docname = new_name;
			frm.doc = (locals[frm.doctype] && locals[frm.doctype][new_name])
				? locals[frm.doctype][new_name]
				: frappe.get_doc(frm.doctype, new_name);
		}
	},
	notify_party(frm) {
		// Auto-populate notify_party_address when notify_party is selected
		if (frm.doc.notify_party) {
			frappe.call({
				method: "logistics.customs.doctype.declaration.declaration.get_customer_address",
				args: {
					customer: frm.doc.notify_party
				},
				callback: function(r) {
					if (r.message && !frm.doc.notify_party_address) {
						frm.set_value("notify_party_address", r.message);
					}
				}
			});
		} else {
			frm.set_value("notify_party_address", "");
		}
	},
	
	refresh(frm) {
		// Filter Declaration Product Code by importer/exporter for line items
		frm.set_query("declaration_product_code", "commercial_invoice_line_items", function() {
			const filters = [["Declaration Product Code", "active", "=", 1]];
			if (frm.doc.importer_consignee) {
				filters.push(["Declaration Product Code", "importer", "in", ["", frm.doc.importer_consignee]]);
			}
			if (frm.doc.exporter_shipper) {
				filters.push(["Declaration Product Code", "exporter", "in", ["", frm.doc.exporter_shipper]]);
			}
			return { filters };
		});
		// Load dashboard HTML in Dashboard tab (only when doc is saved)
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frm.call("get_dashboard_html").then((r) => {
					if (r.message && frm.fields_dict.dashboard_html) {
						frm.fields_dict.dashboard_html.$wrapper.html(r.message);
						if (window.logistics_bind_document_alert_cards) {
							window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
						}
						_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
					}
				}).catch(() => {}).always(() => {
					setTimeout(() => { frm._dashboard_html_called = false; }, 2000);
				});
			}
		}
		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
				_load_milestone_html(frm);
			});
		}

		// Load documents summary HTML in Documents tab (Declaration: swap Exemptions / Total card order)
		_load_declaration_documents_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				_load_declaration_documents_html(frm);
			});
		}

		// --- Actions menu ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Get Documents"), function() {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Declaration", docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					}
				});
			}, __("Action"));
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Declaration', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Action'));
			if (frm.doc.charges && frm.doc.charges.length > 0) {
				frm.add_custom_button(__("Calculate Charges"), function() {
					frm.call("recalculate_all_charges").then(function(r) {
						if (r && r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "green" }, 3);
						}
					});
				}, __("Action"));
				
				// Revert Charges - restore source charges
				frm.add_custom_button(__("Revert Charges"), function() {
					frappe.confirm(__("Are you sure you want to revert charges to source values?"), function() {
						frm.call("revert_charges_to_source").then(function(r) {
							const msg = r && r.message ? r.message : null;
							if (!msg || !msg.success) {
								frappe.msgprint({
									title: __("Revert Charges"),
									message: (msg && msg.message) || __("No source charges available to revert."),
									indicator: "orange"
								});
								return;
							}
							frm.reload_doc();
							let source_label = __("source");
							if (msg.source === "declaration_order") source_label = __("Declaration Order");
							if (msg.source === "sales_quote") source_label = __("Sales Quote");
							frappe.show_alert({
								message: __("Charges reverted to {0} values ({1} rows)", [source_label, msg.charges_count || 0]),
								indicator: "green"
							}, 4);
						});
					});
				}, __("Action"));
			}
		}

		// --- View menu ---
		// View Sales Invoice if exists
		if (frm.doc.docstatus < 2 && !frm.doc.__islocal && frm.doc.job_number) {
			frappe.db.get_value("Sales Invoice", {"job_number": frm.doc.job_number}, "name", function(r) {
				if (r && r.name) {
					frm.add_custom_button(__("View Sales Invoice"), function() {
						frappe.set_route("Form", "Sales Invoice", r.name);
					}, __("View"));
				}
			});
		}
		// View Declaration Order if linked
		if (frm.doc.declaration_order) {
			frm.add_custom_button(__("View Declaration Order"), function() {
				frappe.set_route("Form", "Declaration Order", frm.doc.declaration_order);
			}, __("View"));
		}
		// View Sales Quote if linked
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__("View Sales Quote"), function() {
				frappe.set_route("Form", "Sales Quote", frm.doc.sales_quote);
			}, __("View"));
		}

		// --- Create menu ---
		// Create > Permit Application / Exemption Certificate (customs): link new docs to this declaration and child rows.
		if (frm.doc.name && !frm.doc.__islocal) {
			frm.add_custom_button(__("Permit Application"), function () {
				logistics_show_create_permit_application_dialog(frm);
			}, __("Create"));
			frm.add_custom_button(__("Exemption Certificate"), function () {
				logistics_show_create_exemption_certificate_dialog(frm);
			}, __("Create"));
			frm.add_custom_button(__('Create Change Request'), function() {
				frappe.call({
					method: 'logistics.pricing_center.doctype.change_request.change_request.create_change_request',
					args: { job_type: 'Declaration', job_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.set_route('Form', 'Change Request', r.message);
						}
					}
				});
			}, __('Create'));
		}
		// Create > Declaration Order from linked Sales Quote (same eligibility as Air/Sea Shipment)
		if (frm.doc.name && !frm.doc.__islocal && frm.doc.sales_quote && !frm.doc.declaration_order) {
			frappe.call({
				method: "logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
				args: { sales_quote: frm.doc.sales_quote },
				callback: function (r) {
					const f = r.message || {};
					if (!f.allow_declaration) {
						return;
					}
					frm.add_custom_button(__("Declaration Order"), function () {
						frappe.confirm(
							__(
								"Create a Declaration Order from the linked Sales Quote and link it to this Declaration (or link the existing order if one was already created from that quote)?"
							),
							function () {
								frappe.call({
									method:
										"logistics.customs.doctype.declaration.declaration.link_or_create_declaration_order_for_declaration",
									args: { declaration_name: frm.doc.name },
									freeze: true,
									freeze_message: __("Creating Declaration Order..."),
									callback: function (r2) {
										if (r2.exc) {
											return;
										}
										const msg = r2.message || {};
										if (msg.declaration_order) {
											frappe.show_alert({
												message: msg.message || __("Declaration Order linked."),
												indicator: "green",
											}, 5);
											frm.reload_doc().then(function () {
												frappe.set_route("Form", "Declaration Order", msg.declaration_order);
											});
										}
									},
								});
							}
						);
					}, __("Create"));
				},
			});
		}
		// Create > Transport Order from Main Service Declaration (internal job; link on Declaration)
		if (
			frm.doc.name &&
			!frm.doc.__islocal &&
			frm.doc.is_main_service &&
			!frm.doc.is_internal_job &&
			frm.doc.sales_quote &&
			!frm.doc.transport_order
		) {
			frm.add_custom_button(__("Transport Order"), function () {
				_show_create_from_job_review_dialog(frm, "Transport Order", function() {
					_warn_if_missing_service_charges(frm, "Transport");
					frappe.call({
						method: "logistics.utils.module_integration.create_transport_order_from_declaration",
						args: { declaration_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Creating Transport Order..."),
						callback: function (r) {
							if (r.message && r.message.transport_order) {
								frappe.set_route("Form", "Transport Order", r.message.transport_order);
							}
						},
					});
				});
			}, __("Create"));
		}
		if (frm.doc.name && !frm.doc.__islocal && frm.doc.sales_quote) {
			frappe.call({
				method: "logistics.utils.sales_quote_service_eligibility.get_quote_module_flags",
				args: { sales_quote: frm.doc.sales_quote },
				callback: function (r) {
					const f = r.message || {};
					if (!f.allow_inbound) return;
					frm.add_custom_button(__("Inbound Order"), function () {
						_show_create_from_job_review_dialog(frm, "Inbound Order", function() {
							frappe.call({
								method: "logistics.utils.module_integration.create_inbound_order_from_declaration",
								args: { declaration_name: frm.doc.name },
								freeze: true,
								freeze_message: __("Creating Inbound Order..."),
								callback: function (r2) {
									if (r2.message && r2.message.inbound_order) {
										frappe.set_route("Form", "Inbound Order", r2.message.inbound_order);
									}
								},
							});
						});
					}, __("Create"));
				},
			});
		}
		// Create > Sales Invoice: Draft or submitted (not cancelled). Dialog or fallback creates customer invoices from charges.
		if (frm.doc.docstatus < 2 && !frm.doc.__islocal) {
			frm.add_custom_button(__("Sales Invoice"), function() {
				logistics_declaration_show_sales_invoice_dialog(frm);
			}, __("Create"));
		}
		// Create > Purchase Invoice: Draft or submitted (not cancelled). Select charges and supplier in the dialog.
		if (frm.doc.docstatus < 2 && !frm.doc.__islocal) {
			frm.add_custom_button(__("Purchase Invoice"), function() {
				logistics_declaration_show_purchase_invoice_dialog(frm);
			}, __("Create"));
		}

		// --- Create and Post menus - use setTimeout so they appear after form ready ---
		if (frm.doc.name && !frm.doc.__islocal) {
			setTimeout(function() {
				// Post menu
				frm.add_custom_button(__('Standard Costs'), function() {
					frappe.call({
						method: 'logistics.customs.doctype.declaration.declaration.post_standard_costs',
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
				// WIP & Accrual recognition (Post > Recognize WIP & Accrual, Recognition menu)
				_declaration_add_recognition_buttons(frm);
			}, 100);
		}
	},
});

function create_sales_invoice_from_declaration(frm) {
	// Show confirmation dialog
	frappe.confirm(
		__("Are you sure you want to create a Sales Invoice from this Declaration?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Creating Sales Invoice..."));
			
			// Call the server method
			frappe.call({
				method: "logistics.customs.doctype.declaration.declaration.create_sales_invoice",
				args: {
					declaration_name: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					
					if (r.message && r.message.success) {
						// Show success message
						frappe.msgprint({
							title: __("Sales Invoice Created"),
							message: __("Sales Invoice {0} has been created successfully.", [r.message.sales_invoice]),
							indicator: "green"
						});
						
						// Open the created Sales Invoice
						frappe.set_route("Form", "Sales Invoice", r.message.sales_invoice);
					} else if (r.message && r.message.message) {
						// Show error message
						frappe.msgprint({
							title: __("Error"),
							message: r.message.message,
							indicator: "red"
						});
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Sales Invoice. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}

/**
 * Add WIP & Accrual recognition buttons to Declaration (Post and Recognition menus).
 * Inline here so buttons show even when recognition_client.js is not loaded.
 */
function _declaration_add_recognition_buttons(frm) {
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
		frm.add_custom_button(__('Recognize WIP & Accrual'), function() {
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

function logistics_open_form_new_tab(doctype, docname) {
	var slug = frappe.router.slug(doctype);
	window.open(
		frappe.urllib.get_full_url("/app/" + slug + "/" + encodeURIComponent(docname)),
		"_blank"
	);
}

function logistics_show_create_permit_application_dialog(frm) {
	frm.call("get_permit_application_create_context").then(function (r) {
		var d = r.message;
		if (!d) {
			return;
		}
		var s = d.summary || {};
		var fields = [
			{
				fieldtype: "Link",
				fieldname: "permit_type",
				label: __("Permit Type"),
				options: "Permit Type",
				reqd: 1,
				default: d.default_permit_type || undefined,
			},
			{ fieldtype: "Section Break", label: __("Prefilled on Permit Application") },
			{ fieldtype: "Data", fieldname: "pv_customer", label: __("Customer (applicant)"), read_only: 1, default: s.customer || "" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Data", fieldname: "pv_company", label: __("Company"), read_only: 1, default: s.company || "" },
			{ fieldtype: "Data", fieldname: "pv_decl", label: __("Declaration"), read_only: 1, default: s.declaration || "" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Data", fieldname: "pv_auth", label: __("Customs authority"), read_only: 1, default: s.customs_authority || "" },
		];
		var dialog = new frappe.ui.Dialog({
			title: __("Create Permit Application"),
			fields: fields,
			primary_action_label: __("Create"),
			primary_action: function (values) {
				if (!values.permit_type) {
					frappe.msgprint(__("Select a Permit Type."));
					return;
				}
				frappe.call({
					method: "create_linked_permit_application",
					doc: frm.doc,
					args: { permit_type: values.permit_type, child_row_name: null },
					freeze: true,
					freeze_message: __("Creating Permit Application..."),
					callback: function (r2) {
						if (r2.exc) {
							return;
						}
						var msg = r2.message || {};
						if (msg.permit_application) {
							dialog.hide();
							frm.reload_doc().then(function () {
								logistics_open_form_new_tab("Permit Application", msg.permit_application);
								frappe.show_alert({
									message: __("Permit Application {0} created and linked.", [msg.permit_application]),
									indicator: "green",
								});
							});
						}
					},
				});
			},
		});
		dialog.show();
	});
}

function logistics_show_create_exemption_certificate_dialog(frm) {
	frm.call("get_exemption_certificate_create_context").then(function (r) {
		var d = r.message;
		if (!d) {
			return;
		}
		var s = d.summary || {};
		var fields = [
			{
				fieldtype: "Link",
				fieldname: "exemption_type",
				label: __("Exemption Type"),
				options: "Exemption Type",
				reqd: 1,
				default: d.default_exemption_type || undefined,
			},
			{
				fieldtype: "Data",
				fieldname: "certificate_number",
				label: __("Certificate Number"),
				reqd: 1,
				default: d.suggested_certificate_number || "",
			},
			{
				fieldtype: "HTML",
				fieldname: "ex_help",
				options:
					"<p class='text-muted small'>" +
					__("Certificate is issued to the Declaration Customer ({0}). Adjust on the certificate if another party is required.", [
						frappe.utils.escape_html(s.customer || "—"),
					]) +
					"</p>",
			},
			{ fieldtype: "Section Break", label: __("Prefilled on Exemption Certificate") },
			{ fieldtype: "Data", fieldname: "ex_company", label: __("Company"), read_only: 1, default: s.company || "" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Data", fieldname: "ex_decl", label: __("Declaration"), read_only: 1, default: s.declaration || "" },
		];
		var dialog = new frappe.ui.Dialog({
			title: __("Create Exemption Certificate"),
			fields: fields,
			primary_action_label: __("Create"),
			primary_action: function (values) {
				if (!values.exemption_type || !values.certificate_number) {
					frappe.msgprint(__("Exemption Type and Certificate Number are required."));
					return;
				}
				frappe.call({
					method: "create_linked_exemption_certificate",
					doc: frm.doc,
					args: {
						exemption_type: values.exemption_type,
						certificate_number: values.certificate_number,
						child_row_name: null,
					},
					freeze: true,
					freeze_message: __("Creating Exemption Certificate..."),
					callback: function (r2) {
						if (r2.exc) {
							return;
						}
						var msg = r2.message || {};
						if (msg.exemption_certificate) {
							dialog.hide();
							frm.reload_doc().then(function () {
								logistics_open_form_new_tab("Exemption Certificate", msg.exemption_certificate);
								frappe.show_alert({
									message: __("Exemption Certificate {0} created and linked.", [msg.exemption_certificate]),
									indicator: "green",
								});
							});
						}
					},
				});
			},
		});
		dialog.show();
	});
}
