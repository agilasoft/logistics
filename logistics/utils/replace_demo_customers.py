# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Upsert Customer masters from the ATN/ASL Google Sheet (no deletes).

Sheet:
    https://docs.google.com/spreadsheets/d/1oiF3DmiQz0oS3kxV8Ld0gc3IKfLIacwDVJGqgk8jG5A/edit?gid=184185565

Dry run:

    bench --site atndemo.s.frappe.cloud execute logistics.utils.replace_demo_customers.replace_demo_customers --kwargs '{"dry_run": true}'

Live:

    bench --site atndemo.s.frappe.cloud execute logistics.utils.replace_demo_customers.replace_demo_customers --kwargs '{"dry_run": false, "confirm_site": "atndemo.s.frappe.cloud"}'
"""

from __future__ import annotations

import csv
import io
import os
import urllib.request

import frappe
from frappe.utils import cint

SHEET_CSV_URL = (
	"https://docs.google.com/spreadsheets/d/1oiF3DmiQz0oS3kxV8Ld0gc3IKfLIacwDVJGqgk8jG5A"
	"/export?format=csv&gid=184185565"
)
SHEET_GVIZ_URL = (
	"https://docs.google.com/spreadsheets/d/1oiF3DmiQz0oS3kxV8Ld0gc3IKfLIacwDVJGqgk8jG5A"
	"/gviz/tq?tqx=out:csv&gid=184185565"
)

LOCAL_CSV = os.path.join(
	os.path.dirname(os.path.dirname(__file__)),
	"data",
	"atn_asl_customers.csv",
)


@frappe.whitelist()
def replace_demo_customers(dry_run=True, confirm_site=None, source="auto", commit_every=50):
	"""Create/update Customers from the sheet. Does not delete customers missing from the sheet."""
	frappe.only_for("System Manager")
	dry_run = frappe.utils.cint(dry_run)
	site = frappe.local.site
	if not dry_run and confirm_site != site:
		frappe.throw(
			f"Pass confirm_site='{site}' to upsert customers on this site. "
			"Live run refused without an explicit matching site name."
		)

	rows = _load_rows(source)
	incoming = _normalize_rows(rows)
	field_map = _customer_field_map()
	unloco_field = field_map["unloco_field"]
	code_fields = field_map["code_fields"]
	default_cg = _resolve_customer_group("")
	default_territory = _default_territory()

	for row in incoming:
		row["existing_name"] = _find_customer(row["code"], code_fields)

	to_create = [r for r in incoming if not r["existing_name"]]
	to_update = [r for r in incoming if r["existing_name"]]
	missing_unloco = sorted(
		{
			r["unloco"]
			for r in incoming
			if r["unloco"] and not frappe.db.exists("UNLOCO", r["unloco"])
		}
	)

	print(f"Site: {site}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
	print(f"UNLOCO field: {unloco_field or '(none)'}")
	print(f"Code fields: {code_fields}")
	print(f"Default Customer Group (leaf): {default_cg}")
	print(f"Default Territory: {default_territory}")
	print(f"Sheet rows after dedupe: {len(incoming)}")
	print(f"Create: {len(to_create)}")
	print(f"Update: {len(to_update)}")
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
			"missing_unloco": missing_unloco,
		}

	frappe.set_user("Administrator")
	frappe.flags.ignore_links = True

	created = updated = 0
	failed = []
	for i, row in enumerate(incoming, 1):
		try:
			if _upsert_customer(row, unloco_field, code_fields, default_cg, default_territory):
				created += 1
			else:
				updated += 1
		except Exception as e:
			failed.append((row["code"], str(e)[:240]))
			print(f"  FAIL {row['code']}: {e}")
		if i % commit_every == 0:
			frappe.db.commit()
			print(f"  ... {i}/{len(incoming)} (created {created}, updated {updated}, failed {len(failed)})")
	frappe.db.commit()
	frappe.clear_cache(doctype="Customer")

	print(f"\nCreated: {created}")
	print(f"Updated: {updated}")
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
		"failed": failed,
		"missing_unloco": missing_unloco,
	}


def _load_rows(source):
	errors = []
	if source in ("auto", "google"):
		for url in (SHEET_CSV_URL, SHEET_GVIZ_URL):
			try:
				print(f"Fetching {url}")
				req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
				with urllib.request.urlopen(req, timeout=120) as resp:
					raw = resp.read().decode("utf-8-sig")
				if "Customer Name" in raw:
					return list(csv.DictReader(io.StringIO(raw)))
				errors.append(f"{url} was not a CSV")
			except Exception as e:
				errors.append(f"Google fetch failed ({url}): {e}")
		if source == "google":
			frappe.throw(" | ".join(errors))

	if source in ("auto", "local"):
		if os.path.exists(LOCAL_CSV):
			print(f"Reading {LOCAL_CSV}")
			with open(LOCAL_CSV, newline="", encoding="utf-8-sig") as f:
				return list(csv.DictReader(f))
		errors.append(f"Local CSV not found: {LOCAL_CSV}")

	frappe.throw("Could not load Customer sheet. " + " | ".join(errors))


def _normalize_rows(rows):
	by_code = {}
	for raw in rows:
		code = (raw.get("ID") or raw.get("Code") or "").strip().upper()
		name = (raw.get("Customer Name") or "").strip()
		if not code or not name:
			continue
		unloco = (raw.get("Default UNLOCO") or "").strip().upper()
		row = {
			"code": code,
			"customer_name": name,
			"customer_type": (raw.get("Customer Type") or "Company").strip() or "Company",
			"unloco": unloco,
			"website": (raw.get("Website") or "").strip(),
			"email_id": (raw.get("Email Id") or raw.get("Email ID") or "").strip(),
			"mobile_no": (raw.get("Mobile No") or "").strip(),
			"disabled": cint(raw.get("Disabled") or 0),
			"customer_group": (raw.get("Customer Group") or "").strip(),
			"territory": (raw.get("Territory") or "").strip(),
			"primary_address_link": (raw.get("Customer Primary Address") or "").strip(),
		}
		prev = by_code.get(code)
		if not prev or (unloco and not prev["unloco"]):
			by_code[code] = row
	incoming = list(by_code.values())
	incoming.sort(key=lambda r: r["code"])
	return incoming


def _customer_field_map():
	meta = frappe.get_meta("Customer")
	unloco_field = None
	for fn in ("logistics_default_unloco", "default_unloco"):
		if meta.has_field(fn):
			unloco_field = fn
			break
	code_fields = []
	if meta.has_field("custom_code"):
		code_fields.append("custom_code")
	if meta.has_field("logistics_party_code"):
		code_fields.append("logistics_party_code")
	return {"unloco_field": unloco_field, "code_fields": code_fields}


def _customer_group_is_leaf(name):
	if not name or not frappe.db.exists("Customer Group", name):
		return False
	return not cint(frappe.db.get_value("Customer Group", name, "is_group"))


def _resolve_customer_group(preferred):
	if _customer_group_is_leaf(preferred):
		return preferred
	default = frappe.db.get_default("Customer Group")
	if _customer_group_is_leaf(default):
		return default
	for fb in ("Commercial", "Individual", "Government", "Non Profit"):
		if _customer_group_is_leaf(fb):
			return fb
	leaf = frappe.get_all(
		"Customer Group",
		filters={"is_group": 0},
		pluck="name",
		limit=1,
		order_by="name asc",
	)
	if leaf:
		return leaf[0]
	frappe.throw("No non-group Customer Group found. Create a leaf Customer Group first.")


def _default_territory():
	d = frappe.db.get_default("Territory")
	if d and frappe.db.exists("Territory", d):
		return d
	for fb in ("All Territories", "Rest Of The World"):
		if frappe.db.exists("Territory", fb):
			return fb
	names = frappe.get_all("Territory", pluck="name", limit=1)
	if not names:
		frappe.throw("No Territory found on site.")
	return names[0]


def _find_customer(code, code_fields):
	if frappe.db.exists("Customer", code):
		return code
	for fn in code_fields:
		names = frappe.get_all(
			"Customer",
			filters=[[fn, "=", code]],
			pluck="name",
			limit=1,
		)
		if names:
			return names[0]
	return None


def _set_code_fields(doc, code, code_fields):
	for fn in code_fields:
		doc.set(fn, code)


def _apply_row(doc, row, unloco_field, code_fields, default_cg, default_territory):
	doc.customer_name = row["customer_name"]
	doc.customer_type = row["customer_type"]
	doc.disabled = row["disabled"]

	cg = row["customer_group"] or default_cg
	if _customer_group_is_leaf(cg):
		doc.customer_group = cg

	terr = row["territory"] or default_territory
	if terr and frappe.db.exists("Territory", terr):
		doc.territory = terr

	_set_code_fields(doc, row["code"], code_fields)

	if unloco_field:
		if row["unloco"] and frappe.db.exists("UNLOCO", row["unloco"]):
			doc.set(unloco_field, row["unloco"])
		elif not row["unloco"]:
			doc.set(unloco_field, None)

	if row["website"]:
		doc.website = row["website"] if "://" in row["website"] else f"http://{row['website']}"
	if row["email_id"]:
		doc.email_id = row["email_id"]
	if row["mobile_no"]:
		doc.mobile_no = row["mobile_no"]

	addr = row["primary_address_link"]
	if addr and frappe.db.exists("Address", addr):
		doc.customer_primary_address = addr


def _upsert_customer(row, unloco_field, code_fields, default_cg, default_territory):
	existing = row.get("existing_name") or _find_customer(row["code"], code_fields)
	if existing:
		doc = frappe.get_doc("Customer", existing)
		_apply_row(doc, row, unloco_field, code_fields, default_cg, default_territory)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = True
		doc.save()
		if doc.name != row["code"]:
			frappe.rename_doc("Customer", doc.name, row["code"], force=True)
		return False

	doc = frappe.new_doc("Customer")
	doc.customer_group = default_cg
	doc.territory = default_territory
	_apply_row(doc, row, unloco_field, code_fields, default_cg, default_territory)
	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	doc.insert()
	if doc.name != row["code"]:
		frappe.rename_doc("Customer", doc.name, row["code"], force=True)
	return True
