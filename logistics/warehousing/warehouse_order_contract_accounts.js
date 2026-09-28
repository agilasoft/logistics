// Copyright (c) 2026, www.agilasoft.com and contributors
// Sync company / branch / cost center / profit center from Warehouse Contract on warehouse orders.

frappe.provide("logistics.warehousing");

const WH_ORDER_CONTRACT_FIELD = {
	"Inbound Order": "contract",
	"Release Order": "contract",
	"Cross-Docking Order": "contract",
	"Transfer Order": "contract",
	"VAS Order": "contract",
	"Stocktake Order": "contract",
	"Warehouse Job": "warehouse_contract",
};

const WH_CONTRACT_ACCOUNT_FIELDS = ["company", "branch", "cost_center", "profit_center"];

logistics.warehousing.sync_accounts_from_warehouse_contract = function (frm, opts = {}) {
	const contractField = opts.contract_field || WH_ORDER_CONTRACT_FIELD[frm.doctype] || "contract";
	const contract = frm.doc[contractField];
	if (!contract) {
		return;
	}
	const fields = WH_CONTRACT_ACCOUNT_FIELDS.filter((f) => frm.fields_dict[f]);
	if (!fields.length) {
		return;
	}
	frappe.db.get_value("Warehouse Contract", contract, fields, (r) => {
		if (!r) {
			return;
		}
		fields.forEach((field) => {
			const value = r[field];
			if (value != null && value !== "" && frm.doc[field] !== value) {
				frm.set_value(field, value);
			}
		});
		if (typeof opts.callback === "function") {
			opts.callback();
		}
	});
};

logistics.warehousing.warehouse_order_defaults_from_contract = function (contractDoc) {
	return {
		contract: contractDoc.name,
		customer: contractDoc.customer,
		company: contractDoc.company,
		branch: contractDoc.branch,
		cost_center: contractDoc.cost_center,
		profit_center: contractDoc.profit_center,
	};
};

Object.entries(WH_ORDER_CONTRACT_FIELD).forEach(([doctype, contractField]) => {
	const handlers = {
		onload(frm) {
			if (!frm.doc[contractField] || frm.doc.company) {
				return;
			}
			logistics.warehousing.sync_accounts_from_warehouse_contract(frm, {
				contract_field: contractField,
			});
		},
	};
	handlers[contractField] = function (frm) {
		if (!frm.doc[contractField]) {
			return;
		}
		logistics.warehousing.sync_accounts_from_warehouse_contract(frm, {
			contract_field: contractField,
		});
	};
	frappe.ui.form.on(doctype, handlers);
});
