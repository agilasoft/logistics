// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Bill To on charge rows: default to parent Customer and limit choices to
 * shipper/consignee/freight-agent related customers.
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

	const PARTY_REFRESH_FIELDS = [
		"local_customer",
		"customer",
		"shipper",
		"consignee",
		"exporter_shipper",
		"importer_consignee",
		"freight_agent",
		"freight_agent_sea",
		"job_type",
		"job",
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

	function billToFilters(frm) {
		const eligible = frm._eligible_bill_to_customers;
		if (!eligible || !eligible.length) {
			return { filters: { name: "__none__" } };
		}
		// Do not filter on Customer.disabled here — link_filters and doctype-prefixed
		// filters trigger a permlevel-0 permission check (Customer.0). Eligible customers
		// are already limited to enabled customers on the server.
		return {
			filters: [["name", "in", eligible]],
		};
	}

	function refreshEligibleBillToCustomers(frm, callback) {
		frappe.call({
			method: "logistics.utils.charge_bill_to.get_eligible_bill_to_customers_for_doc",
			args: {
				doctype: frm.doctype,
				docname: frm.doc.name,
				doc_data: frm.doc,
			},
			callback(r) {
				frm._eligible_bill_to_customers = (r && r.message) || [];
				if (callback) {
					callback();
				}
			},
		});
	}

	function clearInvalidBillToOnCharges(frm) {
		const cdt = chargeChildDoctype(frm);
		if (!cdt || !chargeRowHasBillTo(frm)) {
			return;
		}
		const eligible = new Set(frm._eligible_bill_to_customers || []);
		(frm.doc.charges || []).forEach((row) => {
			if (!row.bill_to || eligible.has(row.bill_to)) {
				return;
			}
			frappe.model.set_value(row.doctype, row.name, "bill_to", "");
		});
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
		const eligible = frm._eligible_bill_to_customers || [];
		if (eligible.length && !eligible.includes(defaultCustomer)) {
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
		frm.set_query("bill_to", "charges", function () {
			return billToFilters(frm);
		});
		refreshEligibleBillToCustomers(frm);
	};

	logistics.charge_bill_to.on_party_field_change = function (frm) {
		if (!chargeRowHasBillTo(frm)) {
			return;
		}
		refreshEligibleBillToCustomers(frm, function () {
			clearInvalidBillToOnCharges(frm);
		});
	};

	CHARGE_PARENT_DOCTYPES.forEach(function (doctype) {
		const events = {
			refresh(frm) {
				logistics.charge_bill_to.setup(frm);
			},
			charges_add(frm, cdt, cdn) {
				if (!frm._eligible_bill_to_customers) {
					refreshEligibleBillToCustomers(frm, function () {
						defaultBillToOnChargeAdd(frm, cdt, cdn);
					});
					return;
				}
				defaultBillToOnChargeAdd(frm, cdt, cdn);
			},
		};

		PARTY_REFRESH_FIELDS.forEach(function (fieldname) {
			if (events[fieldname]) {
				return;
			}
			events[fieldname] = function (frm) {
				logistics.charge_bill_to.on_party_field_change(frm);
			};
		});

		frappe.ui.form.on(doctype, events);
	});
})();
