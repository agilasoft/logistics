# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Replace Exporter Category masters from the ATN/ASL spreadsheet.

Sheet:
    https://docs.google.com/spreadsheets/d/1t3kAEqS13Ix2PYcyB0kfRi-2oCVDCugtU95qCZQzB9c/edit?gid=816019952

The sheet lists TME twice (Manufacturer and Trader / Merchant). Trader / Merchant
keeps TME; Manufacturer is stored as MME so document names stay unique.
The sheet also truncates Individual / Personal Exporter as "Exporte".

Dry run first:

    from logistics.utils.replace_demo_exporter_categories import replace_demo_exporter_categories
    replace_demo_exporter_categories(dry_run=True)

Then run for real (must match the current site name):

    replace_demo_exporter_categories(
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
	"/export?format=csv&gid=816019952"
)

# Sheet code + description -> unique document name when the sheet repeats a code.
CODE_OVERRIDES = {
	("TME", "MANUFACTURER"): "MME",
}

DESCRIPTION_OVERRIDES = {
	("IPE", "INDIVIDUAL / PERSONAL EXPORTE"): "Individual / Personal Exporter",
}

LOCAL_CSV = os.path.join(
	os.path.dirname(os.path.dirname(__file__)),
	"data",
	"atn_asl_exporter_categories.csv",
)


def replace_demo_exporter_categories(dry_run=True, confirm_site=None, source="auto"):
	"""Delete existing Exporter Categories not in the sheet, then upsert sheet rows.

	source: "auto" (Google, then local CSV), "google", or "local"
	"""
	site = frappe.local.site
	if not dry_run and confirm_site != site:
		frappe.throw(
			f"Pass confirm_site='{site}' to replace exporter categories on this site. "
			"Live replace refused without an explicit matching site name."
		)

	rows = _load_rows(source)
	incoming = _normalize_rows(rows)
	keep = {row["name"] for row in incoming}
	existing = set(frappe.get_all("Exporter Category", pluck="name"))
	to_delete = sorted(existing - keep)
	to_create = [r for r in incoming if r["name"] not in existing]
	to_update = [r for r in incoming if r["name"] in existing]
	has_is_active = frappe.db.has_column("Exporter Category", "is_active")

	print(f"Site: {site}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
	print(f"Sheet rows after unique codes: {len(incoming)}")
	print(f"Existing Exporter Category: {len(existing)}")
	print(f"Create: {len(to_create)}")
	print(f"Update: {len(to_update)}")
	print(f"Delete (not in sheet): {len(to_delete)}")
	if to_delete:
		print("  " + ", ".join(to_delete[:40]) + (" ..." if len(to_delete) > 40 else ""))
	for row in incoming:
		print(f"  {row['name']}: {row['description']}")

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

	print("\nUnlinking Exporter Category from other documents...")
	_unlink_categories(to_delete)
	frappe.db.commit()

	print(f"\nDeleting {len(to_delete)} Exporter Category records not in the sheet...")
	failed = []
	for name in to_delete:
		try:
			frappe.delete_doc("Exporter Category", name, force=1, ignore_permissions=True)
		except Exception as e:
			failed.append((name, str(e)[:240]))
			print(f"  FAIL delete {name}: {e}")
	frappe.db.commit()

	print(f"\nUpserting {len(incoming)} Exporter Category records...")
	created = updated = 0
	for row in incoming:
		try:
			if _upsert_category(row, has_is_active):
				created += 1
			else:
				updated += 1
		except Exception as e:
			failed.append((row["name"], str(e)[:240]))
			print(f"  FAIL {row['name']}: {e}")
	frappe.db.commit()
	frappe.clear_cache(doctype="Exporter Category")

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

	frappe.throw("Could not load Exporter Category sheet. " + " | ".join(errors))


def _normalize_rows(rows):
	incoming = []
	used = set()
	for raw in rows:
		code = (raw.get("Code") or "").strip().upper()
		description = (raw.get("Description") or "").strip()
		if not code or not description:
			continue
		name = CODE_OVERRIDES.get((code, description.upper()), code)
		description = DESCRIPTION_OVERRIDES.get((name, description.upper()), description)
		if name in used:
			frappe.throw(
				f"Exporter Category code {name} is repeated for {description}. "
				"Give Manufacturer a unique code in the sheet."
			)
		used.add(name)
		incoming.append({"name": name, "code": name, "description": description})
	incoming.sort(key=lambda r: r["name"])
	return incoming


def _upsert_category(row, has_is_active):
	values = {
		"code": row["code"],
		"description": row["description"],
	}
	if has_is_active:
		values["is_active"] = 1

	if frappe.db.exists("Exporter Category", row["name"]):
		doc = frappe.get_doc("Exporter Category", row["name"])
		doc.update(values)
		doc.flags.ignore_permissions = True
		doc.save()
		return False

	doc = frappe.new_doc("Exporter Category")
	doc.update(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True, set_name=row["name"])
	return True


def _unlink_categories(names):
	if not names:
		return

	try:
		link_fields = get_link_fields("Exporter Category")
	except Exception:
		link_fields = []

	name_set = set(names)
	chunks = [names[i : i + 500] for i in range(0, len(names), 500)]
	for lf in link_fields:
		parent = lf.parent
		field = lf.fieldname
		if not parent or not field or parent == "Exporter Category":
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
