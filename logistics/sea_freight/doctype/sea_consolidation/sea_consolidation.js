// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: "Sea Consolidation", docname: frm.doc.name },
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

function _load_documents_html(frm) {
	if (!frm.fields_dict.documents_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._documents_html_called) return;
	frm._documents_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_document_alerts_html",
		args: { doctype: "Sea Consolidation", docname: frm.doc.name },
		callback: function (r) {
			if (r.message && frm.fields_dict.documents_html) {
				frm.fields_dict.documents_html.$wrapper.html(r.message);
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

frappe.ui.form.on("Sea Consolidation Packages", {
	contains_dangerous_goods: function (frm) {
		frm.refresh_field("consolidation_packages");
	},
	temperature_controlled: function (frm) {
		frm.refresh_field("consolidation_packages");
	},
});

frappe.ui.form.on("Sea Consolidation", {
	validate: async function (frm) {
		const rows = frm.doc.consolidation_containers || [];
		for (let i = 0; i < rows.length; i++) {
			const raw = rows[i].container_number;
			if (raw === undefined || raw === null || String(raw).trim() === "") {
				continue;
			}
			try {
				const r = await frappe.call({
					method: "logistics.logistics.doctype.container.container.validate_container_number_for_form",
					args: { container_number: String(raw) },
				});
				const d = r.message || {};
				if (!d.valid) {
					frappe.validated = false;
					frappe.msgprint({
						title: __("Invalid Container Number"),
						message: __("Consolidation container row {0}: {1}", [
							i + 1,
							d.message || __("Invalid container number"),
						]),
						indicator: "red",
					});
					return;
				}
			} catch (e) {
				// Server-side Sea Consolidation / child row validate still runs on save.
			}
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
	setup: function (frm) {

		frm.set_query('milestone_template', function() {
			return frappe.call('logistics.document_management.api.get_milestone_template_filters', { doctype: frm.doctype })
				.then(function(r) { return r.message || { filters: [] }; });
		});
	},
	refresh: function (frm) {
		// Dashboard tab
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frm.call("get_dashboard_html").then(function (r) {
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
				setTimeout(function () {
					frm._dashboard_html_called = false;
				}, 2000);
			}
		}
		_load_documents_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				_load_documents_html(frm);
			});
		}
		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.milestone_html").on("click.milestone_html", '[data-fieldname="milestones_tab"]', function () {
				_load_milestone_html(frm);
			});
		}
		(function lock_planned_shipments_grid() {
			const planningLocked =
				(frm.doc.sea_planning_status || "Draft") === "Submitted" && frm.doc.docstatus === 0;
			if (!frm.fields_dict.consolidation_planning_lines) {
				return;
			}
			frm.set_df_property("consolidation_planning_lines", "read_only", planningLocked ? 1 : 0);
			frm.set_df_property(
				"consolidation_planning_lines",
				"cannot_add_rows",
				planningLocked ? 1 : 0
			);
			frm.set_df_property(
				"consolidation_planning_lines",
				"cannot_delete_rows",
				planningLocked ? 1 : 0
			);
			frm.refresh_field("consolidation_planning_lines");
		})();
		if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
			if ((frm.doc.sea_planning_status || "Draft") === "Draft") {
				frm.add_custom_button(__("Aligned Sea Shipments…"), function () {
					if (window.logistics && logistics.open_sea_consolidation_matching_shipments_dialog) {
						logistics.open_sea_consolidation_matching_shipments_dialog(frm);
					} else {
						frappe.msgprint(__("Sea consolidation UI is still loading — try again in a moment."));
					}
				}, __("Action"));
			}
			if (
				(frm.doc.sea_planning_status || "Draft") === "Draft" &&
				(frm.doc.consolidation_planning_lines || []).length
			) {
				frm.add_custom_button(
					__("Submit planned shipments"),
					function () {
						frappe.confirm(
							__("Submit planned shipment list? It will lock until reset."),
							function () {
								frm.call("submit_sea_planning").then(function () {
									frappe.show_alert({ message: __("Planning submitted"), indicator: "green" }, 3);
									frm.reload_doc();
								});
							}
						);
					},
					__("Action")
				);
			}
			if (frm.doc.sea_planning_status === "Submitted") {
				frm.add_custom_button(
					__("Reset planned shipments to draft"),
					function () {
						frappe.confirm(
							__(
								"This is only allowed after removing cargo that references sea shipments. Planning will return to draft: planned shipments stay listed, the table becomes editable again, and you can add more from Aligned Sea Shipments. Continue?"
							),
							function () {
								frm.call("cancel_sea_planning_submit").then(function () {
									frappe.show_alert({ message: __("Planning set to draft"), indicator: "blue" }, 3);
									frm.reload_doc();
								});
							}
						);
					},
					__("Action")
				);
			}
		}
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Get Milestones"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_milestones_from_template",
					args: { doctype: "Sea Consolidation", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Action"));
			frm.add_custom_button(__("Get Documents"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Sea Consolidation", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Action"));
		}
		if (frm.doc.consolidation_charges && frm.doc.consolidation_charges.length > 0) {
			frm.add_custom_button(__("Calculate Charges"), function () {
				frappe.call({
					method: "logistics.sea_freight.doctype.sea_consolidation.sea_consolidation.recalculate_all_charges",
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
		if (frm.doc.origin_port && frm.doc.destination_port) {
			frm.add_custom_button(__("Populate from Ports"), function () {
				frappe.call({
					method: "logistics.sea_freight.doctype.sea_consolidation.sea_consolidation.populate_routing_from_ports",
					args: { docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.message) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "green" }, 3);
						}
					},
				});
			}, __("Action"));
		}
		setTimeout(function () {
			if (frm.doc.name && !frm.doc.__islocal && typeof show_create_consolidation_purchase_invoice_dialog === "function") {
				frm.add_custom_button(__("Purchase Invoice"), function () {
					show_create_consolidation_purchase_invoice_dialog(frm);
				}, __("Create"));
			}
		}, 0);
	},
});

