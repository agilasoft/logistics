frappe.ui.form.on("Storage Facility", {
	setup(frm) {
		frm.set_query("storagefacility_primary_contact", function (doc) {
			if (doc.__islocal || !doc.name) return { filters: { name: "__none__" } };
			let contact_names = [];
			frappe.call({
				method: "logistics.contact_links.get_contact_names_for_dynamic_link",
				args: { link_doctype: "Storage Facility", link_name: doc.name },
				async: false,
				callback: function (r) {
					contact_names = r.message || [];
				},
			});
			return contact_names.length
				? { filters: { name: ["in", contact_names] } }
				: { filters: { name: "__none__" } };
		});

		frm.set_query("storagefacility_primary_address", function (doc) {
			if (doc.__islocal || !doc.name) return { filters: { name: "__none__" } };
			return logistics.address.query_for_link("Storage Facility", doc.name);
		});
	},

	storagefacility_primary_address(frm) {
		if (frm.doc.storagefacility_primary_address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: {
					address_dict: frm.doc.storagefacility_primary_address,
				},
				callback: function (r) {
					frm.set_value("primary_address", r.message || "");
				},
			});
		} else {
			frm.set_value("primary_address", "");
		}
	},

	refresh(frm) {
		if (!frm.doc.__islocal) {
			frappe.dynamic_link = {
				doc: frm.doc,
				fieldname: "name",
				doctype: frm.doctype,
			};
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
	},
});
