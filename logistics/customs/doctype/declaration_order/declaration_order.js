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

	$items.each(function() {
		const $el = $(this);
		const level = $el.hasClass("danger") ? "danger" : $el.hasClass("warning") ? "warning" : "info";
		groups[level].push($el[0].outerHTML);
	});

	let groupsHtml = "";
	order.forEach(function(level) {
		const items = groups[level];
		if (!items || items.length === 0) return;
		const count = items.length;
		const label = labels[level].replace("%s", count);
		const groupClass = "dash-alert-group dash-alert-group-" + level + " collapsed";
		groupsHtml += '<div class="' + groupClass + '">';
		groupsHtml += '<div class="dash-alert-group-header" data-level="' + level + '">';
		groupsHtml += '<i class="fa fa-chevron-right dash-alert-group-chevron"></i>';
		groupsHtml += '<span class="dash-alert-group-title">' + label + '</span>';
		groupsHtml += '</div>';
		groupsHtml += '<div class="dash-alert-group-body">' + items.join("") + '</div>';
		groupsHtml += "</div>";
	});
	$section.html(groupsHtml);

	$section.find(".dash-alert-group-header").on("click", function() {
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

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Declaration Order', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		}
	}).always(function() {
		setTimeout(function() { frm._milestone_html_called = false; }, 2000);
	});
}

function _populate_charges_from_sales_quote(frm) {
	var sales_quote = frm.doc.sales_quote;
	var docname = frm.is_new() ? null : frm.doc.name;
	var ij = frm.doc.is_internal_job;
	var mjt = frm.doc.main_job_type;
	var mj = frm.doc.main_job;
	if (!sales_quote) return;
	// Skip when sales_quote is a temporary name (unsaved document)
	if (String(sales_quote).startsWith('new-')) {
		frappe.msgprint({
			title: __("Save Required"),
			message: __("Please save the Sales Quote first before selecting it here."),
			indicator: 'orange'
		});
		return;
	}
	frappe.call({
		method: "logistics.customs.doctype.declaration_order.declaration_order.populate_charges_from_sales_quote",
		args: {
			docname: docname,
			sales_quote: sales_quote,
			is_internal_job: ij,
			main_job_type: mjt,
			main_job: mj
		},
		freeze: true,
		freeze_message: __("Fetching charges from Sales Quote..."),
		callback: function(r) {
			if (r.message) {
				if (r.message.error) {
					frappe.msgprint({ title: __("Error"), message: r.message.error, indicator: "red" });
					return;
				}
				if (r.message.charges && r.message.charges.length > 0) {
					frm.clear_table("charges");
					r.message.charges.forEach(function(charge) {
						var row = frm.add_child("charges");
						Object.keys(charge).forEach(function(key) {
							if (charge[key] !== null && charge[key] !== undefined) {
								row[key] = charge[key];
							}
						});
					});
					frm.refresh_field("charges");
					if (r.message.charges_count > 0) {
						frappe.show_alert({
							message: __("Populated {0} charges from Sales Quote", [r.message.charges_count]),
							indicator: "green"
						}, 3);
					}
					_warn_if_missing_service_charges(frm, "Customs");
				} else {
					frm.clear_table("charges");
					frm.refresh_field("charges");
					if (!_customs_internal_job_dialog_handled(frm, sales_quote)) {
						_prompt_internal_customs_job_dialog(frm, sales_quote);
					}
					_warn_if_missing_service_charges(frm, "Customs");
				}
			}
		}
	});
}

function _customs_internal_job_dialog_handled(frm, sales_quote) {
	if (!frm._internal_job_dialog_shown_for_quote) {
		frm._internal_job_dialog_shown_for_quote = {};
	}
	return !!frm._internal_job_dialog_shown_for_quote[sales_quote];
}

function _prompt_internal_customs_job_dialog(frm, sales_quote) {
	if (!_customs_internal_job_dialog_handled(frm, sales_quote)) {
		frm._internal_job_dialog_shown_for_quote[sales_quote] = true;
	}

	frappe.call({
		method: "logistics.customs.doctype.declaration_order.declaration_order.get_sales_quote_details",
		args: { sales_quote: sales_quote },
		callback: function(resp) {
			var sq = (resp && resp.message) || {};
			var defaults = {
				company: frm.doc.company || sq.company || "",
				branch: frm.doc.branch || sq.branch || "",
				cost_center: frm.doc.cost_center || sq.cost_center || "",
				profit_center: frm.doc.profit_center || sq.profit_center || "",
				customs_authority: frm.doc.customs_authority || sq.customs_authority || "",
				declaration_type: frm.doc.declaration_type || sq.declaration_type || ""
			};

			var dialog = new frappe.ui.Dialog({
				title: __("Create Internal Job - Customs"),
				fields: [
					{ fieldtype: "HTML", fieldname: "context_html" },
					{ fieldtype: "Section Break", label: __("Internal Job Setup") },
					{ fieldtype: "Check", fieldname: "is_internal_job", label: __("Internal Job"), default: 1, read_only: 1 },
					{ fieldtype: "Link", fieldname: "main_job_type", label: __("Main Job Type"), options: "DocType", reqd: 1, default: frm.doc.main_job_type || "" },
					{
						fieldtype: "Dynamic Link",
						fieldname: "main_job",
						label: __("Main Job"),
						options: "main_job_type",
						reqd: 1,
						default: frm.doc.main_job || ""
					},
					{ fieldtype: "Section Break", label: __("Defaults") },
					{ fieldtype: "Link", fieldname: "company", label: __("Company"), options: "Company", default: defaults.company },
					{ fieldtype: "Link", fieldname: "branch", label: __("Branch"), options: "Branch", default: defaults.branch },
					{ fieldtype: "Link", fieldname: "cost_center", label: __("Cost Center"), options: "Cost Center", default: defaults.cost_center },
					{ fieldtype: "Link", fieldname: "profit_center", label: __("Profit Center"), options: "Profit Center", default: defaults.profit_center },
					{ fieldtype: "Section Break", label: __("Required Additional Details") },
					{ fieldtype: "Link", fieldname: "customs_authority", label: __("Customs Authority"), options: "Customs Authority", reqd: 1, default: defaults.customs_authority },
					{ fieldtype: "Select", fieldname: "declaration_type", label: __("Declaration Type"), options: "\nImport\nExport\nTransit", reqd: 1, default: defaults.declaration_type }
				],
				primary_action_label: __("Create Internal Job"),
				primary_action: function(values) {
					frm.set_value("is_internal_job", 1);
					frm.set_value("main_job_type", values.main_job_type);
					frm.set_value("main_job", values.main_job);
					frm.set_value("company", values.company || frm.doc.company);
					frm.set_value("branch", values.branch || "");
					frm.set_value("cost_center", values.cost_center || "");
					frm.set_value("profit_center", values.profit_center || "");
					frm.set_value("customs_authority", values.customs_authority);
					frm.set_value("declaration_type", values.declaration_type);
					dialog.hide();
					_populate_charges_from_sales_quote(frm);
				}
			});

			dialog.fields_dict.context_html.$wrapper.html(
				'<div class="text-muted">' +
				__("No Customs charges were found on Sales Quote <b>{0}</b>. This will be created as an Internal Job linked to a Main Job.", [sales_quote]) +
				"</div>"
			);
			dialog.show();
		}
	});
}

function _warn_if_missing_service_charges(frm, service_type) {
	const charges = frm.doc.charges || [];
	const has_match = charges.some(function(row) {
		return ((row.service_type || "").trim() === service_type);
	});
	if (!has_match) {
		frappe.msgprint({
			title: __("Charges Warning"),
			message: __("No {0} charges found yet. You can continue in draft, but submit will be blocked.", [service_type]),
			indicator: "orange"
		});
	}
}

/** Table flags for charges: `cannot_add_rows` / `allow_bulk_edit` may not match client meta; set on the docfield so the grid hides Add / Upload / Download as intended. */
function _logistics_set_charges_cannot_add_rows(frm) {
	if (!frm.get_docfield || !frm.get_docfield("charges")) {
		return;
	}
	frm.set_df_property("charges", "cannot_add_rows", 1);
	frm.set_df_property("charges", "allow_bulk_edit", 0);
}

frappe.ui.form.on("Declaration Order", {
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
	onload(frm) {
		_logistics_set_charges_cannot_add_rows(frm);
	},
	setup(frm) {
		frm._initial_sales_quote = frm.doc.sales_quote || null;
		frm.set_query('milestone_template', function() {
			return frappe.call('logistics.document_management.api.get_milestone_template_filters', { doctype: frm.doctype })
				.then(function(r) { return r.message || { filters: [] }; });
		});
		frm.set_query('sales_quote', function() {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Customs',
					reference_doctype: 'Declaration Order',
					reference_name: frm.doc.name || ''
				}
			};
		});
	},
	exporter_shipper(frm) {
		if (logistics.party_defaults) {
			logistics.party_defaults.apply(frm);
		}
	},
	importer_consignee(frm) {
		if (logistics.party_defaults) {
			logistics.party_defaults.apply(frm);
		}
	},
	refresh(frm) {
		_logistics_set_charges_cannot_add_rows(frm);
		setTimeout(function () {
			if (window.logistics_hide_cannot_add_rows_buttons) {
				window.logistics_hide_cannot_add_rows_buttons(frm, "charges");
			}
		}, 0);
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
		// Auto-fill valid_until as date + 1 day if missing
		if (frm.doc.date && !frm.doc.valid_until) {
			frm.set_value("valid_until", frappe.datetime.add_days(frm.doc.date, 1));
		}
		// Load dashboard HTML in Dashboard tab (only when doc is saved)
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frm.call('get_dashboard_html').then(function(r) {
					if (r.message && frm.fields_dict.dashboard_html) {
						frm.fields_dict.dashboard_html.$wrapper.html(r.message);
						_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
						if (window.logistics_bind_document_alert_cards) {
							window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
						}
					}
				}).always(() => {
					setTimeout(() => { frm._dashboard_html_called = false; }, 2000);
				});
			}
		}
		// Load milestone HTML in Milestones tab
		_load_milestone_html(frm);
		// Pre-filled Sales Quote on a new doc does not fire the sales_quote field trigger; fetch charges once.
		if (
			frm.is_new() &&
			frm.doc.sales_quote &&
			!String(frm.doc.sales_quote).startsWith("new-") &&
			!(frm.doc.charges && frm.doc.charges.length) &&
			!frm._sq_charges_prefill_done
		) {
			frm._sq_charges_prefill_done = true;
			_populate_charges_from_sales_quote(frm);
		}
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
					args: { doctype: 'Declaration Order', docname: frm.doc.name },
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
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Declaration Order", docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
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
				
				// Revert Charges - restore source charges
				frm.add_custom_button(__('Revert Charges'), function() {
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
							if (msg.source === "main_job") source_label = __("Main Job");
							if (msg.source === "sales_quote") source_label = __("Sales Quote");
							frappe.show_alert({
								message: __("Charges reverted to {0} values ({1} rows)", [source_label, msg.charges_count || 0]),
								indicator: "green"
							}, 4);
						});
					});
				}, __('Action'));
			}
		}

		// View Sales Quote
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__("View Sales Quote"), function() {
				frappe.set_route("Form", "Sales Quote", frm.doc.sales_quote);
			}, __("View"));
		}
		// Create Declaration or View Declaration
		if (frm.doc.name && !frm.doc.__islocal && frm.doc.docstatus === 1 && frm.doc.sales_quote) {
			setTimeout(function() {
				frappe.db.get_value("Declaration", { declaration_order: frm.doc.name, docstatus: ["<", 2] }, "name", function(r) {
					if (r && r.name) {
						frm.add_custom_button(__("View Declaration"), function() {
							frappe.set_route("Form", "Declaration", r.name);
						}, __("Create"));
					} else {
						frm.add_custom_button(__("Create Declaration"), function() {
							frappe.call({
								method: "logistics.customs.doctype.declaration.declaration.create_declaration_from_declaration_order",
								args: { declaration_order_name: frm.doc.name },
								callback: function(res) {
									if (res.exc) return;
									if (res.message && res.message.success && res.message.declaration) {
										frappe.msgprint({
											title: __("Declaration Created"),
											message: __("Declaration {0} created.", [res.message.declaration]),
											indicator: "green"
										});
										setTimeout(function() {
											frappe.set_route("Form", "Declaration", res.message.declaration);
										}, 100);
									}
								}
							});
						}, __("Create"));
					}
				});
			}, 100);
		}
	},
	before_submit(frm) {
		// Validate required fields before submission and show clear error messages
		if (!frm.doc.sales_quote) {
			frappe.msgprint({
				title: __("Validation Error"),
				message: __("Sales Quote is required. Please select a Sales Quote before submitting the Declaration Order."),
				indicator: 'red'
			});
			return Promise.reject(__("Sales Quote is required. Please select a Sales Quote before submitting the Declaration Order."));
		}
	},
	after_save(frm) {
		// After first save (insert), sync renames the doc in locals but the form may still reference the old doc object. Point the form to the new doc so refresh() and run_doc_method (e.g. get_dashboard_html) use the correct modified timestamp.
		var new_name = frappe.model.new_names && frappe.model.new_names[frm.doc.name];
		if (new_name) {
			frm.docname = new_name;
			frm.doc = (locals[frm.doctype] && locals[frm.doctype][new_name])
				? locals[frm.doctype][new_name]
				: frappe.get_doc(frm.doctype, new_name);
		}
	},
	date(frm) {
		if (!frm.doc.date) return;
		frm.set_value("valid_until", frappe.datetime.add_days(frm.doc.date, 1));
	},
	sales_quote(frm) {
		// no_copy should keep copied/amended drafts from auto-fetching by inherited value
		if (
			frm.is_new() &&
			frm._initial_sales_quote &&
			frm.doc.sales_quote === frm._initial_sales_quote &&
			!(frappe.route_options && frappe.route_options.sales_quote === frm.doc.sales_quote)
		) {
			return;
		}
		if (!frm.doc.sales_quote) {
			frm.clear_table("charges");
			frm.refresh_field("charges");
			return;
		}
		frappe.call({
			method: "logistics.customs.doctype.declaration_order.declaration_order.get_sales_quote_details",
			args: { sales_quote: frm.doc.sales_quote },
			callback: function(r) {
				if (r.message) {
					const msg = r.message;
					if (!frm.doc.customer) frm.set_value("customer", msg.customer || "");
					if (!frm.doc.company) frm.set_value("company", msg.company || "");
					if (!frm.doc.customs_authority) frm.set_value("customs_authority", msg.customs_authority || "");
					if (!frm.doc.branch) frm.set_value("branch", msg.branch || "");
					if (!frm.doc.cost_center) frm.set_value("cost_center", msg.cost_center || "");
					if (!frm.doc.profit_center) frm.set_value("profit_center", msg.profit_center || "");
					if (!frm.doc.declaration_type) frm.set_value("declaration_type", msg.declaration_type || "");
					if (!frm.doc.incoterm) frm.set_value("incoterm", msg.incoterm || "");
				}
			}
		});
		// Populate charges from Sales Quote
		_populate_charges_from_sales_quote(frm);
	}
});
