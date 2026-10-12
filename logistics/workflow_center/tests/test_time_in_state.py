# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Time in state must show the relative time, not the frappe-timestamp markup."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_suffix(".js")


class TestTimeInState(unittest.TestCase):
	def test_comment_when_html_is_rendered_as_text(self):
		result = subprocess.run(
			["node", str(SCRIPT)],
			cwd=ROOT,
			check=False,
			capture_output=True,
			text=True,
		)
		self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
		self.assertIn("1 hour ago", result.stdout)
		self.assertNotIn("&lt;span", result.stdout)


if __name__ == "__main__":
	unittest.main()
