# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Push catalog-driven CNX management reports into the site database.

Generated ``Report`` JSON under each module's ``report/`` tree is not always
imported during ``bench migrate`` (timestamp skips, deploy order). This hook
re-imports those files so reports appear in **Report** list, Awesome Bar, and
DocType **Go to > Report** menus.
"""

from __future__ import unicode_literals

from pathlib import Path

import frappe
from frappe.modules.import_file import import_file_by_path

from logistics.analytics_reports.catalog import REPORTS_BY_MODULE, f_scrub
from logistics.patches.build_cnx_analytics_reports import MODULES


def _iter_report_json_paths():
	pkg_root = Path(frappe.get_app_path("logistics"))
	for _mod_label, subdir in MODULES:
		for row in REPORTS_BY_MODULE[_mod_label]:
			title = row[0]
			folder = f_scrub(title)
			p = pkg_root / subdir / "report" / folder / (folder + ".json")
			if p.is_file():
				yield p


def sync_cnx_management_reports(force=True):
	"""Import each CNX management report from disk. ``force=True`` matches standard doc sync."""
	n = 0
	for path in _iter_report_json_paths():
		if import_file_by_path(str(path), force=force):
			n += 1
	if n:
		frappe.db.commit()
	return n


def after_migrate():
	"""Ensure CNX KPI Script Reports exist and match shipped JSON (incl. roles, filters)."""
	sync_cnx_management_reports(force=True)
