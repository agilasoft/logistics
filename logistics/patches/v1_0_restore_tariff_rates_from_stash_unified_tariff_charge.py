# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""After Tariff Charge exists, populate ``Tariff.rates`` from pre_model_sync stash then drop stash."""

import json

import frappe
from frappe.utils import cint

from logistics.utils.charges_calculation import TARIFF_TO_CHARGE_FIELD_ALIASES

STASH_TABLE = "_tariff_legacy_rates_stash"

SERVICE_BY_SOURCE = {
	"Air Freight Rate": "Air",
	"Sea Freight Rate": "Sea",
	"Transport Rate": "Transport",
	"Warehouse Rate": "Warehousing",
	"Customs Rate": "Customs",
}

SKIP = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"parent",
		"parentfield",
		"parenttype",
		"idx",
		"doctype",
		"calculation_method",
		"rate_value",
		"rate",
	}
)


def execute():
	if not frappe.db.table_exists(STASH_TABLE):
		return
	cnt = frappe.db.sql(f"SELECT COUNT(*) FROM `{STASH_TABLE}`")[0][0]
	if not cnt:
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{STASH_TABLE}`")
		frappe.db.commit()
		return

	meta = frappe.get_meta("Tariff Charge")
	allowed = {df.fieldname for df in meta.fields}

	rows = frappe.db.sql(
		f"SELECT * FROM `{STASH_TABLE}` ORDER BY parent_tariff, stash_idx",
		as_dict=True,
	)
	by_parent = {}
	for r in rows:
		by_parent.setdefault(r.parent_tariff, []).append(r)

	for parent, seq in by_parent.items():
		if not frappe.db.exists("Tariff", parent):
			continue
		doc = frappe.get_doc("Tariff", parent)
		if doc.get("rates"):
			continue
		for st in seq:
			d = json.loads(st.row_json)
			doc.append("rates", legacy_row_to_tariff_charge(st.source_dt, d, allowed))
		doc.flags.ignore_validate = True
		doc.save(ignore_permissions=True)

	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{STASH_TABLE}`")
	frappe.db.commit()


def legacy_row_to_tariff_charge(source_dt, d, allowed):
	svc = SERVICE_BY_SOURCE.get(source_dt)
	if not svc:
		return {}
	calc = (d.get("calculation_method") or "Per Unit").strip()
	rv = d.get("rate_value")
	if rv is None:
		rv = d.get("rate")
	rv = rv or 0
	cur = d.get("currency")

	row = {
		"service_type": svc,
		"charge_type": "Revenue",
		"quotation_type": "Regular",
		"revenue_calculation_method": calc,
		"cost_calculation_method": calc,
		"unit_rate": rv,
		"unit_cost": rv,
		"quantity": 1,
		"cost_quantity": 1,
		"tariff_valid_from": d.get("valid_from"),
		"tariff_valid_to": d.get("valid_to"),
		"tariff_rate_active": cint(d.get("is_active", 1)),
	}
	if cur:
		row["currency"] = cur
		row["cost_currency"] = cur

	ic = d.get("item_code") or d.get("item_charge")
	if ic and "item_code" in allowed:
		row["item_code"] = ic

	for key, val in d.items():
		if key in SKIP or val in (None, "", []):
			continue
		tgt = TARIFF_TO_CHARGE_FIELD_ALIASES.get(key, key)
		if tgt not in allowed:
			continue
		if tgt in row:
			continue
		row[tgt] = val

	return row
