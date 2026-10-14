# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Workflow Center actions must be buttons that apply the workflow transition."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_suffix(".js")


class TestWorkflowCenterActionButtons(unittest.TestCase):
	def test_actions_render_as_buttons_and_apply_workflow(self):
		result = subprocess.run(
			["node", str(SCRIPT)],
			cwd=ROOT,
			check=False,
			capture_output=True,
			text=True,
		)
		self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
		self.assertIn("workflow center action buttons apply the workflow", result.stdout)
		self.assertNotIn("<img", result.stdout)


if __name__ == "__main__":
	unittest.main()
