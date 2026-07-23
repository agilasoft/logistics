// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_exhibit_job(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
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

frappe.ui.form.on("MICE Job", {
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
		logistics_set_site_query_exhibit_job(frm);
		if (logistics.party_address_contact) {
			logistics.party_address_contact.populate_displays_if_missing(frm);
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

		if (window.logistics_load_documents_html) {
			window.logistics_load_documents_html(frm, "MICE Job");
		}
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.documents_html")
				.on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
					if (window.logistics_load_documents_html) {
						window.logistics_load_documents_html(frm, "MICE Job");
					}
				});
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
});
