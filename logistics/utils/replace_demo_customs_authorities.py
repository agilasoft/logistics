# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Replace Customs Authority masters from the ATN/ASL spreadsheet.

Sheet:
    https://docs.google.com/spreadsheets/d/1t3kAEqS13Ix2PYcyB0kfRi-2oCVDCugtU95qCZQzB9c/edit?gid=512053172

The sheet sets Authority Type to CUSTOMS. That value is not in the
Customs Authority select (National, Regional, Port, Airport, Border),
so CUSTOMS is stored as Port. Country is set to Philippines when that
Country record exists. Operating hours are stored as 06:00:00 and 17:00:00.

Dry run first:

    from logistics.utils.replace_demo_customs_authorities import replace_demo_customs_authorities
    replace_demo_customs_authorities(dry_run=True)

Then run for real (must match the current site name):

    replace_demo_customs_authorities(
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
	"/export?format=csv&gid=512053172"
)

LOCAL_CSV = os.path.join(
	os.path.dirname(os.path.dirname(__file__)),
	"data",
	"atn_asl_customs_authorities.csv",
)

AUTHORITY_TYPE_FALLBACK = {
	"CUSTOMS": "Port",
}


def replace_demo_customs_authorities(dry_run=True, confirm_site=None, source="auto"):
	"""Delete Customs Authorities not in the sheet, then upsert sheet rows.

	source: "auto" (Google, then local CSV), "google", or "local"
	"""
	site = frappe.local.site
	if not dry_run and confirm_site != site:
		frappe.throw(
			f"Pass confirm_site='{site}' to replace customs authorities on this site. "
			"Live replace refused without an explicit matching site name."
		)

	rows = _load_rows(source)
	incoming = _normalize_rows(rows)
	keep = {row["name"] for row in incoming}
	existing_rows = frappe.get_all(
		"Customs Authority", fields=["name", "code"], limit_page_length=0
	)
	existing_names = {row.name for row in existing_rows}
	by_code = {}
	for row in existing_rows:
		code = (row.code or row.name or "").strip().upper()
		if code:
			by_code[code] = row.name

	resolved = []
	for row in incoming:
		found_name = by_code.get(row["name"]) or (row["name"] if row["name"] in existing_names else None)
		item = dict(row)
		item["found_name"] = found_name
		resolved.append(item)

	kept_names = {item["found_name"] or item["name"] for item in resolved}
	to_delete = sorted(existing_names - kept_names)
	to_create = [r for r in resolved if not r["found_name"]]
	to_update = [r for r in resolved if r["found_name"]]

	print(f"Site: {site}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
	print(f"Sheet rows: {len(incoming)}")
	print(f"Existing Customs Authority: {len(existing_names)}")
	print(f"Create: {len(to_create)}")
	print(f"Update: {len(to_update)}")
	print(f"Delete (not in sheet): {len(to_delete)}")
	if to_delete:
		print("  " + ", ".join(to_delete[:40]) + (" ..." if len(to_delete) > 40 else ""))
	for row in resolved:
		print(
			f"  {row['name']}: {row['city']}, {row['state']} | "
			f"type {row['sheet_authority_type']} -> {row['authority_type'] or '(blank)'}"
		)

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

	print("\nUnlinking Customs Authority from other documents...")
	_unlink(to_delete)
	frappe.db.commit()

	print(f"\nDeleting {len(to_delete)} Customs Authority records not in the sheet...")
	failed = []
	for name in to_delete:
		try:
			frappe.delete_doc("Customs Authority", name, force=1, ignore_permissions=True)
		except Exception as e:
			failed.append((name, str(e)[:240]))
			print(f"  FAIL delete {name}: {e}")
	frappe.db.commit()

	print(f"\nUpserting {len(resolved)} Customs Authority records...")
	created = updated = 0
	for row in resolved:
		try:
			if _upsert(row):
				created += 1
			else:
				updated += 1
		except Exception as e:
			failed.append((row["name"], str(e)[:240]))
			print(f"  FAIL {row['name']}: {e}")
	frappe.db.commit()
	frappe.clear_cache(doctype="Customs Authority")

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

	frappe.throw("Could not load Customs Authority sheet. " + " | ".join(errors))


def _normalize_rows(rows):
	options = _authority_type_options()
	country = "Philippines" if frappe.db.exists("Country", "Philippines") else None
	incoming = []
	used = set()
	for raw in rows:
		code = (raw.get("Code") or "").strip().upper()
		name = (raw.get("Customs Authority Name") or "").strip() or code
		if not code or not name:
			continue
		if code in used:
			frappe.throw(f"Customs Authority code {code} is repeated in the sheet.")
		used.add(code)
		sheet_type = (raw.get("Authority Type") or "").strip()
		incoming.append(
			{
				"name": code,
				"code": code,
				"customs_authority_name": name,
				"is_active": _as_check(raw.get("Is Active")),
				"sheet_authority_type": sheet_type,
				"authority_type": _resolve_authority_type(sheet_type, options),
				"country": country,
				"postal_code": (raw.get("Postal Code") or "").strip(),
				"address_line_1": (raw.get("Address Line 1") or "").strip(),
				"address_line_2": (raw.get("Address Line 2") or "").strip(),
				"email": (raw.get("Email") or "").strip(),
				"phone": (raw.get("Phone") or "").strip(),
				"website": (raw.get("Website") or "").strip(),
				"city": (raw.get("City") or "").strip(),
				"state": (raw.get("State/Province") or "").strip(),
				"operating_hours_start": _to_time(raw.get("Operating Hours Start")),
				"operating_hours_end": _to_time(raw.get("Operating Hours End")),
				"currency": _currency(raw.get("Currency")),
			}
		)
	incoming.sort(key=lambda row: row["name"])
	return incoming


def _authority_type_options():
	field = frappe.get_meta("Customs Authority").get_field("authority_type")
	if not field or not field.options:
		return set()
	return {opt.strip() for opt in field.options.split("\n") if opt.strip()}


def _resolve_authority_type(value, options):
	text = (value or "").strip()
	if text in options:
		return text
	fallback = AUTHORITY_TYPE_FALLBACK.get(text.upper())
	if fallback and (not options or fallback in options):
		return fallback
	return None


def _as_check(value):
	text = (value or "").strip().lower()
	if text in ("1", "yes", "true", "y"):
		return 1
	if text in ("0", "no", "false", "n"):
		return 0
	return 1


def _to_time(value):
	text = (value or "").strip().upper().replace(".", "")
	if not text:
		return None
	parts = text.split()
	clock = parts[0]
	ampm = parts[1] if len(parts) > 1 else ""
	hm = clock.split(":")
	hour = int(hm[0])
	minute = int(hm[1]) if len(hm) > 1 else 0
	if ampm == "PM" and hour < 12:
		hour += 12
	if ampm == "AM" and hour == 12:
		hour = 0
	return f"{hour:02d}:{minute:02d}:00"


def _currency(value):
	code = (value or "").strip().upper()
	if not code:
		return None
	if frappe.db.exists("Currency", code):
		return code
	print(f"  currency {code} is not in Currency master; leaving it blank")
	return None


def _upsert(row):
	values = {
		"code": row["code"],
		"customs_authority_name": row["customs_authority_name"],
		"is_active": row["is_active"],
		"country": row["country"],
		"postal_code": row["postal_code"],
		"address_line_1": row["address_line_1"],
		"address_line_2": row["address_line_2"],
		"email": row["email"],
		"phone": row["phone"],
		"website": row["website"],
		"city": row["city"],
		"state": row["state"],
		"operating_hours_start": row["operating_hours_start"],
		"operating_hours_end": row["operating_hours_end"],
		"currency": row["currency"],
	}
	if row["authority_type"]:
		values["authority_type"] = row["authority_type"]

	target = row.get("found_name")
	if target and frappe.db.exists("Customs Authority", target):
		doc = frappe.get_doc("Customs Authority", target)
		doc.update(values)
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
		return False

	doc = frappe.new_doc("Customs Authority")
	doc.update(values)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return True


def _unlink(names):
	if not names:
		return

	try:
		link_fields = get_link_fields("Customs Authority")
	except Exception:
		link_fields = []

	name_set = set(names)
	chunks = [names[i : i + 500] for i in range(0, len(names), 500)]
	for lf in link_fields:
		parent = lf.parent
		field = lf.fieldname
		if not parent or not field or parent == "Customs Authority":
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
