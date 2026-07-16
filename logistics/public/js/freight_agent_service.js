// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Filter Freight Agent link fields by applicable service types (Air, Sea, Transport, Customs, Warehousing).
 */
frappe.provide("logistics.freight_agent_service");

(function () {
	"use strict";

	const FIELD_SERVICE_MAP = {
		freight_agent_sea: "Sea",
		air_default_sending_agent: "Air",
		air_default_receiving_agent: "Air",
		air_default_broker: "Air",
		sea_default_sending_agent: "Sea",
		sea_default_receiving_agent: "Sea",
		customs_default_freight_agent: "Customs",
	};

	const SETTINGS_DOCTYPE_SERVICE = {
		"Air Freight Settings": "Air",
		"Sea Freight Settings": "Sea",
	};

	const DOCTYPE_IMPLIED_SERVICE = {
		"Air Booking": "Air",
		"Air Shipment": "Air",
		"Sea Booking": "Sea",
		"Sea Shipment": "Sea",
		"Transport Order": "Transport",
		"Transport Job": "Transport",
		Declaration: "Customs",
		"Declaration Order": "Customs",
		"Warehouse Job": "Warehousing",
		"VAS Order": "Warehousing",
		"Inbound Order": "Warehousing",
	};

	/** Services with no Freight Agent module checkbox (must not become filter fieldnames). */
	const MODULE_FLAGS_WITHOUT_SERVICE = new Set(["special project", "exhibits", "mice", "events"]);

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
			"Special Project": "special project",
			MICE: "exhibits",
			Exhibits: "exhibits",
			Events: "exhibits",
		};
		if (byTitle[raw] !== undefined) return byTitle[raw];
		const low = raw.toLowerCase();
		if (low === "customs") return "custom";
		if (low === "events" || low === "mice") return "exhibits";
		if (["air", "sea", "transport", "warehousing", "special project", "exhibits"].includes(low)) {
			return low;
		}
		return low;
	}

	/** Freight Agent checkbox field for a service type, or null when none applies. */
	function moduleFlagForServiceType(st) {
		const c = canonicalChargeServiceType(st);
		if (!c || MODULE_FLAGS_WITHOUT_SERVICE.has(c)) return null;
		if (c === "custom") return "customs";
		if (["air", "sea", "transport", "warehousing"].includes(c)) return c;
		return null;
	}

	/** Sales Quote main_service is a Select (Air/Sea/…); on linked bookings it is a Dynamic Link job ID. */
	function quoteStyleMainService(frm) {
		const df =
			(frm.get_docfield && frm.get_docfield("main_service")) ||
			frappe.meta.get_docfield(frm.doctype, "main_service");
		if (!df || df.fieldtype === "Dynamic Link" || !frm.doc.main_service) {
			return null;
		}
		return frm.doc.main_service;
	}

	function resolveServiceTypeLabel(frm, fieldname, row) {
		if (row && row.service_type) {
			return row.service_type;
		}
		if (FIELD_SERVICE_MAP[fieldname]) {
			return FIELD_SERVICE_MAP[fieldname];
		}
		const quoteMain = quoteStyleMainService(frm);
		if (quoteMain) {
			return quoteMain;
		}
		if (SETTINGS_DOCTYPE_SERVICE[frm.doctype]) {
			return SETTINGS_DOCTYPE_SERVICE[frm.doctype];
		}
		return DOCTYPE_IMPLIED_SERVICE[frm.doctype] || null;
	}

	function stripFreightAgentLinkFilters(doctype, fieldname, childFieldname) {
		const df = frappe.meta.get_docfield(doctype, fieldname, childFieldname);
		if (df && df.link_filters) {
			df.link_filters = null;
		}
	}

	function clearIncompatibleFreightAgent(frm, fieldname, serviceType, childFieldname, cdn) {
		const value = childFieldname
			? (locals[childFieldname] && locals[childFieldname][cdn] && locals[childFieldname][cdn][fieldname])
			: frm.doc[fieldname];
		if (!value) return;
		const flag = moduleFlagForServiceType(serviceType);
		if (!flag) return;
		frappe.db.get_value("Freight Agent", value, flag, (r) => {
			if (r && r[flag]) return;
			if (childFieldname && cdn) {
				frappe.model.set_value(childFieldname, cdn, fieldname, "");
			} else {
				frm.set_value(fieldname, "");
			}
		});
	}

	function setupParentFreightAgentQueries(frm) {
		(frm.meta.fields || []).forEach((df) => {
			if (df.fieldtype !== "Link" || df.options !== "Freight Agent") return;
			stripFreightAgentLinkFilters(frm.doctype, df.fieldname);
			frm.set_query(df.fieldname, function () {
				stripFreightAgentLinkFilters(frm.doctype, df.fieldname);
				const filters = { is_active: 1 };
				const serviceType = resolveServiceTypeLabel(frm, df.fieldname);
				const flag = moduleFlagForServiceType(serviceType);
				if (flag) {
					filters[flag] = 1;
				}
				return { filters };
			});
		});
	}

	function setupChildFreightAgentQueries(frm) {
		(frm.meta.fields || []).forEach((tableDf) => {
			if (tableDf.fieldtype !== "Table") return;
			const childMeta = frappe.get_meta(tableDf.options);
			if (!childMeta) return;
			(childMeta.fields || []).forEach((cdf) => {
				if (cdf.fieldtype !== "Link" || cdf.options !== "Freight Agent") return;
				stripFreightAgentLinkFilters(tableDf.options, cdf.fieldname, tableDf.fieldname);
				frm.set_query(cdf.fieldname, tableDf.fieldname, function (doc, cdt, cdn) {
					stripFreightAgentLinkFilters(tableDf.options, cdf.fieldname, tableDf.fieldname);
					const row = (locals[cdt] && locals[cdt][cdn]) || doc;
					const filters = { is_active: 1 };
					const serviceType = resolveServiceTypeLabel(frm, cdf.fieldname, row);
					const flag = moduleFlagForServiceType(serviceType);
					if (flag) {
						filters[flag] = 1;
					}
					return { filters };
				});
			});
		});
	}

	logistics.freight_agent_service.moduleFlagForServiceType = moduleFlagForServiceType;
	logistics.freight_agent_service.resolveServiceTypeLabel = resolveServiceTypeLabel;
	logistics.freight_agent_service.clearIncompatibleFreightAgent = clearIncompatibleFreightAgent;

	logistics.freight_agent_service.setupForm = function (frm) {
		if (!frm || !frm.meta) return;
		setupParentFreightAgentQueries(frm);
		setupChildFreightAgentQueries(frm);
	};

	frappe.ui.form.on("*", {
		refresh(frm) {
			logistics.freight_agent_service.setupForm(frm);
		},
		main_service(frm) {
			["freight_agent", "freight_agent_sea"].forEach((fieldname) => {
				if (!frm.fields_dict[fieldname]) return;
				clearIncompatibleFreightAgent(frm, fieldname, resolveServiceTypeLabel(frm, fieldname));
			});
		},
	});
})();
