# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Replace Commodity masters from the ATN/ASL spreadsheet.

Sheet:
    https://docs.google.com/spreadsheets/d/1t3kAEqS13Ix2PYcyB0kfRi-2oCVDCugtU95qCZQzB9c/edit?gid=273551933

Default HS Code values are chapter ranges (e.g. 0101–0106). Matching
Customs Tariff Number records are created so the Link field stays valid.

Dry run first:

    from logistics.utils.replace_demo_commodities import replace_demo_commodities
    replace_demo_commodities(dry_run=True)

Then run for real (must match the current site name):

    replace_demo_commodities(
        dry_run=False,
        confirm_site="atndemo.s.frappe.cloud",
    )
"""

from __future__ import annotations

import csv
import io
import os
import urllib.request

import frappe
from frappe.model.rename_doc import get_link_fields

SHEET_CSV_URL = (
	"https://docs.google.com/spreadsheets/d/1t3kAEqS13Ix2PYcyB0kfRi-2oCVDCugtU95qCZQzB9c"
	"/export?format=csv&gid=273551933"
)

LOCAL_CSV = os.path.join(
	os.path.dirname(os.path.dirname(__file__)),
	"data",
	"atn_asl_commodities.csv",
)

PERISHABLE_IATA = {"AVI", "PEM", "PES", "PEF", "PEP", "EAT"}
HAZARDOUS_IATA = {"DGR"}
TIMBER_CODES = {"AHTN044"}

COMMODITY_LINK_FIELDS = (
	("Docket Package", "commodity"),
	("Transport Consolidation Packages", "commodity"),
	("Sea Freight Packages", "commodity"),
	("Transport Order Package", "commodity"),
	("Sea Booking Packages", "commodity"),
	("Air Booking Packages", "commodity"),
	("Transport Job Package", "commodity"),
	("Air Shipment Packages", "commodity"),
	("Project Job Package", "commodity"),
	("Project Order Package", "commodity"),
	("Project Job Material", "commodity"),
	("Special Project Package", "commodity"),
	("Special Project Site Receipt", "commodity"),
	("Sea Consolidation Packages", "commodity"),
	("Permit Type Commodity", "commodity"),
	("Declaration Commodity", "commodity"),
	("Declaration Order Commodity", "commodity"),
	("Commercial Invoice Line Item", "commodity_code"),
	("Declaration Product Code", "commodity_code"),
)


def replace_demo_commodities(dry_run=True, confirm_site=None, source="auto"):
	"""Delete existing Commodities not in the sheet, then upsert sheet rows.

	source: "auto" (Google, then local CSV), "google", or "local"
	"""
	site = frappe.local.site
	if not dry_run and confirm_site != site:
		frappe.throw(
			f"Pass confirm_site='{site}' to replace commodities on this site. "
			"Live replace refused without an explicit matching site name."
		)

	rows = _load_rows(source)
	incoming = _normalize_rows(rows)
	keep = {row["name"] for row in incoming}
	existing = set(frappe.get_all("Commodity", pluck="name"))
	to_delete = sorted(existing - keep)
	to_create = [r for r in incoming if r["name"] not in existing]
	to_update = [r for r in incoming if r["name"] in existing]
	has_tariff = frappe.db.exists("DocType", "Customs Tariff Number")

	print(f"Site: {site}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
	print(f"Sheet rows: {len(incoming)}")
	print(f"Existing Commodity: {len(existing)}")
	print(f"Create: {len(to_create)}")
	print(f"Update: {len(to_update)}")
	print(f"Delete (not in sheet): {len(to_delete)}")
	if to_delete:
		print("  " + ", ".join(to_delete[:40]) + (" ..." if len(to_delete) > 40 else ""))
	for row in incoming[:8]:
		print(
			f"  {row['name']}: {row['iata_commodity_code']} / {row['universal_commodity_code']}"
			f" / {row['default_hs_code'] or '-'} | {row['description'][:60]}"
		)
	if len(incoming) > 8:
		print(f"  ... {len(incoming) - 8} more")

	if dry_run:
		print("\nDry run only. Run again with dry_run=False to apply.")
		return {
			"dry_run": True,
			"site": site,
			"incoming": len(incoming),
			"create": len(to_create),
			"update": len(to_update),
			"delete": len(to_delete),
		}

	frappe.set_user("Administrator")
	frappe.flags.ignore_links = True

	print("\nUnlinking Commodity from other documents...")
	_unlink_commodities(to_delete)
	frappe.db.commit()

	print(f"\nDeleting {len(to_delete)} Commodity records not in the sheet...")
	failed = []
	for name in to_delete:
		try:
			frappe.delete_doc("Commodity", name, force=1, ignore_permissions=True)
		except Exception as e:
			failed.append((name, str(e)[:240]))
			print(f"  FAIL delete {name}: {e}")
	frappe.db.commit()

	print(f"\nUpserting {len(incoming)} Commodity records...")
	created = updated = 0
	for row in incoming:
		try:
			if has_tariff:
				_ensure_tariff(row)
			if _upsert_commodity(row, has_tariff):
				created += 1
			else:
				updated += 1
		except Exception as e:
			failed.append((row["name"], str(e)[:240]))
			print(f"  FAIL {row['name']}: {e}")
	frappe.db.commit()
	frappe.clear_cache(doctype="Commodity")

	print(f"\nCreated: {created}")
	print(f"Updated: {updated}")
	print(f"Delete attempted: {len(to_delete)}")
	print(f"Failed: {len(failed)}")
	for name, err in failed[:40]:
		print(f"  {name}: {err}")
	if not failed:
		print("Done.")

	return {
		"dry_run": False,
		"site": site,
		"created": created,
		"updated": updated,
		"deleted": len(to_delete),
		"failed": failed,
	}


def _load_rows(source):
	errors = []
	if source in ("auto", "google"):
		try:
			print(f"Fetching {SHEET_CSV_URL}")
			req = urllib.request.Request(SHEET_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
			with urllib.request.urlopen(req, timeout=60) as resp:
				raw = resp.read().decode("utf-8-sig")
			if raw.lstrip().upper().startswith("CODE,"):
				return list(csv.DictReader(io.StringIO(raw)))
			errors.append("Google response was not a CSV")
		except Exception as e:
			errors.append(f"Google fetch failed: {e}")
			if source == "google":
				frappe.throw(errors[-1])

	if source in ("auto", "local"):
		if os.path.exists(LOCAL_CSV):
			print(f"Reading {LOCAL_CSV}")
			with open(LOCAL_CSV, newline="", encoding="utf-8-sig") as f:
				return list(csv.DictReader(f))
		errors.append(f"Local CSV not found: {LOCAL_CSV}")

	frappe.throw("Could not load Commodity sheet. " + " | ".join(errors))


def _iata_tokens(iata):
	return [t.strip().upper() for t in (iata or "").replace("|", "/").split("/") if t.strip()]


def _normalize_rows(rows):
	incoming = []
	used = set()
	for raw in rows:
		code = (raw.get("Code") or "").strip().upper()
		description = (raw.get("Description") or "").strip()
		if not code or not description:
			continue
		if code in used:
			frappe.throw(f"Commodity code {code} is repeated for {description}.")
		used.add(code)
		iata = (raw.get("IATA Commodity Code") or "").strip()
		tokens = _iata_tokens(iata)
		incoming.append(
			{
				"name": code,
				"code": code,
				"description": description,
				"iata_commodity_code": iata,
				"universal_commodity_code": (raw.get("Universal Commodity Code") or "").strip(),
				"default_hs_code": (raw.get("Default HS Code") or "").strip(),
				"perishable": 1 if any(t in PERISHABLE_IATA for t in tokens) else 0,
				"hazardous": 1 if any(t in HAZARDOUS_IATA for t in tokens) else 0,
				"timber": 1 if code in TIMBER_CODES else 0,
			}
		)
	incoming.sort(key=lambda r: r["name"])
	return incoming


def _ensure_tariff(row):
	hs = row["default_hs_code"]
	if not hs:
		return
	if frappe.db.exists("Customs Tariff Number", hs):
		return
	doc = frappe.new_doc("Customs Tariff Number")
	doc.tariff_number = hs
	doc.description = (row["description"] or "")[:140]
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)


def _upsert_commodity(row, has_tariff):
	values = {
		"code": row["code"],
		"description": row["description"],
		"active": 1,
		"universal_commodity_code": row["universal_commodity_code"],
		"iata_commodity_code": row["iata_commodity_code"],
		"forwarding": 1,
		"shipping": 1,
		"land_transport": 1,
		"perishable": row["perishable"],
		"timber": row["timber"],
		"hazardous": row["hazardous"],
	}
	if has_tariff and row["default_hs_code"]:
		values["default_hs_code"] = row["default_hs_code"]
	else:
		values["default_hs_code"] = None

	if frappe.db.exists("Commodity", row["name"]):
		doc = frappe.get_doc("Commodity", row["name"])
		doc.update(values)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = True
		doc.save()
		return False

	doc = frappe.new_doc("Commodity")
	doc.update(values)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True, ignore_links=True, set_name=row["name"])
	return True


def _unlink_commodities(names):
	if not names:
		return

	try:
		link_fields = get_link_fields("Commodity")
	except Exception:
		link_fields = []

	seen = set()
	merged = []
	for lf in link_fields:
		merged.append(lf)
		seen.add((lf.parent, lf.fieldname))
	for parent, field in COMMODITY_LINK_FIELDS:
		if (parent, field) in seen:
			continue
		merged.append(frappe._dict(parent=parent, fieldname=field, issingle=0))

	name_set = set(names)
	chunks = [names[i : i + 500] for i in range(0, len(names), 500)]
	for lf in merged:
		parent = lf.parent
		field = lf.fieldname
		if not parent or not field or parent == "Commodity":
			continue
		if not frappe.db.table_exists(parent):
			continue
		try:
			if int(lf.issingle or 0):
				val = frappe.db.get_single_value(parent, field)
				if val in name_set:
					frappe.db.set_single_value(parent, field, None)
				continue
			for chunk in chunks:
				frappe.db.sql(
					f"UPDATE `tab{parent}` SET `{field}` = NULL WHERE `{field}` IN %(names)s",
					{"names": chunk},
				)
		except Exception as e:
			print(f"  skip {parent}.{field}: {e}")
