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
		if (frm.doc.__islocal) return;

		frm.add_custom_button(__("Refresh Voyage Status"), function () {
			frappe.call({
				method: "logistics.sea_freight.doctype.master_bill.master_bill.refresh_voyage_status",
				args: { master_bill_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Refreshing voyage status..."),
				callback: function (r) {
					const m = (r && r.message) || {};
					if (m.success) {
						frm.reload_doc();
						frappe.show_alert({
							message: __("Voyage status refreshed from {0}", [m.provider || __("provider")]),
							indicator: "green",
						});
						return;
					}
					if (m.app_installed === false) {
						frappe.msgprint({
							title: __("GoConnect required"),
							message: m.message || __("Install GoConnect to enable live vessel tracking."),
							indicator: "orange",
						});
						return;
					}
					if (m.licensed === false) {
						frappe.msgprint({
							title: __("Subscription required"),
							message: m.message || __("Your GoConnect license does not cover the vessel voyage tracker."),
							indicator: "orange",
						});
						return;
					}
					frappe.msgprint(m.message || m.error || __("Unable to refresh voyage status."));
				},
			});
		}, __("Action"));

		if (!frm.doc.vessel_schedule) {
			frm.add_custom_button(__("Auto-link Vessel Schedule"), function () {
				frappe.call({
					method: "logistics.sea_freight.doctype.master_bill.master_bill.fetch_and_link_vessel_schedule",
					args: { master_bill_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Looking up Vessel Schedule..."),
					callback: function (r) {
						const m = (r && r.message) || {};
						if (m.success) {
							frm.reload_doc();
							frappe.show_alert({
								message: __("Linked Vessel Schedule {0}", [m.vessel_schedule]),
								indicator: "green",
							});
						} else if (m.app_installed === false) {
							frappe.msgprint({
								title: __("GoConnect required"),
								message: m.message,
								indicator: "orange",
							});
						} else if (m.message) {
							frappe.msgprint(m.message);
						}
					},
				});
			}, __("Action"));
		}
	}
});
