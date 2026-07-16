// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

function _schedule_customs_line_charge_recalc_from_grid(frm) {
	if (
		window.logistics &&
		logistics.schedule_customs_line_charge_recalc &&
		frm &&
		(frm.doctype === "Declaration" || frm.doctype === "Declaration Order")
	) {
		logistics.schedule_customs_line_charge_recalc(frm);
	}
}

function _schedule_commercial_invoice_totals_recalc_from_grid(frm) {
	if (
		window.logistics &&
		logistics.schedule_commercial_invoice_totals_recalc &&
		frm &&
		(frm.doctype === "Declaration" || frm.doctype === "Declaration Order")
	) {
		logistics.schedule_commercial_invoice_totals_recalc(frm);
	}
}

frappe.ui.form.on("Commercial Invoice Line Item", {
	invoice_qty(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
		_schedule_customs_line_charge_recalc_from_grid(frm);
	},
	customs_qty(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
	price(frm) {
		_schedule_commercial_invoice_totals_recalc_from_grid(frm);
	},
	chargeable_weight(frm) {
		_schedule_customs_line_charge_recalc_from_grid(frm);
	},
	chargeable_weight_uom(frm) {
		_schedule_customs_line_charge_recalc_from_grid(frm);
	},
	gross_weight(frm) {
		_schedule_customs_line_charge_recalc_from_grid(frm);
	},
	gross_weight_uom(frm) {
		_schedule_customs_line_charge_recalc_from_grid(frm);
	},
	declaration_product_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.declaration_product_code) {
			// Clear fetched fields when Declaration Product Code is cleared
			frappe.model.set_value(cdt, cdn, {
				item: "",
				product_code: "",
				procedure_code: "",
				tariff: "",
				goods_description: "",
				commodity_code: "",
				goods_origin: "",
				preference: ""
			});
			return;
		}
		frappe.call({
			method: "logistics.customs.doctype.declaration_product_code.declaration_product_code.get_declaration_product_code_details",
			args: { name: row.declaration_product_code },
			callback: function(r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, r.message);
				}
			}
		});
	}
});
