// Copyright (c) 2026, logistics.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Pre-fill branch, cost center, and profit center from Sea Freight Settings on new/unsaved
 * Sea Booking / Sea Shipment forms (mirrors server logic in sea_freight_settings_defaults.py).
 */
window.logistics_apply_sea_freight_settings_accounting_defaults = function (frm) {
	if (!frm || (!frm.is_new() && !frm.doc.__islocal)) return;
	if (frm._applying_sea_freight_accounting_defaults) return;

	var company = frm.doc.company || frappe.defaults.get_user_default("Company");
	if (!company) return;

	frappe.call({
		method: "frappe.client.get",
		args: { doctype: "Sea Freight Settings", name: company },
		callback: function (r) {
			if (!r.message) return;
			var s = r.message;

			var updates = [];
			if (!frm.doc.branch && s.default_branch) {
				updates.push(["branch", s.default_branch]);
			}
			if (!frm.doc.cost_center && s.default_cost_center) {
				updates.push(["cost_center", s.default_cost_center]);
			}
			if (!frm.doc.profit_center && s.default_profit_center) {
				updates.push(["profit_center", s.default_profit_center]);
			}
			if (!updates.length) return;

			frm._applying_sea_freight_accounting_defaults = true;
			var p = Promise.resolve();
			updates.forEach(function (pair) {
				p = p.then(function () {
					return frm.set_value(pair[0], pair[1]);
				});
			});
			p.then(function () {
				frm._applying_sea_freight_accounting_defaults = false;
			}).catch(function () {
				frm._applying_sea_freight_accounting_defaults = false;
			});
		},
	});
};
