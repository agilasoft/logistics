# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Virtual read-only fields on customs child tables backed by linked master docs."""

import frappe
from frappe.utils import strip_html

_PA_VALUE_FIELDS = (
	"permit_type",
	"status",
	"approval_date",
	"valid_to",
	"permit_number",
	"notes",
)


class PermitRequirementVirtualMixin:
	"""Mirror Permit Application on permit requirement rows (Declaration / Declaration Order)."""

	def _permit_application_row(self):
		pa = self.get("permit_application")
		cache = self.__dict__.get("_pa_row_cache")
		if isinstance(cache, dict) and cache.get("link") == pa:
			return cache.get("row")
		if not pa:
			self.__dict__["_pa_row_cache"] = {"link": pa, "row": None}
			return None
		row = frappe.db.get_value("Permit Application", pa, list(_PA_VALUE_FIELDS), as_dict=True)
		self.__dict__["_pa_row_cache"] = {"link": pa, "row": row}
		return row

	@property
	def permit_type(self):
		row = self._permit_application_row()
		return row.get("permit_type") if row else None

	@property
	def status(self):
		row = self._permit_application_row()
		return row.get("status") if row else None

	@property
	def is_obtained(self):
		row = self._permit_application_row()
		if not row or not row.get("status"):
			return 0
		return 1 if row.get("status") in ("Approved", "Renewed") else 0

	@property
	def obtained_date(self):
		row = self._permit_application_row()
		return row.get("approval_date") if row else None

	@property
	def expiry_date(self):
		row = self._permit_application_row()
		return row.get("valid_to") if row else None

	@property
	def permit_number(self):
		row = self._permit_application_row()
		return row.get("permit_number") if row else None

	@property
	def notes(self):
		row = self._permit_application_row()
		raw = row.get("notes") if row else None
		if not raw:
			return None
		stripped = strip_html(raw)
		return stripped if stripped else None


_CERT_VALUE_FIELDS = ("exemption_type", "certificate_number")


class ExemptionCertificateVirtualMixin:
	"""Mirror Exemption Certificate (+ type percentage) on declaration exemption rows."""

	def _exemption_certificate_row(self):
		ec = self.get("exemption_certificate")
		cache = self.__dict__.get("_ec_row_cache")
		if isinstance(cache, dict) and cache.get("link") == ec:
			return cache.get("row")
		if not ec:
			self.__dict__["_ec_row_cache"] = {"link": ec, "row": None}
			return None
		row = frappe.db.get_value("Exemption Certificate", ec, list(_CERT_VALUE_FIELDS), as_dict=True)
		self.__dict__["_ec_row_cache"] = {"link": ec, "row": row}
		return row

	@property
	def exemption_type(self):
		row = self._exemption_certificate_row()
		return row.get("exemption_type") if row else None

	@property
	def certificate_number(self):
		row = self._exemption_certificate_row()
		return row.get("certificate_number") if row else None

	@property
	def exemption_percentage(self):
		row = self._exemption_certificate_row()
		if not row or not row.get("exemption_type"):
			return None
		return frappe.db.get_value("Exemption Type", row["exemption_type"], "exemption_percentage")
