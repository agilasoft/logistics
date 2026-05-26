// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

function logistics_docket_set_exhibitor_query(frm) {
	frm.set_query("exhibitor", function () {
		const exhibit = frm.doc.exhibit;
		if (!exhibit) return { filters: [["Customer", "name", "=", ""]] };
		return {
			query: "logistics.exhibits.doctype.docket.docket.get_exhibitor_options_query",
			filters: { exhibit: exhibit },
		};
	});
}

function logistics_docket_set_site_query(frm) {
	frm.set_query("site", function () {
		const cust = frm.doc.customer || frm.doc.exhibitor;
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

frappe.ui.form.on("Docket", {
	onload(frm) {
		logistics_docket_set_exhibitor_query(frm);
		logistics_docket_set_site_query(frm);
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
	},
	refresh(frm) {
		logistics_docket_set_exhibitor_query(frm);
		logistics_docket_set_site_query(frm);
		_load_docket_milestone_html(frm);

		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, frm.doctype);
		}

		if (!frm.doc.__islocal && frm.doc.exhibit) {
			frm.add_custom_button(
				__("Open Exhibit"),
				function () {
					frappe.set_route("Form", "Exhibit", frm.doc.exhibit);
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
							"logistics.exhibits.doctype.docket.docket.recalculate_all_charges",
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
});
