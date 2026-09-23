# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Replace Consignee masters from the ATN/ASL spreadsheet.

Sheet:
    https://docs.google.com/spreadsheets/d/1t3kAEqS13Ix2PYcyB0kfRi-2oCVDCugtU95qCZQzB9c/edit?gid=1559381395

Dry run first:

    from logistics.utils.replace_demo_consignees import replace_demo_consignees
    replace_demo_consignees(dry_run=True)

Then run for real (must match the current site name):

    replace_demo_consignees(
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

from logistics.utils.party_code import ensure_unique_code, generate_party_code

SHEET_CSV_URL = (
	"https://docs.google.com/spreadsheets/d/1t3kAEqS13Ix2PYcyB0kfRi-2oCVDCugtU95qCZQzB9c"
	"/export?format=csv&gid=1559381395"
)

CLASSIFICATION_OPTIONS = {
	"SGL",
	"GL",
	"Yellow Lane",
	"Red Lane",
	"Not Classified",
}

LOCAL_CSV = os.path.join(
	os.path.dirname(os.path.dirname(__file__)),
	"data",
	"atn_asl_consignees.csv",
)


def replace_demo_consignees(dry_run=True, confirm_site=None, source="auto"):
	"""Delete existing Consignees and import the ATN/ASL sheet.

	source: "auto" (Google, then local CSV), "google", or "local"
	"""
	site = frappe.local.site
	if not dry_run and confirm_site != site:
		frappe.throw(
			f"Pass confirm_site='{site}' to replace consignees on this site. "
			"Live replace refused without an explicit matching site name."
		)

	rows = _load_rows(source)
	incoming = _normalize_rows(rows)
	keep = {row["code"] for row in incoming}
	existing = set(frappe.get_all("Consignee", pluck="name"))
	to_delete = sorted(existing - keep)
	to_create = [r for r in incoming if r["code"] not in existing]
	to_update = [r for r in incoming if r["code"] in existing]
	missing_unloco = sorted({r["unloco"] for r in incoming if r["unloco"] and r["skipped_unloco"]})

	print(f"Site: {site}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
	print(f"Sheet rows after dedupe: {len(incoming)}")
	print(f"Existing Consignee: {len(existing)}")
	print(f"Create: {len(to_create)}")
	print(f"Update: {len(to_update)}")
	print(f"Delete (not in sheet): {len(to_delete)}")
	if missing_unloco:
		print(f"UNLOCO not in master (will leave blank): {len(missing_unloco)}")
		print("  " + ", ".join(missing_unloco[:40]) + (" ..." if len(missing_unloco) > 40 else ""))

	if dry_run:
		print("\nDry run only. Run again with dry_run=False to apply.")
		return {
			"dry_run": True,
			"site": site,
			"incoming": len(incoming),
			"create": len(to_create),
			"update": len(to_update),
			"delete": len(to_delete),
			"missing_unloco": missing_unloco,
		}

	frappe.set_user("Administrator")
	frappe.flags.ignore_links = True

	print("\nUnlinking Consignee from other documents...")
	_unlink_consignees(to_delete)
	frappe.db.commit()

	print(f"\nDeleting {len(to_delete)} Consignee records not in the sheet...")
	failed = []
	for i, name in enumerate(to_delete, 1):
		try:
			frappe.delete_doc("Consignee", name, force=1, ignore_permissions=True)
		except Exception as e:
			failed.append((name, str(e)[:240]))
			print(f"  FAIL delete {name}: {e}")
		if i % 50 == 0:
			frappe.db.commit()
			print(f"  ... {i}/{len(to_delete)}")
	frappe.db.commit()

	print(f"\nUpserting {len(incoming)} Consignee records...")
	created = updated = 0
	for i, row in enumerate(incoming, 1):
		try:
			if _upsert_consignee(row):
				created += 1
			else:
				updated += 1
		except Exception as e:
			failed.append((row["code"], str(e)[:240]))
			print(f"  FAIL {row['code']}: {e}")
		if i % 50 == 0:
			frappe.db.commit()
			print(f"  ... {i}/{len(incoming)}")
	frappe.db.commit()
	frappe.clear_cache(doctype="Consignee")

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
			if raw.lstrip().startswith("Code,"):
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

	frappe.throw("Could not load Consignee sheet. " + " | ".join(errors))


def _normalize_rows(rows):
	# Dedupe by code: prefer the row that has a UNLOCO.
	by_code = {}
	blank_code_rows = []
	for raw in rows:
		name = (raw.get("Consignee Name") or "").strip()
		if not name:
			continue
		code = (raw.get("Code") or "").strip().upper()
		unloco = (raw.get("Default UNLOCO") or "").strip().upper()
		classification = (raw.get("Customs Importer Classification") or "").strip()
		row = {
			"code": code,
			"consignee_name": name,
			"unloco": unloco,
			"classification": classification if classification in CLASSIFICATION_OPTIONS else "",
			"skipped_unloco": False,
		}
		if not code:
			blank_code_rows.append(row)
			continue
		prev = by_code.get(code)
		if not prev or (unloco and not prev["unloco"]):
			by_code[code] = row

	used = set(by_code)
	incoming = list(by_code.values())
	for row in blank_code_rows:
		base = generate_party_code(row["consignee_name"], row["unloco"])
		code = _unique_code(base, used)
		row["code"] = code
		used.add(code)
		incoming.append(row)

	unloco_exists = _unloco_set({r["unloco"] for r in incoming if r["unloco"]})
	for row in incoming:
		if row["unloco"] and row["unloco"] not in unloco_exists:
			row["skipped_unloco"] = True

	incoming.sort(key=lambda r: r["code"])
	return incoming


def _unique_code(base, used):
	candidate = ensure_unique_code("Consignee", base, None, "code")
	if candidate not in used:
		return candidate
	seq = 1
	while True:
		candidate = (base[:6] + str(seq).zfill(3))[:9]
		if candidate not in used and not frappe.db.exists("Consignee", {"code": candidate}):
			return candidate
		seq += 1
		if seq > 999:
			frappe.throw(f"Could not allocate a unique Consignee code from {base}")


def _unloco_set(codes):
	if not codes or not frappe.db.exists("DocType", "UNLOCO"):
		return set()
	found = frappe.get_all("UNLOCO", filters={"name": ("in", list(codes))}, pluck="name")
	return {n.upper() for n in found}


def _upsert_consignee(row):
	unloco = None if row["skipped_unloco"] else (row["unloco"] or None)
	values = {
		"consignee_name": row["consignee_name"],
		"default_unloco": unloco,
		"is_active": 1,
	}
	if row["classification"]:
		values["customs_importer_classification"] = row["classification"]

	if frappe.db.exists("Consignee", row["code"]):
		doc = frappe.get_doc("Consignee", row["code"])
		doc.update(values)
		doc.flags.ignore_permissions = True
		doc.save()
		return False

	doc = frappe.get_doc(
		{
			"doctype": "Consignee",
			"code": row["code"],
			**values,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return True


def _unlink_consignees(names):
	if not names:
		if frappe.db.table_exists("Dynamic Link"):
			frappe.db.delete("Dynamic Link", {"link_doctype": "Consignee"})
		return

	try:
		link_fields = get_link_fields("Consignee")
	except Exception:
		link_fields = []

	name_set = set(names)
	chunks = [names[i : i + 500] for i in range(0, len(names), 500)]
	for lf in link_fields:
		parent = lf.parent
		field = lf.fieldname
		if not parent or not field or parent == "Consignee":
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

	if frappe.db.table_exists("Dynamic Link"):
		for chunk in chunks:
			frappe.db.sql(
				"""
				DELETE FROM `tabDynamic Link`
				WHERE link_doctype = 'Consignee' AND link_name IN %(names)s
				""",
				{"names": chunk},
			)
