# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Script Report files must live where Frappe imports them.

Opening a report calls
``{app}.{scrub(module)}.report.{scrub(report_name)}.{scrub(report_name)}.execute``.
A folder that still uses a shorter name raises ModuleNotFoundError.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]


def scrub(txt: str) -> str:
	"""Match ``frappe.utils.scrub`` for report and module names."""
	return txt.replace(" ", "_").replace("-", "_").lower()


def script_report_mismatches():
	mismatches = []
	for path in sorted(PACKAGE.rglob("report/*/*.json")):
		data = json.loads(path.read_text())
		if data.get("doctype") != "Report" or data.get("report_type") != "Script Report":
			continue
		name = data.get("name") or data.get("report_name") or ""
		expected = scrub(name)
		folder = path.parent
		problems = []
		if folder.name != expected:
			problems.append(f"folder {folder.name}")
		if path.stem != expected:
			problems.append(f"json {path.name}")
		if not (folder / f"{expected}.py").is_file():
			problems.append(f"missing {expected}.py")
		javascript = list(folder.glob("*.js"))
		if javascript and not (folder / f"{expected}.js").is_file():
			problems.append(f"js {[item.name for item in javascript]}")
		if problems:
			mismatches.append(f"{name}: {', '.join(problems)}")
	return mismatches


class TestScriptReportModulePaths(unittest.TestCase):
	def test_script_report_files_match_scrubbed_report_name(self):
		self.assertEqual(script_report_mismatches(), [])

	def test_on_time_performance_reports_use_freight_prefixes(self):
		air = (
			PACKAGE
			/ "air_freight"
			/ "report"
			/ "air_freight_on_time_performance_report"
			/ "air_freight_on_time_performance_report.py"
		)
		sea = (
			PACKAGE
			/ "sea_freight"
			/ "report"
			/ "sea_freight_on_time_performance_report"
			/ "sea_freight_on_time_performance_report.py"
		)
		self.assertTrue(air.is_file())
		self.assertTrue(sea.is_file())
		self.assertFalse((PACKAGE / "air_freight" / "report" / "on_time_performance_report").exists())
		self.assertFalse((PACKAGE / "sea_freight" / "report" / "on_time_performance_report").exists())


if __name__ == "__main__":
	unittest.main()
