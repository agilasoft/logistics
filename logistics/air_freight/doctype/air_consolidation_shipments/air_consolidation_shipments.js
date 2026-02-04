// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, see license.txt

frappe.ui.form.on("Air Consolidation Shipments", {
	form_load: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (!row || (row.weight_uom && row.volume_uom)) return;
		frappe.call({
			method: "logistics.utils.default_uom.get_default_uoms_for_domain_api",
			args: { domain: "air" },
			callback: function (r) {
				if (r.message) {
					if (!row.weight_uom && r.message.weight_uom) {
						frappe.model.set_value(cdt, cdn, "weight_uom", r.message.weight_uom);
					}
					if (!row.volume_uom && r.message.volume_uom) {
						frappe.model.set_value(cdt, cdn, "volume_uom", r.message.volume_uom);
					}
				}
			},
		});
	},
});
