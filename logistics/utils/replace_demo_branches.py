# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Replace Branch masters on demo.cargonext.io from the ATN/ASL master sheet.

    bench --site logistics.agilasoft.com execute logistics.utils.replace_demo_branches.run --kwargs '{"dry_run": true}'
    bench --site logistics.agilasoft.com execute logistics.utils.replace_demo_branches.run --kwargs '{"dry_run": false}'
"""

from __future__ import annotations

import re

import frappe
from frappe.model.rename_doc import get_link_fields

# ID, display name, company, tax id, registration details, branch code
SHEET_BRANCHES = [
	{
		"name": "PAHMBC",
		"branch": "Mabalacat (PAH)",
		"company": "PRIME ALTA HOLDINGS, INC.",
		"tax_id": "010-706-356-00000",
		"registration": "2nd floor Baronesa Place, Mc Arthur Highway, Dau, Mabalacat City, Pampanga Philippines 2010",
		"code": "MBC",
	},
	{
		"name": "PBSILN",
		"branch": "Batac (PBS)",
		"company": "PRIME HUB BUSINESS SERVICES",
		"tax_id": "010-772-443-00000",
		"registration": "10 Lacub, Lacub (POB), City of Batac,Ilocos Norte, Region 1, 2906",
		"code": "ILN",
	},
	{
		"name": "FPTPNS",
		"branch": "Las Pinas (FPT)",
		"company": "FAST PRIME TRANSPORT CORP.",
		"tax_id": "010-767-380-00000",
		"registration": "LOT 1,2,3,J, Tiongquiao St., Bondoc Compound, Manuyo Dos, City of Las Pinas 1744",
		"code": "PNS",
	},
	{
		"name": "AFEPPA",
		"branch": "Paranaque (AFE)",
		"company": "ALTA FAIRS AND EXHIBITS CORP.",
		"tax_id": "010-785-624-00000",
		"registration": "#3 Sta. Agueda Avenue, Pascor Drive, Santo. Nino, Paranaque City 1700",
		"code": "PPA",
	},
	{
		"name": "TPOILN",
		"branch": "Batac (TPO)",
		"company": "THE PEAK ONE HOLDINGS INC.",
		"tax_id": "601-582-332-00000",
		"registration": "",
		"code": "ILN",
	},
	{
		"name": "AGSMBC",
		"branch": "Mabalacat (AGS)",
		"company": "ALTA GLOBAL SERVICES, INC",
		"tax_id": "008-914-631-00000",
		"registration": "",
		"code": "MBC",
	},
	{
		"name": "MTEQZT",
		"branch": "Quezon City (MTE)",
		"company": "MTE PROPERTIES, INC.",
		"tax_id": "202-137-531-00000",
		"registration": "",
		"code": "QZT",
	},
	{
		"name": "ATNSUB",
		"branch": "Subic (ATN)",
		"company": "ALL TRANSPORT NETWORK, INC.",
		"tax_id": "000-414-368-00000",
		"registration": "All Transport Network, Inc.Unit 1-3A Subic Creative Center Building, Manila Avenue Cor. Dewey Avenue, Central Business District, Subic Bay 2222 Freeport Zone, Zambales Philippines",
		"code": "SUB",
	},
	{
		"name": "ATNGES",
		"branch": "General Santos (ATN)",
		"company": "ALL TRANSPORT NETWORK, INC.",
		"tax_id": "000-414-368-00000",
		"registration": "All Transport Network, Inc.2nd Floor, JMP Building 3, National Highway, Purok San Roque, Labangal, General Santos City, 9500, Philippines",
		"code": "GES",
	},
	{
		"name": "ATNBTN",
		"branch": "Bataan (ATN)",
		"company": "ALL TRANSPORT NETWORK, INC.",
		"tax_id": "000-414-368-00000",
		"registration": "All Transport Network, Inc.2nd Floor, RCBC Building, Authority of the Freeport Area of Bataan (AFAB), Mariveles, Bataan, 2105",
		"code": "BTN",
	},
	{
		"name": "ATNDVO",
		"branch": "Davao (ATN)",
		"company": "ALL TRANSPORT NETWORK, INC.",
		"tax_id": "000-414-368-00000",
		"registration": "All Transport Network, Inc.3 & 4 Pasalubong Airport View Building, Stall No. 6, CPG Highway, Buhangin, Davao City, Philippines",
		"code": "DVO",
	},
	{
		"name": "ATNPPA",
		"branch": "Paranaque (ATN)",
		"company": "ALL TRANSPORT NETWORK, INC.",
		"tax_id": "000-414-368-00012",
		"registration": "All Transport Network, Inc.3 Sta. Agueda Avenue, Pascor Drive, Sto. Nino, 170 City of Paranaque, NCR Fourth District, Philippines",
		"code": "PPA",
	},
	{
		"name": "ATNCEB",
		"branch": "Cebu (ATN)",
		"company": "ALL TRANSPORT NETWORK, INC.",
		"tax_id": "000-414-368-00001",
		"registration": "All Transport Network, Inc.Unit 5 Jabbe Properties Inc. Marciano Quizon St.Alang-alang, Mandaue City, Cebu, Philippines 6014",
		"code": "CEB",
	},
	{
		"name": "AGSPPA",
		"branch": "Paranaque (AGS)",
		"company": "ALTA GLOBAL SERVICES, INC",
		"tax_id": "008-914-631-00001",
		"registration": "",
		"code": "PPA",
	},
	{
		"name": "ASLMNL",
		"branch": "Paranaque (ASL)",
		"company": "ALL SYSTEMS LOGISTICS INC.",
		"tax_id": "200-003-195-00001",
		"registration": "All Systems Logistics, Inc.3 Sta. Agueda Avenue, Pascor Drive, Sto. Nino, 170 City of Paranaque, NCR Fourth District, Philippines",
		"code": "MNL",
	},
	{
		"name": "ASLSUB",
		"branch": "Subic (ASL)",
		"company": "ALL SYSTEMS LOGISTICS INC.",
		"tax_id": "200-003-195-00000",
		"registration": "1-3 Subic Creative Centre Bldg., Manila Avenue corner Dewey Avenue,\nCentral Business District, Subic Bay Freeport Zone 2222\nVAT Re. TIN: 200-003-195-00000",
		"code": "SUB",
	},
	{
		"name": "PWDPNS",
		"branch": "Las Pinas (PWD)",
		"company": "PRIME WAREHOUSE DYNAMICS CORP.",
		"tax_id": "010-767-403-00000",
		"registration": "Lot 1,2,3 , J. Tionquiao St., Bondoc Compound, Manuyo Dos, 1744,\nCity Of Las Piñas,Fourth District, Philippines\nVAT Reg TIN: 010-767-403-00000",
		"code": "LPS",
	},
	{
		"name": "PWDPPA",
		"branch": "Paranaque (PWD)",
		"company": "PRIME WAREHOUSE DYNAMICS CORP.",
		"tax_id": "010-767-403-00000",
		"registration": "3 Sta. Agueda Ave. PASCOR Drive Metro Manila\nParanaque City, Philippines 1700\nVAT Reg TIN: 010-767-403-00000",
		"code": "PPA",
	},
]

# Main branch used when an old location code cannot be mapped more precisely.
COMPANY_DEFAULT_BRANCH = {
	"PRIME ALTA HOLDINGS, INC.": "PAHMBC",
	"PRIME HUB BUSINESS SERVICES": "PBSILN",
	"FAST PRIME TRANSPORT CORP.": "FPTPNS",
	"ALTA FAIRS AND EXHIBITS CORP.": "AFEPPA",
	"THE PEAK ONE HOLDINGS INC.": "TPOILN",
	"ALTA GLOBAL SERVICES, INC": "AGSPPA",
	"MTE PROPERTIES, INC.": "MTEQZT",
	"ALL TRANSPORT NETWORK, INC.": "ATNPPA",
	"ALL SYSTEMS LOGISTICS INC.": "ASLMNL",
	"PRIME WAREHOUSE DYNAMICS CORP.": "PWDPNS",
}

FALLBACK_BRANCH = "ATNPPA"

NAMING_RULE_BRANCH = {
	("AFE-PPA-", "PPA"): "AFEPPA",
	("AGS-MBC-", "MBC"): "AGSMBC",
	("AGS-PPA-", "PPA"): "AGSPPA",
	("ASL-MNL-", "MNL"): "ASLMNL",
	("ASL-SUB-", "SUB"): "ASLSUB",
	("ATN-BTN-", "BTN"): "ATNBTN",
	("ATN-CEB-", "CEB"): "ATNCEB",
	("ATN-DVO-", "DVO"): "ATNDVO",
	("ATN-GSN-", "GSN"): "ATNGES",
	("ATN-MNL-", "MNL"): "ATNPPA",
	("ATN-SUB-", "SUB"): "ATNSUB",
	("FPT-PNS-", "PNS"): "FPTPNS",
	("MTE-QUE-", "QUE"): "MTEQZT",
	("PAH-MBC-", "MBC"): "PAHMBC",
	("PBS-BTC-", "BTC"): "PBSILN",
	("PWC-PNS-", "PNS"): "PWDPNS",
	("TPO-BTC-", "BTC"): "TPOILN",
}

NAMING_RULE_COMPANY = {
	"Alta Fairs and Exhibits Corp.": "ALTA FAIRS AND EXHIBITS CORP.",
	"Alta Global Services, Inc.": "ALTA GLOBAL SERVICES, INC",
	"All Systems Logistics": "ALL SYSTEMS LOGISTICS INC.",
	"All Sytems Logistics": "ALL SYSTEMS LOGISTICS INC.",
	"All Transport Network": "ALL TRANSPORT NETWORK, INC.",
	"Fast Prime Transport Corp.": "FAST PRIME TRANSPORT CORP.",
	"MTE Properties, Inc.": "MTE PROPERTIES, INC.",
	"Prime Alta Holdings, Inc.": "PRIME ALTA HOLDINGS, INC.",
	"Prime Hub Business Services": "PRIME HUB BUSINESS SERVICES",
	"Prime Warehouse Dynamics Corp.": "PRIME WAREHOUSE DYNAMICS CORP.",
	"The Peak One Holdings Inc.": "THE PEAK ONE HOLDINGS INC.",
}


def run(dry_run=True):
	keep = [row["name"] for row in SHEET_BRANCHES]
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")

	_ensure_companies(keep)
	_upsert_branches(dry_run=dry_run)
	_update_naming_rules(dry_run=dry_run)
	_sync_company_branches(dry_run=dry_run)
	_remap_and_delete_old(keep, dry_run=dry_run)
	_set_settings_defaults(dry_run=dry_run)

	if dry_run:
		print("\nDry run only. Run again with dry_run=False to apply.")
		return {"keep": keep, "dry_run": True}

	frappe.db.commit()
	frappe.clear_cache()
	print("\nDone.")
	return {"keep": keep, "dry_run": False}


def _ensure_companies(_keep=None):
	missing = [
		row["company"]
		for row in SHEET_BRANCHES
		if not frappe.db.exists("Company", row["company"])
	]
	if missing:
		frappe.throw("These companies do not exist: " + ", ".join(sorted(set(missing))))


def _upsert_branches(dry_run=True):
	print("\nUpsert Branch records:")
	for row in SHEET_BRANCHES:
		registration = _clean_registration(row["registration"], row["code"])
		if frappe.db.exists("Branch", row["name"]):
			print(f"  update {row['name']} ({row['branch']})")
			if dry_run:
				continue
			frappe.db.set_value(
				"Branch",
				row["name"],
				{
					"branch": row["branch"],
					"custom_company": row["company"],
					"custom_tax_id": row["tax_id"],
					"custom_registration_details": registration,
				},
				update_modified=True,
			)
			_set_branch_code(row["name"], row["code"])
			continue

		print(f"  create {row['name']} ({row['branch']})")
		if dry_run:
			continue
		doc = frappe.new_doc("Branch")
		doc.name = row["name"]
		doc.branch = row["branch"]
		doc.custom_company = row["company"]
		doc.custom_tax_id = row["tax_id"]
		doc.custom_registration_details = registration
		doc.insert(ignore_permissions=True)
		_set_branch_code(row["name"], row["code"])


def _set_branch_code(name, code):
	if code and frappe.db.has_column("Branch", "custom_branch_code"):
		frappe.db.set_value("Branch", name, "custom_branch_code", code, update_modified=False)


def _clean_registration(text, code):
	text = (text or "").replace("\r\n", "\n")
	text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
	text = re.sub(r"[ \t]+\n", "\n", text).strip()
	if not text:
		return ""
	if text.upper() == (code or "").upper():
		return ""
	if len(text) <= 3:
		return ""
	return text


def _naming_rule_branch(prefix, old_value):
	for (stem, old), new in NAMING_RULE_BRANCH.items():
		if prefix.startswith(stem) and old_value == old:
			return new
	return None


def _update_naming_rules(dry_run=True):
	print("\nUpdate Document Naming Rule conditions:")
	rules = frappe.get_all(
		"Document Naming Rule",
		fields=["name", "prefix"],
	)
	for rule in rules:
		conditions = frappe.get_all(
			"Document Naming Rule Condition",
			filters={"parent": rule.name},
			fields=["name", "field", "value"],
		)
		for cond in conditions:
			new_value = None
			if cond.field == "branch":
				new_value = _naming_rule_branch(rule.prefix, cond.value)
			elif cond.field == "company":
				new_value = NAMING_RULE_COMPANY.get(cond.value)
			if not new_value or new_value == cond.value:
				continue
			print(f"  {rule.prefix} {cond.field}: {cond.value} -> {new_value}")
			if not dry_run:
				frappe.db.set_value(
					"Document Naming Rule Condition",
					cond.name,
					"value",
					new_value,
					update_modified=False,
				)


def _sync_company_branches(dry_run=True):
	if not frappe.db.table_exists("Company Branches"):
		return
	keep = {row["name"] for row in SHEET_BRANCHES}
	print("\nSync Company Branches child table:")
	stale = frappe.get_all(
		"Company Branches",
		filters=[["branch", "not in", list(keep)]],
		fields=["name", "parent", "branch"],
	)
	for child in stale:
		print(f"  remove {child.parent} / {child.branch}")
		if not dry_run:
			frappe.delete_doc("Company Branches", child.name, ignore_permissions=True, force=1)
	for row in SHEET_BRANCHES:
		existing = frappe.db.get_value(
			"Company Branches",
			{"parent": row["company"], "branch": row["name"]},
			"name",
		)
		registration = _clean_registration(row["registration"], row["code"])
		if existing:
			print(f"  update {row['company']} / {row['name']}")
			if dry_run:
				continue
			frappe.db.set_value(
				"Company Branches",
				existing,
				{
					"registration_details": registration,
					"branch_tin": row["tax_id"],
				},
				update_modified=False,
			)
			continue
		print(f"  add {row['company']} / {row['name']}")
		if dry_run:
			continue
		idx = (
			frappe.db.sql(
				"""
				SELECT IFNULL(MAX(idx), 0) FROM `tabCompany Branches`
				WHERE parent = %s
				""",
				row["company"],
			)[0][0]
			+ 1
		)
		child = frappe.get_doc(
			{
				"doctype": "Company Branches",
				"parent": row["company"],
				"parenttype": "Company",
				"parentfield": "custom_company_branches",
				"idx": idx,
				"branch": row["name"],
				"registration_details": registration,
				"branch_tin": row["tax_id"],
			}
		)
		child.insert(ignore_permissions=True)


def _remap_and_delete_old(keep, dry_run=True):
	link_fields = get_link_fields("Branch")
	old_branches = [
		name for name in frappe.get_all("Branch", pluck="name") if name not in keep
	]
	print(f"\nOld branches to remove: {old_branches or '(none)'}")
	for old in old_branches:
		print(f"\n{old}:")
		_remap_old_branch(old, link_fields, dry_run=dry_run)
		if dry_run:
			print(f"  would delete Branch {old}")
			continue
		frappe.delete_doc("Branch", old, ignore_permissions=True, force=1)
		print(f"  deleted Branch {old}")


def _remap_old_branch(old, link_fields, dry_run=True):
	for lf in link_fields:
		dt = lf.parent
		fn = lf.fieldname
		if not dt or not fn or dt in ("Branch", "Company Branches") or not frappe.db.table_exists(dt):
			continue
		if int(lf.issingle or 0):
			_remap_single(dt, fn, old, dry_run=dry_run)
			continue
		_remap_table(dt, fn, old, dry_run=dry_run)

	if frappe.db.table_exists("Dynamic Link"):
		count = frappe.db.count(
			"Dynamic Link", {"link_doctype": "Branch", "link_name": old}
		)
		if count:
			print(f"  Dynamic Link: {count}")
			if not dry_run:
				rows = frappe.get_all(
					"Dynamic Link",
					filters={"link_doctype": "Branch", "link_name": old},
					fields=["name", "parenttype", "parent"],
				)
				for row in rows:
					company = _company_of(row.parenttype, row.parent)
					frappe.db.set_value(
						"Dynamic Link",
						row.name,
						"link_name",
						_target_for(old, company),
						update_modified=False,
					)

	if frappe.db.table_exists("User Permission"):
		count = frappe.db.count(
			"User Permission", {"allow": "Branch", "for_value": old}
		)
		if count:
			print(f"  User Permission: {count}")
			if not dry_run:
				frappe.db.delete(
					"User Permission", {"allow": "Branch", "for_value": old}
				)


def _remap_single(dt, fn, old, dry_run=True):
	try:
		current = frappe.db.get_single_value(dt, fn)
	except Exception:
		return
	if current != old:
		return
	target = _target_for(old, None)
	print(f"  {dt}.{fn}: {old} -> {target}")
	if not dry_run:
		frappe.db.set_single_value(dt, fn, target)


def _remap_table(dt, fn, old, dry_run=True):
	try:
		count = frappe.db.count(dt, {fn: old})
	except Exception:
		return
	if not count:
		return

	company_field = _company_field(dt)
	print(f"  {dt}.{fn}: {count}" + (f" (by {company_field})" if company_field else ""))
	if dry_run:
		return

	if not company_field:
		frappe.db.sql(
			f"UPDATE `tab{dt}` SET `{fn}` = %s WHERE `{fn}` = %s",
			(_target_for(old, None), old),
		)
		return

	companies = frappe.db.sql(
		f"SELECT DISTINCT `{company_field}` FROM `tab{dt}` WHERE `{fn}` = %s",
		old,
	)
	for (company,) in companies:
		target = _target_for(old, company)
		if company:
			frappe.db.sql(
				f"UPDATE `tab{dt}` SET `{fn}` = %s WHERE `{fn}` = %s AND `{company_field}` = %s",
				(target, old, company),
			)
		else:
			frappe.db.sql(
				f"UPDATE `tab{dt}` SET `{fn}` = %s WHERE `{fn}` = %s AND IFNULL(`{company_field}`, '') = ''",
				(target, old),
			)


def _company_field(dt):
	if frappe.db.has_column(dt, "company"):
		return "company"
	if frappe.db.has_column(dt, "custom_company"):
		return "custom_company"
	return None


def _company_of(dt, name):
	if not dt or not name or not frappe.db.table_exists(dt):
		return None
	field = _company_field(dt)
	if not field:
		return None
	try:
		return frappe.db.get_value(dt, name, field)
	except Exception:
		return None


def _target_for(old, company):
	if company and company in COMPANY_DEFAULT_BRANCH:
		return COMPANY_DEFAULT_BRANCH[company]
	if old in ("Las Pinas", "PNS"):
		return "FPTPNS"
	return FALLBACK_BRANCH


def _set_settings_defaults(dry_run=True):
	keep = {row["name"] for row in SHEET_BRANCHES}
	print("\nSettings defaults ->", FALLBACK_BRANCH)
	for dt in (
		"Air Freight Settings",
		"Sea Freight Settings",
		"Customs Settings",
	):
		if not frappe.db.table_exists(dt) or not frappe.db.has_column(dt, "default_branch"):
			continue
		current = frappe.db.get_single_value(dt, "default_branch")
		if current in keep:
			continue
		print(f"  {dt}.default_branch: {current} -> {FALLBACK_BRANCH}")
		if not dry_run:
			frappe.db.set_single_value(dt, "default_branch", FALLBACK_BRANCH)
