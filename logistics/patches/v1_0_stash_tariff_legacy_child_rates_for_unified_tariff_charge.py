# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Before Tariff child tables are dropped, copy legacy rate rows into a SQL stash for post_model_sync."""

import json

import frappe

STASH_TABLE = "_tariff_legacy_rates_stash"

LEGACY_TABLES = (
	"Air Freight Rate",
	"Sea Freight Rate",
	"Transport Rate",
	"Warehouse Rate",
	"Customs Rate",
)


def execute():
	frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{STASH_TABLE}`")

	has_any = False
	for dt in LEGACY_TABLES:
		if frappe.db.table_exists(f"tab{dt}"):
			cnt = frappe.db.sql(
				f"SELECT COUNT(*) FROM `tab{dt}` WHERE parenttype = 'Tariff'",
			)[0][0]
			if cnt:
				has_any = True
				break
	if not has_any:
		return

	frappe.db.sql_ddl(
		f"""
		CREATE TABLE `{STASH_TABLE}` (
			`name` varchar(140) NOT NULL,
			`parent_tariff` varchar(140) NOT NULL,
			`stash_idx` int(11) NOT NULL default 0,
			`source_dt` varchar(140) NOT NULL,
			`row_json` longtext,
			PRIMARY KEY (`name`),
			KEY `parent_idx` (`parent_tariff`, `stash_idx`)
		)
		"""
	)

	idx = 0
	for source_dt in LEGACY_TABLES:
		if not frappe.db.table_exists(f"tab{source_dt}"):
			continue
		rows = frappe.db.sql(
			f"SELECT * FROM `tab{source_dt}` WHERE parenttype = %(pt)s ORDER BY parent, idx",
			{"pt": "Tariff"},
			as_dict=True,
		)
		for r in rows:
			parent = r.get("parent")
			if not parent:
				continue
			stash_name = frappe.generate_hash(length=12)
			row_copy = {k: v for k, v in r.items()}
			frappe.db.sql(
				f"""
				INSERT INTO `{STASH_TABLE}` (`name`, `parent_tariff`, `stash_idx`, `source_dt`, `row_json`)
				VALUES (%(n)s, %(p)s, %(i)s, %(s)s, %(j)s)
				""",
				{
					"n": stash_name,
					"p": parent,
					"i": idx,
					"s": source_dt,
					"j": json.dumps(row_copy, default=str),
				},
			)
			idx += 1

	frappe.db.commit()
