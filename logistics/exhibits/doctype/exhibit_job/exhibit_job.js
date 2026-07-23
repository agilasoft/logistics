// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

function logistics_set_site_query_exhibit_job(frm) {
	frm.set_query("site", function () {
		return logistics.address.query_for_customer(frm.doc.customer);
	});
}

frappe.ui.form.on("Exhibit Job", {
	setup(frm) {
		if (logistics.party_address_contact) {
			logistics.party_address_contact.setup_queries(frm);
		}
	},

	refresh(frm) {
		logistics_set_site_query_exhibit_job(frm);
		if (logistics.party_address_contact) {
			logistics.party_address_contact.populate_displays_if_missing(frm);
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
});
