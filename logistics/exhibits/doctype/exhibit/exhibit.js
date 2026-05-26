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

function _create_docket_for_participant_row(frm, row) {
	if (!row) return;
	if (!row.customer) {
		frappe.msgprint({
			message: __("Set a <b>Customer</b> on this row before creating a Docket."),
			indicator: "orange",
		});
		return;
	}
	if (row.docket) {
		frappe.set_route("Form", "Docket", row.docket);
		return;
	}
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save the Exhibit first, then create the Docket."));
		return;
	}
	frappe.model.with_doctype("Docket", function () {
		const docket = frappe.model.get_new_doc("Docket");
		docket.exhibit = frm.doc.name;
		docket.exhibitor = row.customer;
		docket.exhibitor_name = row.participant_name || "";
		docket.booth_no = row.booth_no || "";
		frappe.set_route("Form", "Docket", docket.name);
	});
}

function _open_or_create_docket_for_row(frm, row) {
	if (!row) return;
	if (row.docket) {
		frappe.set_route("Form", "Docket", row.docket);
	} else {
		_create_docket_for_participant_row(frm, row);
	}
}

function _setup_dockets_grid_buttons(frm) {
	const grid = frm.fields_dict.dockets && frm.fields_dict.dockets.grid;
	if (!grid) return;

	// Drop any previously registered custom buttons (idempotent on refresh).
	grid.custom_buttons = grid.custom_buttons || {};
	const create_label = __("Create Docket");
	const open_label = __("Open Docket");
	[create_label, open_label].forEach(function (lbl) {
		if (grid.custom_buttons[lbl]) {
			try { grid.custom_buttons[lbl].remove(); } catch (e) { /* ignore */ }
			delete grid.custom_buttons[lbl];
		}
	});

	grid.add_custom_button(create_label, function () {
		const selected = grid.get_selected_children();
		if (!selected || !selected.length) {
			frappe.msgprint(__("Select an Exhibitor row first."));
			return;
		}
		_create_docket_for_participant_row(frm, selected[0]);
	}).addClass("btn-primary");

	grid.add_custom_button(open_label, function () {
		const selected = grid.get_selected_children();
		if (!selected || !selected.length) {
			frappe.msgprint(__("Select a row first."));
			return;
		}
		_open_or_create_docket_for_row(frm, selected[0]);
	});
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
	onload: function (frm) {
		if (frm.get_docfield && frm.get_docfield("charges")) {
			frm.set_df_property("charges", "cannot_add_rows", 1);
			frm.set_df_property("charges", "allow_bulk_edit", 0);
		}
	},
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

			frm.add_custom_button(__("New Docket"), function () {
				frappe.new_doc("Docket", { exhibit: frm.doc.name });
			}, __("Create"));
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

		if (window.logistics && logistics.add_get_charges_from_quotation_button_if_allowed) {
			logistics.add_get_charges_from_quotation_button_if_allowed(frm);
		}
		if (frm.doc.charges && frm.doc.charges.length > 0) {
			frm.add_custom_button(__("Calculate Charges"), function () {
				frappe.call({
					method: "logistics.exhibits.doctype.exhibit.exhibit.recalculate_all_charges",
					args: { docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "green" }, 3);
						}
					},
				});
			}, __("Action"));
		}

		if (frm.doc.project && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Open Project"), function () {
				frappe.set_route("Form", "Project", frm.doc.project);
			}, __("Action"));
		}

		_refresh_cost_revenue_summary(frm);

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
	},
	lifecycle_jobs_remove: function (frm) {
		_refresh_cost_revenue_summary(frm);
	},
});

frappe.ui.form.on("Exhibit Docket", {
	dockets_add: function (frm) {
		_setup_dockets_grid_buttons(frm);
	},
	customer: function (frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row || !row.customer || row.participant_name) return;
		frappe.db.get_value("Customer", row.customer, "customer_name").then(function (r) {
			if (r && r.message && r.message.customer_name) {
				frappe.model.set_value(cdt, cdn, "participant_name", r.message.customer_name);
			}
		});
	},
	docket: function (frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (row && row.docket) {
			frappe.set_route("Form", "Docket", row.docket);
		}
	},
});
