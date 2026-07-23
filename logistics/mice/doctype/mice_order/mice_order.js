// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_exhibit_order(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
}

function _logistics_mice_order_add_create_or_open_job(frm) {
	// Mirror Transport Order → Transport Job / Project Order → Project Job.
	if (frm.doc.__islocal || frm.is_new() || !frm.doc.name || String(frm.doc.name).startsWith("new-")) {
		return;
	}

	frappe.db.get_value("MICE Job", { exhibit_order: frm.doc.name }, "name", function (r) {
		if (r && r.name) {
			frm.add_custom_button(__("MICE Job"), function () {
				frappe.set_route("Form", "MICE Job", r.name);
			}, __("Action"));
			frm.dashboard.add_indicator(__("MICE Job: {0}", [r.name]), "blue");
			return;
		}

		frm.add_custom_button(__("Job"), function () {
			const fields = [
				{
					fieldname: "title",
					fieldtype: "Data",
					label: __("Job title"),
					reqd: 1,
					default: frm.doc.name + " — " + __("Task"),
				},
			];
			frappe.prompt(
				fields,
				function (values) {
					frappe.call({
						method: "logistics.mice.doctype.mice_order.mice_order.action_create_mice_job",
						args: {
							docname: frm.doc.name,
							title: values.title,
						},
						freeze: true,
						freeze_message: __("Creating MICE Job..."),
						callback: function (response) {
							if (!response || !response.message) {
								return;
							}
							const payload = response.message;
							if (payload.already_exists) {
								frappe.msgprint({
									title: __("MICE Job Already Exists"),
									message: __("MICE Job {0} already exists for this MICE Order.", [payload.name]),
									indicator: "blue",
								});
								frappe.set_route("Form", "MICE Job", payload.name);
								frm.reload_doc();
							} else if (payload.created) {
								frappe.msgprint({
									title: __("MICE Job Created"),
									message: __("MICE Job {0} created successfully.", [payload.name]),
									indicator: "green",
								});
								frappe.set_route("Form", "MICE Job", payload.name);
								frm.reload_doc();
							}
						},
					});
				},
				__("Create MICE Job"),
				__("Create")
			);
		}, __("Create"));
	});
}

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: "logistics.document_management.api.get_milestone_html",
		args: { doctype: frm.doctype, docname: frm.doc.name },
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

frappe.ui.form.on("MICE Order", {
	setup(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.setup_queries(frm);
		}
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
		logistics_set_site_query_exhibit_order(frm);
		if (logistics.party_address_contact) {
			logistics.party_address_contact.populate_displays_if_missing(frm);
		}
		_logistics_mice_order_add_create_or_open_job(frm);

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

		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, "MICE Order");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.documents_html")
				.on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
					if (window.logistics_load_documents_html) {
						window.logistics_load_documents_html(frm, "MICE Order");
					}
				});
		}
	},

	shipper(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_shipper_change(frm);
		}
	},

	consignee(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_consignee_change(frm);
		}
	},

	shipper_address(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_shipper_address_change(frm);
		}
	},

	consignee_address(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_consignee_address_change(frm);
		}
	},

	shipper_contact(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_shipper_contact_change(frm);
		}
	},

	consignee_contact(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.on_consignee_contact_change(frm);
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
