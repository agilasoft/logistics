// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _master_bill_set_query_shipping_line_cto(frm) {
	frm.set_query("origin_cto", function () {
		if (!frm.doc.shipping_line || !frm.doc.origin_port) {
			return { filters: { name: ["in", []] } };
		}
		return {
			query:
				"logistics.sea_freight.doctype.shipping_line.shipping_line.shipping_line_cto_by_line_and_port_search",
			filters: { shipping_line: frm.doc.shipping_line, port: frm.doc.origin_port },
		};
	});
	frm.set_query("destination_cto", function () {
		if (!frm.doc.shipping_line || !frm.doc.destination_port) {
			return { filters: { name: ["in", []] } };
		}
		return {
			query:
				"logistics.sea_freight.doctype.shipping_line.shipping_line.shipping_line_cto_by_line_and_port_search",
			filters: { shipping_line: frm.doc.shipping_line, port: frm.doc.destination_port },
		};
	});
}

frappe.ui.form.on("Master Bill", {
	setup(frm) {
		_master_bill_set_query_shipping_line_cto(frm);
	},

	shipping_line(frm) {
		frm.set_value("origin_cto", "");
		frm.set_value("destination_cto", "");
	},

	origin_port(frm) {
		frm.set_value("origin_cto", "");
	},

	destination_port(frm) {
		frm.set_value("destination_cto", "");
	},

	refresh(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Refresh Voyage Status"), function () {
				frappe.call({
					method: "logistics.sea_freight.doctype.master_bill.master_bill.refresh_voyage_status",
					args: { master_bill_name: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
							frappe.show_alert({ message: __("Voyage status refreshed"), indicator: "green" });
						} else if (r.message && r.message.error) {
							frappe.msgprint(r.message.error);
						}
					}
				});
			}, __("Action"));
		}
	}
});
