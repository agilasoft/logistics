// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: "Exhibit", docname: frm.doc.name },
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
		method: "logistics.exhibits.doctype.exhibit.exhibit.get_cost_revenue_summary",
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
		method: "logistics.exhibits.doctype.exhibit.exhibit.get_dashboard_html",
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

function _open_docket_for_row(frm, row) {
	if (!row || !row.docket) {
		frappe.msgprint(__("Select a row with a Docket first."));
		return;
	}
	frappe.set_route("Form", "Docket", row.docket);
}

function _open_exhibit_link_docket_dialog(frm) {
	if (window.logistics_open_exhibit_link_docket_dialog) {
		window.logistics_open_exhibit_link_docket_dialog(frm);
		return;
	}
	frappe.require("/assets/logistics/js/exhibit_link_docket_dialog.js", function () {
		window.logistics_open_exhibit_link_docket_dialog(frm);
	});
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
	const stale_labels = [__("Open Docket"), __("Create Docket"), __("View Dockets"), __("Add Dockets")];
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
		__("Open Docket"),
		function () {
			const selected = grid.get_selected_children();
			const row = selected && selected.length ? selected[0] : null;
			_open_docket_for_row(frm, row);
		},
		"top"
	);

	grid.add_custom_button(
		__("Add Dockets"),
		function () {
			_open_exhibit_link_docket_dialog(frm);
		},
		"top"
	);

	// Ensure the footer stays available if Frappe toggles it for read-only grids.
	grid.wrapper.find(".grid-footer").removeClass("hidden");
}

function logistics_set_internal_job_site_query(frm) {
	frm.set_query("sp_site", "lifecycle_jobs", function () {
		const cust = frm.doc.customer;
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

frappe.ui.form.on("Exhibit", {
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
	},
	refresh: function (frm) {
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
					method: "logistics.exhibits.doctype.exhibit.exhibit.reload_standard_service_activities",
					args: { show: frm.doc.name },
					callback: function () {
						frm.reload_doc();
						frappe.show_alert({ message: __("Standard lifecycle jobs loaded"), indicator: "green" });
					},
				});
			}, __("Lifecycle"));

			frm.add_custom_button(__("Apply Lifecycle Template"), function () {
				if (window.logistics_open_apply_lifecycle_template_dialog) {
					window.logistics_open_apply_lifecycle_template_dialog(frm, "Exhibit");
				} else {
					frappe.require(
						"/assets/logistics/js/apply_lifecycle_template_dialog.js",
						function () {
							window.logistics_open_apply_lifecycle_template_dialog(frm, "Exhibit");
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
			window.logistics_load_documents_html(frm, "Exhibit");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.documents_html")
				.on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
					if (window.logistics_load_documents_html) {
						window.logistics_load_documents_html(frm, "Exhibit");
					}
				});
		}
		// Profitability tab loading + click handler is registered by
		// logistics/public/js/profitability_project_form.js — keep it in one place
		// to avoid double-firing the GL query.
	},
	venue_address: function (frm) {
		_refresh_exhibit_dashboard_html(frm);
	},
	venue_name: function (frm) {
		_refresh_exhibit_dashboard_html(frm);
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
