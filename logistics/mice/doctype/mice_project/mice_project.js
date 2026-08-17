// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: "MICE Project", docname: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		},
	}).always(function () {
		setTimeout(function () {
			frm._milestone_html_called = false;
		}, 2000);
	});
}

function _setup_lifecycle_jobs_duplicate_fix(frm) {
	if (window.logistics && logistics.lifecycle && logistics.lifecycle.setup_lifecycle_jobs_grid) {
		logistics.lifecycle.setup_lifecycle_jobs_grid(frm);
	}
}

function _load_profitability_html(frm, opts) {
	opts = opts || {};
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.profitability_section_html) {
		if (opts.done) {
			opts.done();
		}
		return;
	}
	var loader =
		window.logistics &&
		logistics.profitability &&
		logistics.profitability.load_project_profitability_html;
	if (typeof loader === "function") {
		loader(frm, opts);
		return;
	}
	frappe.require("/assets/logistics/js/profitability_project_form.js", function () {
		var retry =
			window.logistics &&
			logistics.profitability &&
			logistics.profitability.load_project_profitability_html;
		if (typeof retry === "function") {
			retry(frm, opts);
		} else if (opts.done) {
			opts.done();
		}
	});
}

function _bind_mice_project_profitability_tab(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.profitability_section_html) {
		return;
	}
	if (!window.logistics || !logistics.bind_lazy_tab_loader) {
		_load_profitability_html(frm);
		return;
	}
	if (frm.doc.modified !== frm._logistics_lazy_modified) {
		logistics.invalidate_lazy_tab_loaders(frm);
		frm._logistics_lazy_modified = frm.doc.modified;
	}
	logistics.bind_lazy_tab_loader(
		frm,
		"profitability_tab",
		"profitability",
		_load_profitability_html
	);
	if (logistics.is_form_tab_active(frm, "profitability_tab")) {
		setTimeout(function () {
			logistics.trigger_lazy_tab_loaders(frm, "profitability_tab");
		}, 150);
	}
}

function _refresh_cost_revenue_summary(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.cost_revenue_html) return;
	frappe.call({
		method: "logistics.mice.doctype.mice_project.mice_project.get_cost_revenue_summary",
		args: { show: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.cost_revenue_html) {
				frm.fields_dict.cost_revenue_html.$wrapper.html(r.message);
			}
		},
	});
}

function _load_exhibit_dashboard_html(frm) {
	if (!frm.fields_dict.dashboard_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._exhibit_dashboard_html_called) return;
	frm._exhibit_dashboard_html_called = true;
	frappe.call({
		method: "logistics.mice.doctype.mice_project.mice_project.get_dashboard_html",
		args: { exhibit: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.dashboard_html) {
				frm.fields_dict.dashboard_html.$wrapper.html(r.message);
				if (window.logistics_group_and_collapse_dash_alerts) {
					setTimeout(function () {
						window.logistics_group_and_collapse_dash_alerts(
							frm.fields_dict.dashboard_html.$wrapper
						);
					}, 100);
				}
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
				}
			}
		},
	}).always(function () {
		setTimeout(function () {
			frm._exhibit_dashboard_html_called = false;
		}, 2000);
	});
}

function _refresh_exhibit_dashboard_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.dashboard_html) return;
	frm._exhibit_dashboard_html_called = false;
	_load_exhibit_dashboard_html(frm);
}

function _setup_dockets_grid_buttons(frm) {
	const grid = frm.fields_dict.dockets && frm.fields_dict.dockets.grid;
	if (!grid) return;

	if (typeof grid.cannot_add_rows !== "undefined") {
		grid.cannot_add_rows = true;
	}
	if (grid.df) {
		grid.df.cannot_add_rows = true;
		grid.df.cannot_delete_rows = true;
	}

	// Read-only child tables hide the grid footer, so custom buttons must go on top.
	const stale_labels = [
		__("Open Docket"),
		__("Create Docket"),
		__("View Dockets"),
		__("Add Dockets"),
		__("Add Docket"),
	];
	stale_labels.forEach(function (lbl) {
		if (grid.custom_buttons && grid.custom_buttons[lbl]) {
			try {
				grid.custom_buttons[lbl].remove();
			} catch (e) {
				/* ignore */
			}
			delete grid.custom_buttons[lbl];
		}
	});

	grid.add_custom_button(
		__("Add Docket"),
		function () {
			if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
				frappe.msgprint({
					message: __("Save this MICE Project before creating a Sales Quote."),
					indicator: "orange",
				});
				return;
			}
			frappe.call({
				method: "logistics.mice.doctype.mice_project.mice_project.get_sales_quote_defaults_from_exhibit",
				args: { exhibit_name: frm.doc.name },
				callback: function (r) {
					const defaults = r.message || {};
					frappe.route_options = defaults;
					frappe.new_doc("Sales Quote");
				},
			});
		},
		"top"
	);

	// Ensure the footer stays available if Frappe toggles it for read-only grids.
	grid.wrapper.find(".grid-footer").removeClass("hidden");
}

function _render_exhibit_cost_allocation_help(frm) {
	if (!frm.fields_dict.cost_allocation_html || !frm.fields_dict.cost_allocation_html.$wrapper) {
		return;
	}
	const target_label = frm.doc.cost_allocation_target || "Auto";
	const basis_label = frm.doc.cost_allocation_basis || "Equal";
	const html = `
		<div class="text-muted" style="font-size: 12px; margin-bottom: 6px;">
			${__("Target")}: <b>${frappe.utils.escape_html(target_label)}</b>
			· ${__("Default basis")}: <b>${frappe.utils.escape_html(basis_label)}</b>
			· ${__("Use the Charges → Allocate Costs action to refresh.")}
		</div>`;
	frm.fields_dict.cost_allocation_html.$wrapper.html(html);
}

function _exhibit_refresh_allocation_targets(frm) {
	frm.call({
		method: "refresh_cost_allocation_targets",
		doc: frm.doc,
		callback: function (r) {
			if (r.message) {
				frm.reload_doc();
				frappe.show_alert({ message: r.message.message, indicator: "blue" }, 4);
			}
		},
	});
}

function _exhibit_allocate_costs_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Allocate Costs"),
		fields: [
			{
				fieldname: "target_type",
				fieldtype: "Select",
				label: __("Allocation Target"),
				options: ["Auto", "Dockets", "MICE Jobs"].join("\n"),
				default: frm.doc.cost_allocation_target || "Auto",
				reqd: 1,
				description: __(
					"Where allocated costs land. Auto picks MICE Jobs when present, otherwise Dockets."
				),
			},
			{
				fieldname: "allocation_basis",
				fieldtype: "Select",
				label: __("Default Allocation Basis"),
				options: ["Equal", "Weight-based", "Volume-based", "Value-based", "Custom"].join("\n"),
				default: frm.doc.cost_allocation_basis || "Equal",
				reqd: 1,
				description: __(
					"Used as the fallback for any charge row that does not set its own Allocation Method. Custom uses the per-row Cost Allocation % values; set those before allocating."
				),
			},
		],
		primary_action_label: __("Allocate"),
		primary_action: function (values) {
			d.hide();
			frm.call({
				method: "allocate_costs",
				doc: frm.doc,
				args: {
					allocation_basis: values.allocation_basis,
					target_type: values.target_type,
				},
				freeze: true,
				freeze_message: __("Allocating costs…"),
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						frappe.show_alert(
							{ message: r.message.message, indicator: "green" },
							5
						);
					}
				},
			});
		},
	});
	d.show();
}

function logistics_set_internal_job_site_query(frm) {
	var site_query = function () {
		return logistics.address.query_for_customer(frm._mice_organizer_customer);
	};
	frm.set_query("sp_site", "linked_services", site_query);
	frm.set_query("sp_site", "lifecycle_jobs", site_query);
}

/** Services tab is a read-only mirror; manage via toolbar Services dialog. */
function _mice_setup_linked_services_grid(frm) {
	if (window.logistics && logistics.setup_virtual_linked_services_grid) {
		logistics.setup_virtual_linked_services_grid(frm);
		return;
	}
	if (!frm.get_docfield || !frm.get_docfield("linked_services")) return;
	frm.set_df_property("linked_services", "read_only", 1);
	frm.set_df_property("linked_services", "cannot_add_rows", 1);
	frm.set_df_property("linked_services", "cannot_delete_rows", 1);
}

const MICE_SERVICES_API = "logistics.mice.doctype.mice_project.mice_project";

function _mice_can_manage_linked_services(frm) {
	return !!(frm && frm.doc && !frm.is_new() && frm.doc.docstatus === 0);
}

function _mice_open_services_dialog(frm) {
	function open() {
		if (!logistics.show_linked_services_dialog) {
			frappe.msgprint({
				message: __(
					"Services dialog failed to load. Hard-refresh the page (Ctrl+Shift+R)."
				),
				indicator: "orange",
			});
			return;
		}
		const can_manage = _mice_can_manage_linked_services(frm);
		logistics.show_linked_services_dialog(frm, {
			listMethod: MICE_SERVICES_API + ".list_mice_project_linked_services",
			addMethod: can_manage ? MICE_SERVICES_API + ".add_linked_service" : null,
			removeMethod: can_manage ? MICE_SERVICES_API + ".remove_linked_service" : null,
			parentField: "mice_project",
			parentLabel: __("Project"),
			allowAdd: can_manage,
			allowRemove: can_manage,
			allowEdit: can_manage,
			emptyHint: __("Add a service type below to link it to this project."),
			addHint: __(
				"Select a service type to link to this project. You can add multiple services of the same type (e.g. three Transport legs)."
			),
			unsavedMessage: __("Save the MICE Project before managing services."),
			removeConfirm: (ls) =>
				__("Remove linked service {0} from this project?", [
					`<strong>${frappe.utils.escape_html(ls)}</strong>`,
				]),
		});
	}
	if (logistics.show_linked_services_dialog) {
		open();
		return;
	}
	frappe.require("/assets/logistics/js/linked_services_dialog.js", open);
}

function _mice_setup_services_button(frm) {
	if (frm.is_new()) return;
	frm.add_custom_button(__("Services"), () => {
		_mice_open_services_dialog(frm);
	});
}

function _cache_organizer_customer(frm) {
	if (!frm.doc.organizer) {
		frm._mice_organizer_customer = null;
		return Promise.resolve(null);
	}
	return frappe.db
		.get_value("MICE Organizer", frm.doc.organizer, "customer")
		.then(function (r) {
			frm._mice_organizer_customer = (r && r.message && r.message.customer) || null;
			return frm._mice_organizer_customer;
		});
}

frappe.ui.form.on("MICE Project", {
	on_tab_change: function (frm) {
		var tab = frm.get_active_tab && frm.get_active_tab();
		var fieldname = tab && tab.df && tab.df.fieldname;
		if (fieldname && window.logistics && logistics.trigger_lazy_tab_loaders) {
			logistics.trigger_lazy_tab_loaders(frm, fieldname);
		}
	},
	setup: function (frm) {
		if (window.logistics && logistics.lifecycle && logistics.lifecycle.setup_queries) {
			logistics.lifecycle.setup_queries(frm);
		}
		_mice_setup_linked_services_grid(frm);
		_mice_setup_consolidation_charges_item_query(frm);
		frm.set_query("milestone_template", function () {
			return frappe
				.call("logistics.document_management.api.get_milestone_template_filters", { doctype: frm.doctype })
				.then(function (r) {
					return r.message || { filters: [] };
				});
		});
		frm.set_query("document_list_template", function () {
			return frappe
				.call("logistics.document_management.api.get_document_template_filters", { doctype: frm.doctype })
				.then(function (r) {
					return r.message || { filters: [] };
				});
		});
	},
	refresh: function (frm) {
		_cache_organizer_customer(frm);
		logistics_set_internal_job_site_query(frm);
		_mice_setup_linked_services_grid(frm);
		_mice_strip_consolidation_item_code_link_filters(frm);
		_mice_setup_services_button(frm);
		_setup_dockets_grid_buttons(frm);
		setTimeout(function () {
			_setup_dockets_grid_buttons(frm);
		}, 300);

		_setup_lifecycle_jobs_duplicate_fix(frm);
		if (!frm.fields_dict.lifecycle_jobs?.grid?._logistics_lifecycle_duplicate_patched) {
			setTimeout(() => _setup_lifecycle_jobs_duplicate_fix(frm), 300);
		}

		if (frm.fields_dict.milestone_html && frm.doc.name && !frm.doc.__islocal) {
			_load_milestone_html(frm);
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.milestone_html")
				.on("click.milestone_html", '[data-fieldname="milestones_tab"]', function () {
					_load_milestone_html(frm);
				});
		}

		if (frm.doc.project && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Open Project"), function () {
				frappe.set_route("Form", "Project", frm.doc.project);
			}, __("Action"));
		}

		if (!frm.is_new() && !frm.doc.__islocal) {
			if (window.logistics && logistics.add_get_charges_from_quotation_button_if_allowed) {
				logistics.add_get_charges_from_quotation_button_if_allowed(frm);
			}
			frm.add_custom_button(
				__("Booking / Order"),
				function () {
					function _openDlg() {
						if (window.logistics_show_exhibit_booking_dialog) {
							window.logistics_show_exhibit_booking_dialog(frm);
						} else {
							frappe.msgprint({
								title: __("Not available"),
								message: __(
									"The Booking / Order dialog could not load. Refresh the page or contact your administrator."
								),
								indicator: "red",
							});
						}
					}
					if (window.logistics_show_exhibit_booking_dialog) {
						_openDlg();
					} else {
						frappe.require(
							"/assets/logistics/js/exhibit_booking_dialog.js",
							_openDlg
						);
					}
				},
				__("Create")
			);

			frm.add_custom_button(
				__("Purchase Invoice"),
				function () {
					if (typeof window.show_create_purchase_invoice_dialog === "function") {
						window.show_create_purchase_invoice_dialog(frm);
					} else {
						frappe.require(
							"/assets/logistics/js/purchase_invoice_dialog.js",
							function () {
								if (typeof window.show_create_purchase_invoice_dialog === "function") {
									window.show_create_purchase_invoice_dialog(frm);
								} else {
									frappe.msgprint({
										title: __("Not available"),
										message: __(
											"The Purchase Invoice dialog could not load. Refresh the page or contact your administrator."
										),
										indicator: "red",
									});
								}
							}
						);
					}
				},
				__("Create")
			);
		}

		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(
				__("Refresh Allocation Targets"),
				function () {
					_exhibit_refresh_allocation_targets(frm);
				},
				__("Charges")
			);
			frm.add_custom_button(
				__("Allocate Costs"),
				function () {
					_exhibit_allocate_costs_dialog(frm);
				},
				__("Charges")
			);
		}

		_render_exhibit_cost_allocation_help(frm);

		_refresh_cost_revenue_summary(frm);

		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			_load_exhibit_dashboard_html(frm);
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.exhibit_dashboard_html")
				.on("click.exhibit_dashboard_html", '[data-fieldname="dashboard_tab"]', function () {
					_refresh_exhibit_dashboard_html(frm);
				});
		}

		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, "MICE Project");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.documents_html")
				.on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
					if (window.logistics_load_documents_html) {
						window.logistics_load_documents_html(frm, "MICE Project");
					}
				});
		}
		_bind_mice_project_profitability_tab(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.profitability_html")
				.on("click.profitability_html", '[data-fieldname="profitability_tab"]', function () {
					if (window.logistics && logistics.trigger_lazy_tab_loaders) {
						logistics.trigger_lazy_tab_loaders(frm, "profitability_tab", true);
					} else {
						_load_profitability_html(frm, { force: true });
					}
				});
		}
	},
	organizer: function (frm) {
		_cache_organizer_customer(frm);
	},
	venue_address: function (frm) {
		_refresh_exhibit_dashboard_html(frm);
	},
	venue_name: function (frm) {
		_refresh_exhibit_dashboard_html(frm);
	},
	venue_image: function (frm) {
		_refresh_exhibit_dashboard_html(frm);
	},
	cost_allocation_target: function (frm) {
		_render_exhibit_cost_allocation_help(frm);
	},
	cost_allocation_basis: function (frm) {
		_render_exhibit_cost_allocation_help(frm);
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
				},
			});
		});
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
				},
			});
		});
	},
	before_save: function (frm) {
		if (frm.fields_dict.linked_services) {
			frm.doc.flags = frm.doc.flags || {};
			frm.doc.flags._linked_services_from_form = true;
		}
	},
	lifecycle_jobs_add: function (frm, cdt, cdn) {
		if (logistics.lifecycle && logistics.lifecycle.clear_lifecycle_job_link_on_row_add) {
			logistics.lifecycle.clear_lifecycle_job_link_on_row_add(frm, cdt, cdn);
		}
		_refresh_cost_revenue_summary(frm);
		_refresh_exhibit_dashboard_html(frm);
	},
	lifecycle_jobs_remove: function (frm) {
		_refresh_cost_revenue_summary(frm);
		_refresh_exhibit_dashboard_html(frm);
	},
});

frappe.ui.form.on("MICE Project Cost Allocation", {
	target: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.target_type || !row.target) {
			return;
		}
		frappe.call({
			method:
				"logistics.mice.doctype.mice_project.mice_project.get_cost_allocation_target_basis",
			args: { target_type: row.target_type, target: row.target },
			callback: function (r) {
				if (!r.message) {
					return;
				}
				const { weight_basis, volume_basis, target_title } = r.message;
				frappe.model.set_value(cdt, cdn, "weight_basis", weight_basis);
				frappe.model.set_value(cdt, cdn, "volume_basis", volume_basis);
				if (target_title) {
					frappe.model.set_value(cdt, cdn, "target_title", target_title);
				}
			},
		});
	},
});

/** Item Logistics checkbox for consolidation charge service_type. */
function _mice_consolidation_item_charge_field_for_service_type(service_type) {
	const map = {
		Air: "custom_air_forwarding_charge",
		Sea: "custom_sea_forwarding_charge",
		Transport: "custom_land_transport_charge",
		Customs: "custom_customs_charge",
		Warehousing: "custom_warehousing_charge",
		"Cross-Docking": "custom_cross_dock_charge",
		"Special Project": "custom_special_project_charge",
		MICE: "custom_mice_charge",
	};
	return map[service_type] || null;
}

function _mice_consolidation_item_code_filters(row) {
	const filters = { disabled: 0 };
	if (!row) return filters;
	const field = _mice_consolidation_item_charge_field_for_service_type(row.service_type);
	if (field) {
		filters[field] = 1;
	}
	return filters;
}

/**
 * Static link_filters on item_code override get_query on every Link search.
 * Strip so Service Type → Item logistics checkbox filters apply.
 */
function _mice_strip_consolidation_item_code_link_filters(frm) {
	const df = frappe.meta.get_docfield("MICE Project Consolidation Charges", "item_code");
	if (df && df.link_filters) {
		df.link_filters = null;
	}
	if (
		frm &&
		frm.fields_dict &&
		frm.fields_dict.consolidation_charges &&
		frm.fields_dict.consolidation_charges.grid
	) {
		const gdf = frm.fields_dict.consolidation_charges.grid.get_docfield("item_code");
		if (gdf && gdf.link_filters) {
			gdf.link_filters = null;
		}
	}
}

function _mice_setup_consolidation_charges_item_query(frm) {
	_mice_strip_consolidation_item_code_link_filters(frm);
	frm.set_query("item_code", "consolidation_charges", function (doc, cdt, cdn) {
		_mice_strip_consolidation_item_code_link_filters(frm);
		const row = locals[cdt] && locals[cdt][cdn];
		return { filters: _mice_consolidation_item_code_filters(row) };
	});
}
