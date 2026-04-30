// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/** Child grid row for Shipping Line CTO (port / sea_cto in same row). */
function shipping_line_cto_row(cdt, cdn) {
	if (locals[cdt] && locals[cdt][cdn]) {
		return locals[cdt][cdn];
	}
	// Unsaved or timing edge: try Frappe’s child doc helper
	if (cdt && cdn) {
		try {
			if (frappe.get_doc) {
				const d = frappe.get_doc(cdt, cdn);
				if (d) {
					return d;
				}
			}
		} catch (e) {
			// ignore
		}
	}
	return null;
}

frappe.ui.form.on("Shipping Line", {
	setup(frm) {
		frm.set_query("sea_cto", "ctos", (doc, cdt, cdn) => {
			const row = shipping_line_cto_row(cdt, cdn);
			const unloco = (row && row.port ? String(row.port).trim() : "") || "";
			if (!unloco) {
				return { filters: { name: ["in", []] } };
			}
			return {
				query:
					"logistics.sea_freight.doctype.cargo_terminal_operator.cargo_terminal_operator.cargo_terminal_operator_by_unloco_search",
				filters: { unloco: unloco },
			};
		});
	},
});

frappe.ui.form.on("Shipping Line CTO", {
	port(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "sea_cto", "");
	},
});
