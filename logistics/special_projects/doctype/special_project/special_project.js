// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Global helper used by the "Submission Blocked" msgprint primary_action to
// jump to the relevant tab on the current Special Project form, then close
// the dialog. The Python side passes `{ fieldname: "fulfillment_tab" }`
// (or "lifecycle_tab") as args.
window.logistics = window.logistics || {};
window.logistics.special_project_modals = window.logistics.special_project_modals || {};
window.logistics.special_project_modals.go_to_tab = function (args) {
	const fieldname = (args && args.fieldname) || "fulfillment_tab";
	const frm = cur_frm;
	if (frm && frm.fields_dict && frm.fields_dict[fieldname] && frm.fields_dict[fieldname].tab) {
		try {
			frm.fields_dict[fieldname].tab.set_active();
			frm.scroll_to_field && frm.scroll_to_field(fieldname);
		} catch (e) {
			// silent fail – modal still closes below
		}
	}
	if (typeof frappe !== "undefined" && frappe.hide_msgprint) {
		frappe.hide_msgprint();
	}
};

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: "Special Project", docname: frm.doc.name },
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
	const field = frm.fields_dict.lifecycle_jobs;
	if (!field || !field.grid || field.grid._logistics_lifecycle_duplicate_patched) {
		return;
	}
	const grid = field.grid;
	const orig_add_new_row = grid.add_new_row.bind(grid);
	grid.add_new_row = function (idx, callback, show, copy_doc, go_to_last_page, go_to_first_page) {
		if (copy_doc) {
			copy_doc = Object.assign({}, copy_doc);
			copy_doc.job_type = null;
			copy_doc.job_no = null;
		}
		return orig_add_new_row(idx, callback, show, copy_doc, go_to_last_page, go_to_first_page);
	};
	const orig_duplicate_row = grid.duplicate_row.bind(grid);
	grid.duplicate_row = function (d, copy_doc) {
		if (copy_doc) {
			copy_doc = Object.assign({}, copy_doc);
			copy_doc.job_type = null;
			copy_doc.job_no = null;
		}
		orig_duplicate_row(d, copy_doc);
		d.job_type = null;
		d.job_no = null;
		return d;
	};
	grid._logistics_lifecycle_duplicate_patched = true;
}

function logistics_clear_stale_package_grid_settings(frm) {
	const grid_view = frappe.get_user_settings(frm.doctype, "GridView") || {};
	let changed = false;
	[
		"Special Project Package",
		"Special Project Site Material",
		"Special Project Site Receipt",
	].forEach((child_dt) => {
		const cols = grid_view[child_dt];
		if (!Array.isArray(cols)) {
			return;
		}
		const filtered = cols.filter((col) => col && col.fieldname !== "item");
		if (filtered.length !== cols.length) {
			grid_view[child_dt] = filtered;
			changed = true;
		}
	});
	if (changed) {
		frappe.model.user_settings.save(frm.doctype, "GridView", grid_view);
	}
}

function logistics_set_packages_site_query(frm) {
	frm.set_query("site", "packages", function () {
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
	frm.set_query("warehouse_item", "packages", function (doc) {
		const filters = {};
		if (doc.customer) {
			filters.customer = doc.customer;
		}
		return { filters: filters };
	});
	frm.set_query("commodity", "packages", function () {
		return { filters: { active: 1 } };
	});
}

const SP_PACKAGES_SUMMARY_COLLAPSED_KEY = "sp_packages_summary_collapsed";

function _sync_packages_summary_full_width($root) {
	if (!$root || !$root.length) {
		return;
	}
	let full_width = false;
	try {
		full_width =
			document.body.classList.contains("full-width") ||
			JSON.parse(localStorage.container_fullwidth || "false");
	} catch (e) {
		full_width = document.body.classList.contains("full-width");
	}
	$root.toggleClass("is-page-full-width", !!full_width);
}

function _bind_packages_summary_layout(frm) {
	const $wrapper = frm.fields_dict.packages_summary?.$wrapper;
	if (!$wrapper) {
		return;
	}
	$wrapper.addClass("sp-packages-summary-field");
	const $root = $wrapper.find(".sp-packages-summary");
	_sync_packages_summary_full_width($root);

	if (!window._logistics_sp_pks_fullwidth_bound) {
		window._logistics_sp_pks_fullwidth_bound = true;
		$(document.body).on("toggleFullWidth.sp-pks", function () {
			$(".sp-packages-summary").each(function () {
				_sync_packages_summary_full_width($(this));
			});
		});
	}
}

function _bind_packages_summary_collapse(frm) {
	const $wrapper = frm.fields_dict.packages_summary?.$wrapper;
	if (!$wrapper) {
		return;
	}
	const $root = $wrapper.find(".sp-packages-summary");
	if (!$root.length) {
		return;
	}
	const $toggle = $root.find(".sp-pks-toggle");
	if (!$toggle.length) {
		return;
	}

	function set_collapsed(collapsed) {
		$root.toggleClass("is-collapsed", collapsed);
		$toggle.attr("aria-expanded", collapsed ? "false" : "true");
		$toggle.attr(
			"title",
			collapsed ? __("Expand summary") : __("Collapse summary")
		);
		try {
			localStorage.setItem(SP_PACKAGES_SUMMARY_COLLAPSED_KEY, collapsed ? "1" : "0");
		} catch (e) {
			/* ignore quota / private mode */
		}
	}

	let collapsed = false;
	try {
		collapsed = localStorage.getItem(SP_PACKAGES_SUMMARY_COLLAPSED_KEY) === "1";
	} catch (e) {
		collapsed = false;
	}
	set_collapsed(collapsed);

	$toggle.off("click.sp-pks").on("click.sp-pks", function () {
		set_collapsed(!$root.hasClass("is-collapsed"));
	});
}

function _refresh_packages_summary(frm) {
	if (!frm.fields_dict.packages_summary || !frm.doc.name || frm.doc.__islocal) {
		return;
	}
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_packages_summary_html",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.packages_summary) {
				frm.fields_dict.packages_summary.$wrapper.html(r.message);
				_bind_packages_summary_layout(frm);
				_bind_packages_summary_collapse(frm);
			}
		},
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

frappe.ui.form.on("Special Project", {
	onload: function (frm) {
		if (frm.get_docfield && frm.get_docfield("charges")) {
			frm.set_df_property("charges", "cannot_add_rows", 1);
			frm.set_df_property("charges", "allow_bulk_edit", 0);
		}
	},
	setup: function (frm) {
		if (logistics.lifecycle && logistics.lifecycle.setup_queries) {
			logistics.lifecycle.setup_queries(frm);
		}
		frm.set_query("milestone_template", function () {
			return frappe.call("logistics.document_management.api.get_milestone_template_filters", { doctype: frm.doctype }).then(function (r) {
				return r.message || { filters: [] };
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
	refresh: function (frm) {
		logistics_set_internal_job_site_query(frm);
		logistics_clear_stale_package_grid_settings(frm);
		logistics_set_packages_site_query(frm);
		_setup_lifecycle_jobs_duplicate_fix(frm);
		_refresh_packages_summary(frm);
		if (!frm.fields_dict.lifecycle_jobs?.grid?._logistics_lifecycle_duplicate_patched) {
			setTimeout(() => _setup_lifecycle_jobs_duplicate_fix(frm), 300);
		}
		// Load dashboard HTML in Dashboard tab (only when doc is saved)
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frappe.call({
					method: "logistics.special_projects.doctype.special_project.special_project.get_dashboard_html",
					args: { special_project: frm.doc.name },
					callback: function (r) {
						if (r.message && frm.fields_dict.dashboard_html) {
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
					frm._dashboard_html_called = false;
				}, 2000);
			}
		}

		// Milestones tab: shared get_milestone_html pipeline with Sea Shipment (tab always visible).
		if (frm.fields_dict.milestone_html && frm.doc.name && !frm.doc.__islocal) {
			_load_milestone_html(frm);
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.milestone_html").on("click.milestone_html", '[data-fieldname="milestones_tab"]', function () {
				_load_milestone_html(frm);
			});
		}

		_refresh_cost_revenue_summary(frm);
		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, "Special Project");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				if (window.logistics_load_documents_html) {
					window.logistics_load_documents_html(frm, "Special Project");
				}
			});
		}
		// Profitability tab loading + click handler is registered by
		// logistics/public/js/profitability_project_form.js — keep it in one place
		// to avoid double-firing the GL query.

		// --- Action menu: Get Milestones, Get Documents, Calculate Charges, Apply Lifecycle Template ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Get Milestones"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_milestones_from_template",
					args: { doctype: "Special Project", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Action"));

			if (frm.fields_dict.documents) {
				frm.add_custom_button(__("Get Documents"), function () {
					frappe.call({
						method: "logistics.document_management.api.populate_documents_from_template",
						args: { doctype: "Special Project", docname: frm.doc.name },
						callback: function (r) {
							if (r.message && r.message.added !== undefined) {
								frappe.show_alert({
									message: __("Added {0} document(s) from template.", [r.message.added]),
									indicator: "green",
								});
								frm.reload_doc();
							} else if (r.message && r.message.message) {
								frappe.msgprint(r.message.message);
							}
						},
					});
				}, __("Action"));
			}

			if (frm.doc.charges && frm.doc.charges.length > 0) {
				frm.add_custom_button(__("Calculate Charges"), function () {
					frappe.call({
						method: "logistics.special_projects.doctype.special_project.special_project.recalculate_all_charges",
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

			frm.add_custom_button(__("Apply Lifecycle Template"), function () {
				if (window.logistics_open_apply_lifecycle_template_dialog) {
					window.logistics_open_apply_lifecycle_template_dialog(frm, "Special Project");
				} else {
					frappe.require(
						"/assets/logistics/js/apply_lifecycle_template_dialog.js",
						function () {
							window.logistics_open_apply_lifecycle_template_dialog(frm, "Special Project");
						}
					);
				}
			}, __("Action"));
		}

		// --- Create menu: Sales Invoice, Purchase Invoice, Booking/Order, Change Request ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Sales Invoice"), function () {
				if (typeof window.show_create_sales_invoice_dialog === "function") {
					window.show_create_sales_invoice_dialog(frm);
				} else {
					frappe.msgprint({
						title: __("Not available"),
						message: __("The Sales Invoice dialog could not load. Refresh the page or contact your administrator."),
						indicator: "red",
					});
				}
			}, __("Create"));

			frm.add_custom_button(__("Purchase Invoice"), function () {
				if (typeof window.show_create_purchase_invoice_dialog === "function") {
					window.show_create_purchase_invoice_dialog(frm);
				} else {
					frappe.msgprint({
						title: __("Not available"),
						message: __("The Purchase Invoice dialog could not load. Refresh the page or contact your administrator."),
						indicator: "red",
					});
				}
			}, __("Create"));

			frm.add_custom_button(__("Booking / Order"), function () {
				function _openDlg() {
					if (window.logistics_show_special_project_booking_dialog) {
						window.logistics_show_special_project_booking_dialog(frm);
					} else {
						frappe.msgprint({
							title: __("Not available"),
							message: __("The Booking / Order dialog could not load. Refresh the page or contact your administrator."),
							indicator: "red",
						});
					}
				}
				if (window.logistics_show_special_project_booking_dialog) {
					_openDlg();
				} else {
					frappe.require(
						"/assets/logistics/js/special_project_booking_dialog.js",
						_openDlg
					);
				}
			}, __("Create"));

			frm.add_custom_button(__("Change Request"), function () {
				frappe.call({
					method: "logistics.pricing_center.doctype.change_request.change_request.create_change_request",
					args: { job_type: "Special Project", job_name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.set_route("Form", "Change Request", r.message);
						}
					},
				});
			}, __("Create"));

			frm.add_custom_button(__("Refresh Delivery Funnel"), function () {
				frappe.call({
					method: "logistics.special_projects.special_project_packages.recalculate_package_delivery_balances",
					args: { special_project: frm.doc.name },
					callback: function () {
						frm.reload_doc();
					},
				});
			}, __("Packages"));
		}
	},
	packages_add: function (frm) {
		_refresh_packages_summary(frm);
	},
	packages_remove: function (frm) {
		_refresh_packages_summary(frm);
	},
	deliveries_add: function (frm) {
		_refresh_packages_summary(frm);
	},
	deliveries_remove: function (frm) {
		_refresh_packages_summary(frm);
	},
	milestones_add: function (frm) {
		_refresh_milestone_html(frm);
	},
	milestones_remove: function (frm) {
		_refresh_milestone_html(frm);
	},
	lifecycle_stage(frm) {
		_refresh_dashboard_html(frm);
	},

	lifecycle_jobs_add: function (frm, cdt, cdn) {
		if (logistics.lifecycle && logistics.lifecycle.clear_lifecycle_job_link_on_row_add) {
			logistics.lifecycle.clear_lifecycle_job_link_on_row_add(frm, cdt, cdn);
		} else if (cdt === "Lifecycle Job" && cdn && locals[cdt] && locals[cdt][cdn]) {
			const row = locals[cdt][cdn];
			row.job_type = null;
			row.job_no = null;
			const grid_row = frm.fields_dict.lifecycle_jobs?.grid?.grid_rows_by_docname?.[cdn];
			if (grid_row) {
				grid_row.refresh_field("job_type");
				grid_row.refresh_field("job_no");
			}
		}
		_refresh_cost_revenue_summary(frm);
		_refresh_dashboard_html(frm);
	},
	lifecycle_jobs_remove: function (frm) {
		_refresh_cost_revenue_summary(frm);
		_refresh_dashboard_html(frm);
	},
});

frappe.ui.form.on("Special Project Charges", {
	service_type: function (frm) {
		if (frm.doc.__islocal) return;
		_refresh_cost_revenue_summary(frm);
	},
	lifecycle_job_row: function (frm) {
		if (frm.doc.__islocal) return;
		_refresh_cost_revenue_summary(frm);
	},
	estimated_cost: function (frm) {
		if (frm.doc.__islocal) return;
		_refresh_cost_revenue_summary(frm);
	},
	estimated_revenue: function (frm) {
		if (frm.doc.__islocal) return;
		_refresh_cost_revenue_summary(frm);
	},
});

function _refresh_cost_revenue_summary(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.cost_revenue_html) return;
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_cost_revenue_summary",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.cost_revenue_html) {
				frm.fields_dict.cost_revenue_html.$wrapper.html(r.message);
			}
		},
	});
}

function _refresh_dashboard_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.dashboard_html) return;
	frm._dashboard_html_called = false;
	frappe.call({
		method: "logistics.special_projects.doctype.special_project.special_project.get_dashboard_html",
		args: { special_project: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.dashboard_html) {
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
}

function _refresh_milestone_html(frm) {
	if (!frm.doc.name || frm.doc.__islocal || !frm.fields_dict.milestone_html) return;
	frm._milestone_html_called = false;
	_load_milestone_html(frm);
}
