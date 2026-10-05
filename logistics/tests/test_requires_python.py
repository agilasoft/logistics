# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""CargoNext installs on the Python version Frappe v16 requires."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from packaging.specifiers import SpecifierSet


ROOT = Path(__file__).resolve().parents[2]


def _requires_python(pyproject):
	data = tomllib.loads((ROOT / pyproject).read_text())
	return SpecifierSet(data["project"]["requires-python"])


class TestRequiresPython(unittest.TestCase):
	def test_logistics_accepts_python_3_14(self):
		spec = _requires_python("pyproject.toml")
		self.assertTrue(spec.contains("3.14"))
		self.assertTrue(spec.contains("3.14.2"))
		self.assertFalse(spec.contains("3.12"))
		self.assertFalse(spec.contains("3.13"))
		self.assertFalse(spec.contains("3.15"))

	def test_workflow_center_accepts_python_3_14(self):
		spec = _requires_python("workflow_center/pyproject.toml")
		self.assertTrue(spec.contains("3.14"))
		self.assertFalse(spec.contains("3.12"))


if __name__ == "__main__":
	unittest.main()
