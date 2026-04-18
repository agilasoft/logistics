# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Regenerate CNX management KPI Script Reports from ``analytics_reports.catalog``.

Each report module calls ``run_management_report(ref_doctype, handler_id, filters, options)``.
Run from bench:  bench --site all execute logistics.patches.build_cnx_analytics_reports.build
Or:  python3 -m logistics.patches.build_cnx_analytics_reports  (from apps/logistics)
"""

from __future__ import unicode_literals

import json
import re
import shutil
from pathlib import Path

from logistics.analytics_reports.catalog import REPORTS_BY_MODULE, f_scrub

# (module label, subdir under inner logistics/) — ref_doctype is taken from the catalog per report.
MODULES = [
	("Logistics", "logistics"),
	("Transport", "transport"),
	("Warehousing", "warehousing"),
	("Customs", "customs"),
	("Global Customs", "global_customs"),
	("Sea Freight", "sea_freight"),
	("Air Freight", "air_freight"),
	("Job Management", "job_management"),
	("Pricing Center", "pricing_center"),
	("Sustainability", "sustainability"),
	("Netting", "netting"),
	("Special Projects", "special_projects"),
	("Intercompany", "intercompany"),
]

LEGACY_NUMERIC_RE = re.compile(r"^.+_analytics_\d{2}$")
MANIFEST_NAME = ".cnx_analytics_build_manifest.json"


def _cleanup_report_package(report_root: Path):
	"""Remove legacy ``*_analytics_##`` trees and any folder from the last manifest."""
	if not report_root.is_dir():
		return
	manifest_path = report_root / MANIFEST_NAME
	prev = []
	if manifest_path.exists():
		try:
			prev = json.loads(manifest_path.read_text(encoding="utf-8"))
		except Exception:
			prev = []
	for name in prev:
		p = report_root / name
		if p.is_dir():
			shutil.rmtree(p, ignore_errors=True)
	for child in list(report_root.iterdir()):
		if child.is_dir() and LEGACY_NUMERIC_RE.match(child.name):
			shutil.rmtree(child, ignore_errors=True)
	if manifest_path.exists():
		manifest_path.unlink()


def _write(pkg_root: Path, subdir: str, mod_label: str):
	if mod_label not in REPORTS_BY_MODULE:
		raise KeyError("No catalog rows for module {0!r}".format(mod_label))
	rows = REPORTS_BY_MODULE[mod_label]
	report_root = pkg_root / subdir / "report"
	report_root.mkdir(parents=True, exist_ok=True)
	if subdir == "global_customs":
		(pkg_root / "global_customs" / "__init__.py").touch(exist_ok=True)

	_cleanup_report_package(report_root)

	new_folders = []
	for title, ref_dt, handler_id, options in rows:
		folder = f_scrub(title)
		if not re.match(r"^[a-z0-9_]+$", folder or ""):
			raise ValueError("Report title scrubs to invalid folder: {0!r} -> {1!r}".format(title, folder))
		new_folders.append(folder)
		rdir = report_root / folder
		rdir.mkdir(parents=True, exist_ok=True)

		json_path = rdir / (folder + ".json")
		py_path = rdir / (folder + ".py")

		doc = {
			"add_total_row": 0,
			"add_translate_data": 0,
			"columns": [],
			"creation": "2026-04-14 00:00:00.000000",
			"disabled": 0,
			"docstatus": 0,
			"doctype": "Report",
			"filters": [
				{"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "width": "80"},
				{"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "width": "80"},
				{"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "width": "120"},
			],
			"idx": 0,
			"is_standard": "Yes",
			"letter_head": "",
			"letterhead": None,
			"modified": "2026-04-14 00:00:00.000000",
			"modified_by": "Administrator",
			"module": mod_label,
			"name": title,
			"owner": "Administrator",
			"prepared_report": 0,
			"ref_doctype": ref_dt,
			"report_name": title,
			"report_type": "Script Report",
			"timeout": 0,
		}
		json_path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")

		opts_literal = json.dumps(options, sort_keys=True, separators=(",", ":"))
		py_tpl = (
			"# -*- coding: utf-8 -*-\n"
			"# Copyright (c) 2026, Agilasoft and contributors\n"
			"# For license information, please see license.txt\n"
			"from __future__ import unicode_literals\n\n"
			"import json\n\n"
			"from logistics.analytics_reports.management_reports import run_management_report\n\n"
			'REF_DOCTYPE = {ref_dt!r}\n'
			'HANDLER_ID = {handler_id!r}\n'
			"OPTIONS = json.loads({opts_literal!r})\n\n\n"
			"def execute(filters=None):\n"
			"\treturn run_management_report(REF_DOCTYPE, HANDLER_ID, filters, OPTIONS)\n"
		).format(ref_dt=ref_dt, handler_id=handler_id, opts_literal=opts_literal)
		py_path.write_text(py_tpl, encoding="utf-8")

	(report_root / MANIFEST_NAME).write_text(
		json.dumps(sorted(new_folders), indent=1) + "\n",
		encoding="utf-8",
	)
	print("Wrote", len(rows), "reports under", report_root)


def build():
	here = Path(__file__).resolve()
	pkg_root = here.parents[1]
	for mod_label, subdir in MODULES:
		_write(pkg_root, subdir, mod_label)
	print("Done.")


if __name__ == "__main__":
	build()
