# Copyright (c) 2026, Agilasoft and contributors
# See license.txt

"""Regression for GitHub #1472 — Frappe save() must not receive ignore_mandatory kwarg."""

from __future__ import annotations

import unittest


class _Frappe16SaveStub:
	"""Minimal mirror of frappe.model.document.Document save/_save signatures."""

	def save(self, *args, **kwargs):
		return self._save(*args, **kwargs)

	def _save(self, ignore_permissions=None, ignore_version=None):
		return self


class TestSeaBookingCreateFromQuoteSaveKwargs(unittest.TestCase):
	def test_save_rejects_ignore_mandatory_kwarg(self):
		doc = _Frappe16SaveStub()
		with self.assertRaises(TypeError):
			doc.save(ignore_permissions=True, ignore_mandatory=True)

	def test_save_accepts_ignore_permissions_only(self):
		doc = _Frappe16SaveStub()
		doc.save(ignore_permissions=True)


if __name__ == "__main__":
	unittest.main()
