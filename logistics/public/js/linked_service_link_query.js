// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Linked Service link picker on charge rows: filter by parent booking and charge service_type.
 */
frappe.provide("logistics.linked_service_link_query");

(function () {
	"use strict";

	/** Canonical charge-line service_type (aligned with charge_service_type.py). */
	function canonicalChargeServiceType(st) {
		const raw = (st && String(st).trim()) || "";
		if (!raw) return "";
		const byTitle = {
			Air: "air",
			Sea: "sea",
			Transport: "transport",
			Custom: "custom",
			Customs: "custom",
			custom: "custom",
			customs: "custom",
			Warehousing: "warehousing",
			"Cross-Docking": "cross-docking",
			"Special Project": "special project",
			MICE: "exhibits",
			Exhibits: "exhibits",
			Events: "exhibits",
		};
		if (byTitle[raw] !== undefined) return byTitle[raw];
		const low = raw.toLowerCase();
		if (low === "customs") return "custom";
		if (low === "events" || low === "mice") return "exhibits";
		if (["air", "sea", "transport", "warehousing", "cross-docking", "special project", "exhibits"].includes(low)) {
			return low;
		}
		return low;
	}

	/** Linked Service Select value for a charge row service_type. */
	function linkedServiceLabelForChargeServiceType(st) {
		const c = canonicalChargeServiceType(st);
		if (!c) return "";
		const byCanonical = {
			air: "Air",
			sea: "Sea",
			transport: "Transport",
			custom: "Customs",
			warehousing: "Warehousing",
			"cross-docking": "Cross-Docking",
			"special project": "Special Project",
			exhibits: "MICE",
		};
		return byCanonical[c] || "";
	}

	function chargeRowLinkField(chargeRowDoctype) {
		return frappe.meta.get_docfield(chargeRowDoctype, "linked_service")
			? "linked_service"
			: "internal_job";
	}

	function isLinkedScope(row) {
		const scope = (row && row.charge_scope || "Main").trim();
		return scope === "Linked" || scope === "Internal Job";
	}

	function chargeRowLinkValue(row) {
		if (!row) return "";
		return row.linked_service !== undefined ? row.linked_service : row.internal_job;
	}

	function buildFilters(frm, parentBookingType, row) {
		const filters = {
			parent_booking_type: parentBookingType,
			parent_booking_name: frm.doc.name || "",
		};
		const label = linkedServiceLabelForChargeServiceType(row && row.service_type);
		if (label) {
			filters.service_type = label;
		}
		return filters;
	}

	logistics.linked_service_link_query.canonicalChargeServiceType = canonicalChargeServiceType;
	logistics.linked_service_link_query.linkedServiceLabelForChargeServiceType =
		linkedServiceLabelForChargeServiceType;

	logistics.linked_service_link_query.setup = function (frm, options) {
		options = options || {};
		const parentBookingType = options.parentBookingType;
		const chargeChildTable = options.chargeChildTable || "charges";
		const chargeRowDoctype = options.chargeRowDoctype;
		if (!parentBookingType || !chargeRowDoctype || !frm.fields_dict[chargeChildTable]) {
			return;
		}
		const linkField = chargeRowLinkField(chargeRowDoctype);
		frm.set_query(linkField, chargeChildTable, function (doc, cdt, cdn) {
			const row = locals[cdt] && locals[cdt][cdn];
			return { filters: buildFilters(frm, parentBookingType, row) };
		});
	};

	/** Clear linked_service when charge service_type no longer matches the linked document. */
	logistics.linked_service_link_query.clearLinkIfServiceTypeMismatch = function (frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!row || !isLinkedScope(row)) return;
		const linkField = row.linked_service !== undefined ? "linked_service" : "internal_job";
		const lsName = chargeRowLinkValue(row);
		if (!lsName) return;
		const expected = linkedServiceLabelForChargeServiceType(row.service_type);
		if (!expected) return;
		frappe.db.get_value("Linked Service", lsName, "service_type").then(function (r) {
			const lsType = (r && r.message && r.message.service_type) || "";
			const lsLabel = linkedServiceLabelForChargeServiceType(lsType);
			if (lsLabel && lsLabel !== expected) {
				frappe.model.set_value(cdt, cdn, linkField, "");
			}
		});
	};
})();
