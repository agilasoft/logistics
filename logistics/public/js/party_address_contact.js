// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.provide("logistics.party_address_contact");

(function () {
	function contact_display_text(contact) {
		if (!contact) {
			return "";
		}
		let txt = [contact.first_name, contact.last_name].filter(Boolean).join(" ") || contact.name || "";
		if (contact.designation) {
			txt += "\n" + contact.designation;
		}
		if (contact.phone) {
			txt += "\n" + contact.phone;
		}
		if (contact.mobile_no) {
			txt += "\n" + contact.mobile_no;
		}
		if (contact.email_id) {
			txt += "\n" + contact.email_id;
		}
		return txt;
	}

	function clear_shipper_party_fields(frm) {
		frm.set_value("shipper_address", "");
		frm.set_value("shipper_address_display", "");
		frm.set_value("shipper_contact", "");
		frm.set_value("shipper_contact_display", "");
	}

	function clear_consignee_party_fields(frm) {
		frm.set_value("consignee_address", "");
		frm.set_value("consignee_address_display", "");
		frm.set_value("consignee_contact", "");
		frm.set_value("consignee_contact_display", "");
	}

	logistics.party_address_contact = {
		setup_queries: function (frm) {
			if (!frm || !frm.fields_dict) {
				return;
			}
			if (frm.fields_dict.shipper_address) {
				frm.set_query("shipper_address", function () {
					return logistics.address.query_for_link("Shipper", frm.doc.shipper);
				});
			}
			if (frm.fields_dict.shipper_contact) {
				frm.set_query("shipper_contact", function () {
					if (frm.doc.shipper) {
						return {
							filters: [
								["Dynamic Link", "link_doctype", "=", "Shipper"],
								["Dynamic Link", "link_name", "=", frm.doc.shipper],
							],
						};
					}
					return {};
				});
			}
			if (frm.fields_dict.consignee_address) {
				frm.set_query("consignee_address", function () {
					return logistics.address.query_for_link("Consignee", frm.doc.consignee);
				});
			}
			if (frm.fields_dict.consignee_contact) {
				frm.set_query("consignee_contact", function () {
					if (frm.doc.consignee) {
						return {
							filters: [
								["Dynamic Link", "link_doctype", "=", "Consignee"],
								["Dynamic Link", "link_name", "=", frm.doc.consignee],
							],
						};
					}
					return {};
				});
			}
		},

		on_shipper_change: function (frm, options) {
			options = options || {};
			if (!frm.doc.shipper) {
				clear_shipper_party_fields(frm);
				return;
			}
			frappe.db.get_value(
				"Shipper",
				frm.doc.shipper,
				["pick_address", "shipper_primary_address", "shipper_primary_contact"],
				function (r) {
					if (r && (r.pick_address || r.shipper_primary_address)) {
						frm.set_value("shipper_address", r.pick_address || r.shipper_primary_address);
						frm.trigger("shipper_address");
					}
					if (r && r.shipper_primary_contact) {
						frm.set_value("shipper_contact", r.shipper_primary_contact);
						frm.trigger("shipper_contact");
					}
					if (options.apply_party_defaults !== false && logistics.party_defaults) {
						logistics.party_defaults.apply(frm);
					}
				}
			);
		},

		on_consignee_change: function (frm, options) {
			options = options || {};
			if (!frm.doc.consignee) {
				clear_consignee_party_fields(frm);
				return;
			}
			frappe.db.get_value(
				"Consignee",
				frm.doc.consignee,
				["delivery_address", "consignee_primary_address", "consignee_primary_contact"],
				function (r) {
					if (r && (r.delivery_address || r.consignee_primary_address)) {
						frm.set_value("consignee_address", r.delivery_address || r.consignee_primary_address);
						frm.trigger("consignee_address");
					}
					if (r && r.consignee_primary_contact) {
						frm.set_value("consignee_contact", r.consignee_primary_contact);
						frm.trigger("consignee_contact");
					}
					if (options.apply_party_defaults !== false && logistics.party_defaults) {
						logistics.party_defaults.apply(frm);
					}
				}
			);
		},

		on_shipper_address_change: function (frm) {
			if (frm.doc.shipper_address) {
				frappe.call({
					method: "frappe.contacts.doctype.address.address.get_address_display",
					args: { address_dict: frm.doc.shipper_address },
					callback: function (r) {
						frm.set_value("shipper_address_display", r.message || "");
					},
				});
			} else {
				frm.set_value("shipper_address_display", "");
			}
		},

		on_consignee_address_change: function (frm) {
			if (frm.doc.consignee_address) {
				frappe.call({
					method: "frappe.contacts.doctype.address.address.get_address_display",
					args: { address_dict: frm.doc.consignee_address },
					callback: function (r) {
						frm.set_value("consignee_address_display", r.message || "");
					},
				});
			} else {
				frm.set_value("consignee_address_display", "");
			}
		},

		on_shipper_contact_change: function (frm) {
			if (frm.doc.shipper_contact) {
				frappe.call({
					method: "frappe.client.get",
					args: { doctype: "Contact", name: frm.doc.shipper_contact },
					callback: function (r) {
						frm.set_value("shipper_contact_display", contact_display_text(r.message));
					},
				});
			} else {
				frm.set_value("shipper_contact_display", "");
			}
		},

		on_consignee_contact_change: function (frm) {
			if (frm.doc.consignee_contact) {
				frappe.call({
					method: "frappe.client.get",
					args: { doctype: "Contact", name: frm.doc.consignee_contact },
					callback: function (r) {
						frm.set_value("consignee_contact_display", contact_display_text(r.message));
					},
				});
			} else {
				frm.set_value("consignee_contact_display", "");
			}
		},

		populate_displays_if_missing: function (frm) {
			if (frm.doc.shipper_address && !frm.doc.shipper_address_display) {
				frm.trigger("shipper_address");
			}
			if (frm.doc.consignee_address && !frm.doc.consignee_address_display) {
				frm.trigger("consignee_address");
			}
			if (frm.doc.shipper_contact && !frm.doc.shipper_contact_display) {
				frm.trigger("shipper_contact");
			}
			if (frm.doc.consignee_contact && !frm.doc.consignee_contact_display) {
				frm.trigger("consignee_contact");
			}
		},
	};
})();
