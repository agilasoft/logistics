// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Static link_filters on exhibitor/customer (Customer.disabled) trigger a
 * permlevel-0 field permission check (Customer.0) for roles that can create
 * Dockets but cannot read base Customer fields. Filtering is handled by
 * get_exhibitor_options_query on the server instead.
 */
function logistics_strip_docket_customer_link_filters(frm) {
	["exhibitor", "customer"].forEach((fieldname) => {
		const df = frappe.meta.get_docfield("Docket", fieldname);
		if (df && df.link_filters) {
			df.link_filters = null;
		}
		if (frm.fields_dict[fieldname]?.df?.link_filters) {
			frm.fields_dict[fieldname].df.link_filters = null;
		}
	});
}

function logistics_docket_set_exhibitor_query(frm) {
	frm.set_query("exhibitor", function () {
		const exhibit = frm.doc.exhibit;
		if (!exhibit) return { filters: [["Customer", "name", "=", ""]] };
		return {
			query: "logistics.mice.doctype.docket.docket.get_exhibitor_options_query",
			filters: { exhibit: exhibit },
		};
	});
}

function logistics_docket_set_site_query(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer || frm.doc.exhibitor);
	});
}

function _load_docket_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: frm.doctype, docname: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.milestone_html) {
				frm.fields_dict.milestone_html.$wrapper.html(r.message);
			}
		},
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

function _logistics_docket_set_linked_services_read_only(frm) {
	if (window.logistics && logistics.setup_virtual_linked_services_grid) {
		logistics.setup_virtual_linked_services_grid(frm);
	}
	if (window.logistics_hide_cannot_add_rows_buttons) {
		logistics_hide_cannot_add_rows_buttons(frm, "linked_services");
	}
}

frappe.ui.form.on("Docket", {
	onload(frm) {
		logistics_strip_docket_customer_link_filters(frm);
		logistics_docket_set_exhibitor_query(frm);
		logistics_docket_set_site_query(frm);
		_logistics_set_charges_cannot_add_rows(frm);
		_logistics_docket_set_linked_services_read_only(frm);
		_docket_update_measurement_fields_readonly(frm);
	},
	setup(frm) {
		frm.set_query("milestone_template", function () {
			return frappe
				.call("logistics.document_management.api.get_milestone_template_filters", {
					doctype: frm.doctype,
				})
				.then(function (r) {
					return r.message || { filters: [] };
				});
		});
		frm.set_query("warehouse_item", "packages", function () {
			var filters = {};
			if (frm.doc.customer) {
				filters.customer = frm.doc.customer;
			}
			return { filters: filters };
		});
	},
	refresh(frm) {
		logistics_strip_docket_customer_link_filters(frm);
		logistics_docket_set_exhibitor_query(frm);
		logistics_docket_set_site_query(frm);
		_logistics_set_charges_cannot_add_rows(frm);
		_logistics_docket_set_linked_services_read_only(frm);
		setTimeout(function () {
			if (window.logistics_hide_cannot_add_rows_buttons) {
				window.logistics_hide_cannot_add_rows_buttons(frm, "charges");
				window.logistics_hide_cannot_add_rows_buttons(frm, "linked_services");
			}
		}, 0);
		_load_docket_milestone_html(frm);

		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, frm.doctype);
		}

		if (!frm.doc.__islocal && frm.doc.exhibit) {
			frm.add_custom_button(
				__("Open Exhibit"),
				function () {
					frappe.set_route("Form", "MICE Project", frm.doc.exhibit);
				},
				__("Action")
			);
		}

		if (!frm.doc.__islocal && frm.doc.charges && frm.doc.charges.length) {
			frm.add_custom_button(
				__("Recalculate Charges"),
				function () {
					frappe.call({
						method:
							"logistics.mice.doctype.docket.docket.recalculate_all_charges",
						args: { docname: frm.doc.name },
						freeze: true,
						callback: function (r) {
							if (r.message && r.message.success) {
								frappe.show_alert({
									message: r.message.message,
									indicator: "green",
								});
								frm.reload_doc();
							}
						},
					});
				},
				__("Action")
			);
		}

		if (!frm.doc.__islocal) {
			frm.add_custom_button(
				__("Booking / Order"),
				function () {
					function _openDlg() {
						if (window.logistics_show_docket_booking_dialog) {
							window.logistics_show_docket_booking_dialog(frm);
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
					if (window.logistics_show_docket_booking_dialog) {
						_openDlg();
					} else {
						frappe.require(
							"/assets/logistics/js/docket_booking_dialog.js",
							_openDlg
						);
					}
				},
				__("Create")
			);

			frm.add_custom_button(
				__("Create Change Request"),
				function () {
					frappe.call({
						method:
							"logistics.pricing_center.doctype.change_request.change_request.create_change_request",
						args: { job_type: "Docket", job_name: frm.doc.name },
						callback: function (r) {
							if (r.message) {
								frappe.set_route("Form", "Change Request", r.message);
							}
						},
					});
				},
				__("Create")
			);

			frm.add_custom_button(
				__("Sales Invoice"),
				function () {
					if (typeof window.show_create_sales_invoice_dialog === "function") {
						window.show_create_sales_invoice_dialog(frm);
					} else {
						frappe.require(
							"/assets/logistics/js/sales_invoice_dialog.js",
							function () {
								if (typeof window.show_create_sales_invoice_dialog === "function") {
									window.show_create_sales_invoice_dialog(frm);
								} else {
									frappe.msgprint({
										title: __("Not available"),
										message: __(
											"The Sales Invoice dialog could not load. Refresh the page or contact your administrator."
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

			// Post menu — same set as Air / Sea Shipment. Dockets are main Services
			// (the Internal Jobs they spawn carry their own Post buttons), so the
			// posting surface lives on the Docket itself.
			setTimeout(function () {
				frm.add_custom_button(
					__("Standard Costs"),
					function () {
						frappe.call({
							method:
								"logistics.mice.doctype.docket.docket.post_standard_costs",
							args: { docname: frm.doc.name },
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({
										message: r.message.message,
										indicator: "blue",
									});
									frm.reload_doc();
								}
							},
						});
					},
					__("Post")
				);

				if (frm.doc.sales_quote && frm.doc.company) {
					frm.add_custom_button(
						__("Intercompany Transactions"),
						function () {
							frappe.call({
								method:
									"logistics.intercompany.intercompany_invoice.create_intercompany_invoices_for_quote",
								args: {
									sales_quote_name: frm.doc.sales_quote,
									posting_date: frappe.datetime.get_today(),
								},
								callback: function (r) {
									if (r.message) {
										var msg =
											r.message.message ||
											__("Intercompany invoices processed");
										if (r.message.created !== undefined) {
											msg = __("Created {0} intercompany invoice(s).", [
												r.message.created,
											]);
										}
										frappe.show_alert({ message: msg, indicator: "green" }, 5);
										frm.reload_doc();
									}
								},
							});
						},
						__("Post")
					);

					frm.add_custom_button(
						__("Internal Billing"),
						function () {
							frappe.call({
								method:
									"logistics.billing.internal_billing.create_internal_billing_for_quote",
								args: {
									sales_quote_name: frm.doc.sales_quote,
									posting_date: frappe.datetime.get_today(),
								},
								callback: function (r) {
									if (r.message) {
										var msg =
											r.message.message || __("Internal billing processed");
										if (
											r.message.journal_entries &&
											r.message.journal_entries.length
										) {
											msg = __("Created Journal Entries: {0}.", [
												r.message.journal_entries.join(", "),
											]);
										} else if (r.message.journal_entry) {
											msg = __("Created Journal Entry {0}.", [
												r.message.journal_entry,
											]);
										}
										frappe.show_alert({ message: msg, indicator: "blue" }, 5);
										frm.reload_doc();
									}
								},
							});
						},
						__("Post")
					);
				}

				_docket_add_recognition_buttons(frm);

				if (
					window.logistics &&
					logistics.job_charge_reopen &&
					logistics.job_charge_reopen.setup
				) {
					logistics.job_charge_reopen.setup(frm);
				}
			}, 100);
		}
	},
	exhibit(frm) {
		if (frm.doc.exhibit) {
			frm.set_value("exhibitor", null);
			frm.set_value("booth_no", null);
			logistics_docket_set_exhibitor_query(frm);
		}
	},
	milestone_template(frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_milestones_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) {
							frappe.show_alert(
								{ message: __(r.message.message), indicator: "blue" },
								5
							);
						}
					}
				},
			});
		});
	},
	document_list_template(frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_documents_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) {
							frappe.show_alert(
								{ message: __(r.message.message), indicator: "blue" },
								5
							);
						}
					}
				},
			});
		});
	},
	aggregate_volume_from_packages(frm) {
		if (frm.is_new() || frm.doc.__islocal) return;
		if (frm.doc.override_volume_weight) return;
		if (!frm.doc.packages || frm.doc.packages.length === 0) {
			return;
		}
		var _aggregate_docname = frm.doc.name;
		frappe.call({
			method:
				"logistics.mice.doctype.docket.docket.aggregate_volume_from_packages_remote",
			args: { doc: frm.doc },
			callback: function (r) {
				if (frm.doc.name !== _aggregate_docname) {
					return;
				}
				if (r && !r.exc && r.message) {
					if (r.message.total_volume !== undefined && frm.fields_dict.total_volume) {
						frm.set_value("total_volume", r.message.total_volume);
					}
					if (r.message.total_weight !== undefined && frm.fields_dict.total_weight) {
						frm.set_value("total_weight", r.message.total_weight);
					}
					if (r.message.total_packages !== undefined && frm.fields_dict.total_packages) {
						frm.set_value("total_packages", r.message.total_packages);
					}
					if (r.message.total_containers !== undefined && frm.fields_dict.total_containers) {
						frm.set_value("total_containers", r.message.total_containers);
					}
					if (r.message.total_teus !== undefined && frm.fields_dict.total_teus) {
						frm.set_value("total_teus", r.message.total_teus);
					}
					if (r.message.chargeable !== undefined && frm.fields_dict.chargeable) {
						frm.set_value("chargeable", r.message.chargeable);
					}
				}
			},
		});
	},
	containers_add(frm) {
		_docket_refresh_package_container_options(frm);
	},
	containers_remove(frm) {
		_docket_refresh_package_container_options(frm);
	},
	packages_on_form_rendered(frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(
				frm,
				"Docket Package",
				"packages",
				"docket_volume"
			);
		}
	},
	override_volume_weight(frm) {
		_docket_update_measurement_fields_readonly(frm);
	},
});

function _docket_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === "function") fn(frm, cdt, cdn, grid_row, "packages");
}

function _docket_is_grid_dialog_open() {
	if (typeof cur_dialog !== "undefined" && cur_dialog && cur_dialog.display) return true;
	if ($(".grid-row-open").length > 0) return true;
	if ($(".grid-form-dialog:visible").length > 0) return true;
	if ($(".grid-row-form:visible, .grid-form-body:visible").length > 0) return true;
	if ($(".modal:visible .grid-row-form, .form-dialog:visible .grid-row-form").length > 0)
		return true;
	return false;
}

function _docket_update_measurement_fields_readonly(frm) {
	var readonly = !frm.doc.override_volume_weight;
	if (frm.fields_dict.total_volume) frm.set_df_property("total_volume", "read_only", readonly);
	if (frm.fields_dict.total_weight) frm.set_df_property("total_weight", "read_only", readonly);
	if (frm.fields_dict.chargeable) frm.set_df_property("chargeable", "read_only", readonly);
}

function _docket_apply_container_cargo_to_form(frm, container_cargo) {
	if (!container_cargo || !container_cargo.length || !frm.doc.containers) return;
	container_cargo.forEach(function (item) {
		var row = (frm.doc.containers || []).find(function (c) {
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
	frm.refresh_field("containers");
	var grid = frm.fields_dict.containers && frm.fields_dict.containers.grid;
	if (grid && grid.grid_form && grid.grid_form.doc) {
		var gd = grid.grid_form.doc;
		var match = container_cargo.find(function (item) {
			return item.idx === gd.idx;
		});
		if (match) {
			[
				"packages_in_container",
				"weight_in_container",
				"volume_in_container",
				"max_weight",
				"max_volume",
				"utilization_percentage",
			].forEach(function (f) {
				if (match[f] !== undefined) grid.grid_form.set_value(f, match[f]);
			});
		}
	}
}

function _docket_refresh_container_cargo_metrics(frm) {
	frappe.call({
		method: "logistics.sea_freight.container_row_metrics.compute_container_cargo_metrics",
		args: { doc: frm.doc },
		freeze: false,
		callback: function (r) {
			if (r && !r.exc && r.message && r.message.container_cargo) {
				_docket_apply_container_cargo_to_form(frm, r.message.container_cargo);
			}
		},
	});
}

function _docket_refresh_container_cargo_debounced(frm) {
	if (frm._docket_container_cargo_timer) clearTimeout(frm._docket_container_cargo_timer);
	frm._docket_container_cargo_timer = setTimeout(function () {
		frm._docket_container_cargo_timer = null;
		_docket_refresh_container_cargo_metrics(frm);
	}, 300);
}

function _docket_update_packing_summary_client_side(frm) {
	var containers = frm.doc.containers || [];
	var packages = frm.doc.packages || [];
	var totalPackages = 0;
	packages.forEach(function (p) {
		totalPackages += parseFloat(p.no_of_packs) || parseFloat(p.quantity) || 0;
	});
	frm.set_value("total_containers", containers.length);
	frm.set_value("total_packages", totalPackages);
}

function _docket_refresh_packing_summary_debounced(frm) {
	if (_docket_is_grid_dialog_open()) return;
	if (frm.doc.override_volume_weight) return;
	if (frm._docket_packing_summary_timer) clearTimeout(frm._docket_packing_summary_timer);
	frm._docket_packing_summary_timer = setTimeout(function () {
		frm._docket_packing_summary_timer = null;
		if (_docket_is_grid_dialog_open()) return;
		if (frm.is_new() || frm.doc.__islocal) {
			_docket_update_packing_summary_client_side(frm);
		} else {
			frm.trigger("aggregate_volume_from_packages");
		}
	}, 300);
}

function _docket_package_or_container_changed(frm) {
	_docket_refresh_container_cargo_debounced(frm);
	_docket_refresh_packing_summary_debounced(frm);
}

function _docket_refresh_package_container_options(frm) {
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
			apply_options(names);
		});
}

frappe.ui.form.on("Docket Package", {
	form_render(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger("packages_on_form_rendered");
		_docket_refresh_package_container_options(frm);
		setTimeout(function () {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === "function") fn_immediate(frm, cdt, cdn);
			else if (typeof fn_debounced === "function") fn_debounced(frm, cdt, cdn);
			else
				_docket_volume_fallback(
					frm,
					cdt,
					cdn,
					frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form()
				);
		}, 50);
	},
	commodity(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.commodity) {
			frappe.db.get_value("Commodity", row.commodity, "default_hs_code", (r) => {
				if (r && r.default_hs_code) {
					frappe.model.set_value(cdt, cdn, "hs_code", r.default_hs_code);
				} else {
					frappe.model.set_value(cdt, cdn, "hs_code", "");
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, "hs_code", "");
		}
	},
	volume(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		frm.trigger("aggregate_volume_from_packages");
		_docket_package_or_container_changed(frm);
	},
	weight(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		frm.trigger("aggregate_volume_from_packages");
		_docket_package_or_container_changed(frm);
	},
	container(frm) {
		_docket_package_or_container_changed(frm);
	},
	no_of_packs(frm) {
		_docket_package_or_container_changed(frm);
	},
	weight_uom(frm, cdt, cdn) {
		if (frm.is_new() || frm.doc.__islocal) return;
		setTimeout(function () {
			frm.trigger("aggregate_volume_from_packages");
		}, 100);
	},
	length(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === "function") fn(frm, cdt, cdn);
		else
			_docket_volume_fallback(
				frm,
				cdt,
				cdn,
				frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form()
			);
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function () {
				frm.trigger("aggregate_volume_from_packages");
			}, 100);
		}
	},
	width(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === "function") fn(frm, cdt, cdn);
		else
			_docket_volume_fallback(
				frm,
				cdt,
				cdn,
				frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form()
			);
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function () {
				frm.trigger("aggregate_volume_from_packages");
			}, 100);
		}
	},
	height(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === "function") fn(frm, cdt, cdn);
		else
			_docket_volume_fallback(
				frm,
				cdt,
				cdn,
				frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form()
			);
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function () {
				frm.trigger("aggregate_volume_from_packages");
			}, 100);
		}
	},
	dimension_uom(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === "function") fn(frm, cdt, cdn);
		else
			_docket_volume_fallback(
				frm,
				cdt,
				cdn,
				frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form()
			);
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function () {
				frm.trigger("aggregate_volume_from_packages");
			}, 100);
		}
	},
	volume_uom(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === "function") fn(frm, cdt, cdn);
		else
			_docket_volume_fallback(
				frm,
				cdt,
				cdn,
				frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form()
			);
		if (!frm.is_new() && !frm.doc.__islocal) {
			setTimeout(function () {
				frm.trigger("aggregate_volume_from_packages");
			}, 100);
		}
	},
});

frappe.ui.form.on("Docket Containers", {
	form_render(frm) {
		_docket_refresh_package_container_options(frm);
		_docket_refresh_container_cargo_debounced(frm);
		if (!_docket_is_grid_dialog_open()) {
			_docket_refresh_packing_summary_debounced(frm);
		}
	},
	container_no(frm) {
		_docket_refresh_package_container_options(frm);
	},
	type(frm) {
		_docket_refresh_container_cargo_debounced(frm);
		if (!_docket_is_grid_dialog_open()) {
			_docket_refresh_packing_summary_debounced(frm);
		}
	},
});

/**
 * Add WIP & Accrual recognition buttons to Docket
 * (Post: WIP and Accrual; Recognition: Adjust WIP / Adjust Accruals / Close).
 * Mirrors `_air_shipment_add_recognition_buttons` / `_sea_shipment_add_recognition_buttons`
 * so the toolbar behaves the same on every main-service job type.
 */
function _docket_add_recognition_buttons(frm) {
	var d = frm.doc;
	var needs_wip =
		typeof logistics !== "undefined" &&
		logistics.recognition &&
		logistics.recognition.needs_wip_recognition
			? logistics.recognition.needs_wip_recognition(d)
			: (function () {
					var rows = d.charges || [];
					for (var iw = 0; iw < rows.length; iw++) {
						var rw = rows[iw];
						if ((rw.charge_type || "").toLowerCase() === "disbursement") continue;
						var erw =
							flt(rw.estimated_revenue) ||
							flt(rw.base_amount) ||
							flt(rw.actual_revenue) ||
							flt(rw.amount) ||
							flt(rw.total) ||
							0;
						if (erw > 0 && !rw.wip_recognition_journal_entry) return true;
					}
					return flt(d.estimated_revenue) > flt(d.wip_amount);
			  })();
	var needs_accrual =
		typeof logistics !== "undefined" &&
		logistics.recognition &&
		logistics.recognition.needs_accrual_recognition
			? logistics.recognition.needs_accrual_recognition(d)
			: (function () {
					var rowsa = d.charges || [];
					for (var ia = 0; ia < rowsa.length; ia++) {
						var ra = rowsa[ia];
						if ((ra.charge_type || "").toLowerCase() === "disbursement") continue;
						var ca =
							flt(ra.estimated_cost) ||
							flt(ra.cost_base_amount) ||
							flt(ra.actual_cost) ||
							flt(ra.cost) ||
							0;
						if (ca > 0 && !ra.accrual_recognition_journal_entry) return true;
					}
					return flt(d.estimated_costs) > flt(d.accrual_amount);
			  })();

	if (needs_wip || needs_accrual) {
		frm.add_custom_button(
			__("WIP and Accrual"),
			function () {
				frappe.call({
					method: "logistics.job_management.recognition_engine.recognize",
					args: { doctype: d.doctype, docname: d.name },
					freeze: true,
					freeze_message: __("Recognizing WIP and Accruals..."),
					callback: function (r) {
						if (r.message) {
							var msg = [];
							if (r.message.wip_journal_entry)
								msg.push(__("WIP: {0}", [r.message.wip_journal_entry]));
							if (r.message.accrual_journal_entry)
								msg.push(
									__("Accruals: {0}", [r.message.accrual_journal_entry])
								);
							if (msg.length) {
								frappe.show_alert({ message: msg.join(" | "), indicator: "green" });
							} else {
								var reason =
									r.message.message ||
									__("Nothing to recognize (already recognized or below minimum)");
								frappe.msgprint({
									title: __("Recognition"),
									message: reason,
									indicator: "blue",
								});
							}
							frm.reload_doc();
						}
					},
				});
			},
			__("Post")
		);
	}

	if (flt(d.wip_amount) > 0) {
		frm.add_custom_button(
			__("Adjust WIP"),
			function () {
				frappe.prompt(
					[
						{
							fieldname: "adjustment_amount",
							fieldtype: "Currency",
							label: __("Adjustment Amount"),
							description: __("Current WIP: {0}", [d.wip_amount]),
							reqd: 1,
						},
						{
							fieldname: "adjustment_date",
							fieldtype: "Date",
							label: __("Adjustment Date"),
							default: frappe.datetime.get_today(),
							reqd: 1,
						},
					],
					function (values) {
						frappe.call({
							method: "logistics.job_management.recognition_engine.adjust_wip",
							args: {
								doctype: d.doctype,
								docname: d.name,
								adjustment_amount: values.adjustment_amount,
								adjustment_date: values.adjustment_date,
							},
							freeze: true,
							freeze_message: __("Creating WIP Adjustment..."),
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({
										message: __("WIP Adjustment created: {0}", [r.message]),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					},
					__("Adjust WIP"),
					__("Create")
				);
			},
			__("Recognition")
		);
	}

	if (flt(d.accrual_amount) > 0) {
		frm.add_custom_button(
			__("Adjust Accruals"),
			function () {
				frappe.prompt(
					[
						{
							fieldname: "adjustment_amount",
							fieldtype: "Currency",
							label: __("Adjustment Amount"),
							description: __("Current Accrual: {0}", [d.accrual_amount]),
							reqd: 1,
						},
						{
							fieldname: "adjustment_date",
							fieldtype: "Date",
							label: __("Adjustment Date"),
							default: frappe.datetime.get_today(),
							reqd: 1,
						},
					],
					function (values) {
						frappe.call({
							method: "logistics.job_management.recognition_engine.adjust_accruals",
							args: {
								doctype: d.doctype,
								docname: d.name,
								adjustment_amount: values.adjustment_amount,
								adjustment_date: values.adjustment_date,
							},
							freeze: true,
							freeze_message: __("Creating Accrual Adjustment..."),
							callback: function (r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Accrual Adjustment created: {0}", [r.message]),
										indicator: "green",
									});
									frm.reload_doc();
								}
							},
						});
					},
					__("Adjust Accruals"),
					__("Create")
				);
			},
			__("Recognition")
		);
	}

	if (flt(d.wip_amount) > 0 || flt(d.accrual_amount) > 0) {
		frm.add_custom_button(
			__("Close Recognition"),
			function () {
				frappe.confirm(
					__("This will close all remaining WIP and Accruals. Continue?"),
					function () {
						frappe.prompt(
							[
								{
									fieldname: "closure_date",
									fieldtype: "Date",
									label: __("Closure Date"),
									default: frappe.datetime.get_today(),
									reqd: 1,
								},
							],
							function (values) {
								frappe.call({
									method:
										"logistics.job_management.recognition_engine.close_job_recognition",
									args: {
										doctype: d.doctype,
										docname: d.name,
										closure_date: values.closure_date,
									},
									freeze: true,
									freeze_message: __("Closing Recognition..."),
									callback: function (r) {
										if (r.message) {
											var msg = [];
											if (r.message.wip_journal_entry)
												msg.push(
													__("WIP closed: {0}", [r.message.wip_journal_entry])
												);
											if (r.message.accrual_journal_entry)
												msg.push(
													__("Accrual closed: {0}", [
														r.message.accrual_journal_entry,
													])
												);
											if (msg.length)
												frappe.show_alert({
													message: msg.join(" | "),
													indicator: "green",
												});
											frm.reload_doc();
										}
									},
								});
							},
							__("Close Recognition"),
							__("Close")
						);
					}
				);
			},
			__("Recognition")
		);
	}
}
