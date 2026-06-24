# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Run Internal Job persistence before Frappe link validation on desk saves."""

from __future__ import annotations


def apply_internal_job_link_validation_patch() -> None:
	"""Patch ``Document._validate_links`` so IJ docs materialise before link checks."""
	import frappe
	from frappe import _
	from frappe.exceptions import CancelledLinkError, LinkValidationError
	from frappe.model.document import Document

	from logistics.utils.internal_job_persistence import (
		prepare_internal_jobs_before_link_validation,
	)
	from logistics.utils.linked_service_compat import (
		filter_invalid_links_with_linked_service_compat,
	)

	if getattr(Document, "_logistics_ij_link_patch", False):
		return

	def _validate_links(self):
		prepare_internal_jobs_before_link_validation(self)
		if self.flags.ignore_links or self._action == "cancel":
			return

		invalid_links, cancelled_links = self.get_invalid_links()

		for child in self.get_all_children():
			child_invalid, child_cancelled = child.get_invalid_links(
				is_submittable=self.meta.is_submittable
			)
			invalid_links.extend(child_invalid)
			cancelled_links.extend(child_cancelled)

		invalid_links = filter_invalid_links_with_linked_service_compat(invalid_links)

		if invalid_links:
			msg = ", ".join(each[2] for each in invalid_links)
			frappe.throw(_("Could not find {0}").format(msg), LinkValidationError)

		if cancelled_links:
			msg = ", ".join(each[2] for each in cancelled_links)
			frappe.throw(
				_("Cannot link cancelled document: {0}").format(msg),
				CancelledLinkError,
			)

	Document._validate_links = _validate_links
	Document._logistics_ij_link_patch = True
