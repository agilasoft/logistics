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
					message: __("Save this Exhibit before creating a Sales Quote."),
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
					"Where allocated costs land. Auto picks Exhibit Jobs when present, otherwise Dockets."
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
	frm.set_query("sp_site", "lifecycle_jobs", function () {
		const cust = frm._mice_organizer_customer;
		if (!cust) {
			return { filters: [["name", "=", ""]] };
		}
		return {
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: {
				link_doctype: "Customer",
				link_name: cust,
			},
		};
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
	setup: function (frm) {
		if (window.logistics && logistics.lifecycle && logistics.lifecycle.setup_queries) {
			logistics.lifecycle.setup_queries(frm);
		}
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
		_setup_dockets_grid_buttons(frm);
		setTimeout(function () {
			_setup_dockets_grid_buttons(frm);
		}, 300);

		_setup_lifecycle_jobs_duplicate_fix(frm);
		if (!frm.fields_dict.lifecycle_jobs?.grid?._logistics_lifecycle_duplicate_patched) {
			setTimeout(() => _setup_lifecycle_jobs_duplicate_fix(frm), 300);
		}

		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Load Standard Lifecycle Jobs"), function () {
				frappe.call({
					method: "logistics.mice.doctype.mice_project.mice_project.reload_standard_service_activities",
					args: { show: frm.doc.name },
					callback: function () {
						frm.reload_doc();
						frappe.show_alert({ message: __("Standard lifecycle jobs loaded"), indicator: "green" });
					},
				});
			}, __("Lifecycle"));

			frm.add_custom_button(__("Apply Lifecycle Template"), function () {
				if (window.logistics_open_apply_lifecycle_template_dialog) {
					window.logistics_open_apply_lifecycle_template_dialog(frm, "MICE Project");
				} else {
					frappe.require(
						"/assets/logistics/js/apply_lifecycle_template_dialog.js",
						function () {
							window.logistics_open_apply_lifecycle_template_dialog(frm, "MICE Project");
						}
					);
				}
			}, __("Lifecycle"));
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
		// Profitability tab loading + click handler is registered by
		// logistics/public/js/profitability_project_form.js — keep it in one place
		// to avoid double-firing the GL query.
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
