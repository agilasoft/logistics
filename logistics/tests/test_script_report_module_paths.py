# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Script reports must live where Frappe imports them.

`Report.get_module_method` loads
`{app}.{scrub(module)}.report.{scrub(report_name)}.{scrub(report_name)}`.
A folder left behind after a report rename raises ModuleNotFoundError.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]

ON_TIME_REPORTS = {
	"Sea Freight On-Time Performance Report": (
		"sea_freight",
		"sea_freight_on_time_performance_report",
	),
	"Air Freight On-Time Performance Report": (
		"air_freight",
		"air_freight_on_time_performance_report",
	),
}


def scrub(txt: str) -> str:
	"""Match frappe.scrub: spaces and hyphens become underscores."""
	return str(txt or "").replace(" ", "_").replace("-", "_").lower()


def script_reports():
	for path in PACKAGE.rglob("report/*/*.json"):
		data = json.loads(path.read_text())
		if data.get("doctype") == "Report" and data.get("report_type") == "Script Report":
			yield path, data


class TestScriptReportModulePaths(unittest.TestCase):
	def test_script_report_files_match_scrubbed_name(self):
		mismatches = []
		for path, data in script_reports():
			name = data.get("name") or data.get("report_name")
			expected = scrub(name)
			if path.parent.name != expected or path.stem != expected:
				mismatches.append(f"{name}: {path.relative_to(PACKAGE)}")
				continue
			controller = path.with_suffix(".py")
			if not controller.is_file():
				mismatches.append(f"{name}: missing {controller.name}")
		self.assertEqual(mismatches, [])

	def test_on_time_performance_reports_are_importable_paths(self):
		for report_name, (module, folder) in ON_TIME_REPORTS.items():
			directory = PACKAGE / module / "report" / folder
			self.assertTrue(directory.is_dir(), report_name)
			for suffix in (".py", ".js", ".json"):
				self.assertTrue((directory / f"{folder}{suffix}").is_file(), f"{report_name} {suffix}")
			payload = json.loads((directory / f"{folder}.json").read_text())
			self.assertEqual(payload["name"], report_name)
			self.assertEqual(payload["report_type"], "Script Report")


if __name__ == "__main__":
	unittest.main()
