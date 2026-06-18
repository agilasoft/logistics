# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Run Internal Job persistence before Frappe link validation on desk saves."""

from __future__ import annotations


def apply_internal_job_link_validation_patch() -> None:
	"""Patch ``Document._validate_links`` so IJ docs materialise before link checks."""
	from frappe.model.document import Document

	from logistics.utils.internal_job_persistence import (
		prepare_internal_jobs_before_link_validation,
	)

	if getattr(Document, "_logistics_ij_link_patch", False):
		return

	_original_validate_links = Document._validate_links

	def _validate_links(self):
		prepare_internal_jobs_before_link_validation(self)
		return _original_validate_links(self)

	Document._validate_links = _validate_links
	Document._logistics_ij_link_patch = True
