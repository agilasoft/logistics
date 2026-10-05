// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Bill To on charge rows defaults to the parent Customer.
 * The link is not filtered by the header customer or related parties.
 */
frappe.provide("logistics.charge_bill_to");

(function () {
	"use strict";

	const CHARGE_PARENT_DOCTYPES = [
		"Sea Booking",
		"Sea Shipment",
		"Air Booking",
		"Air Shipment",
		"Transport Order",
		"Transport Job",
		"Declaration",
		"Declaration Order",
		"Sales Quote",
		"Change Request",
		"Special Project",
	];

	function chargeChildDoctype(frm) {
		const df = frm.get_docfield("charges");
		return (df && df.options) || null;
	}

	function chargeRowHasBillTo(frm) {
		const cdt = chargeChildDoctype(frm);
		return !!(cdt && frappe.meta.get_docfield(cdt, "bill_to"));
	}

	logistics.charge_bill_to.getDefaultBillTo = function (frm) {
		return frm.doc.local_customer || frm.doc.customer || null;
	};

	function stripBillToLinkFilters(cdt) {
		const df = frappe.meta.get_docfield(cdt, "bill_to");
		if (df && df.link_filters) {
			df.link_filters = null;
		}
	}

	function defaultBillToOnChargeAdd(frm, cdt, cdn) {
		const row = locals[cdt] && locals[cdt][cdn];
		if (!row || row.bill_to || row.charge_type === "Cost") {
			return;
		}
		const defaultCustomer = logistics.charge_bill_to.getDefaultBillTo(frm);
		if (!defaultCustomer) {
			return;
		}
		frappe.model.set_value(cdt, cdn, "bill_to", defaultCustomer);
	}

	logistics.charge_bill_to.setup = function (frm) {
		if (!frm.fields_dict.charges || !chargeRowHasBillTo(frm)) {
			return;
		}
		const cdt = chargeChildDoctype(frm);
		if (cdt) {
			stripBillToLinkFilters(cdt);
		}
	};

	CHARGE_PARENT_DOCTYPES.forEach(function (doctype) {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				logistics.charge_bill_to.setup(frm);
			},
			charges_add(frm, cdt, cdn) {
				defaultBillToOnChargeAdd(frm, cdt, cdn);
			},
		});
	});
})();
