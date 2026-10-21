# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Declaration Type values shared by Sales Quote, Declaration Order, and Declaration.

``Application`` is a permit-application-only job: the Declaration still exists,
and saving it opens one Permit Application. Shipper and Consignee are optional
on that job.
"""

from __future__ import annotations

APPLICATION_DECLARATION_TYPE = "Application"

DECLARATION_TYPE_OPTIONS = (
	"Import",
	"Export",
	"Transit",
	"Bonded",
	APPLICATION_DECLARATION_TYPE,
)

DECLARATION_TYPE_SELECT = "\n".join(DECLARATION_TYPE_OPTIONS)

PERMIT_APPLICATION_ONLY_TYPE_CODE = "PERMIT-APPLICATION-ONLY"
PERMIT_APPLICATION_ONLY_TYPE_NAME = "Permit application only"
PERMIT_APPLICATION_ONLY_TEMPLATE = "Permit application only"

PERMIT_APPLICATION_ONLY_TASKS = (
	{
		"task_code": "PREPARE_PERMIT",
		"subject": "Prepare permit application",
		"description": "Collect the documents and party details for the permit application.",
		"sequence": 10,
		"is_required": 1,
	},
	{
		"task_code": "FILE_PERMIT",
		"subject": "File permit application",
		"description": "File the permit application with the issuing authority.",
		"sequence": 20,
		"is_required": 1,
	},
	{
		"task_code": "TRACK_PERMIT",
		"subject": "Track permit application",
		"description": "Track the application until it is approved or rejected.",
		"sequence": 30,
		"is_required": 1,
	},
	{
		"task_code": "CLOSE_PERMIT_JOB",
		"subject": "Close permit application job",
		"description": "Close the job after the permit decision and billing checks.",
		"sequence": 40,
		"is_required": 1,
	},
)


def is_permit_application_only(declaration_type) -> bool:
	"""True when this Declaration Type runs a permit application only job."""
	return (declaration_type or "").strip() == APPLICATION_DECLARATION_TYPE


def optional_party_from_dialog(explicit, fallback, application: bool):
	"""Party chosen in the create dialog.

	Omitted values keep the Sales Quote party. A cleared value on an Application
	job leaves Shipper or Consignee blank. Other declaration types still fall back.
	"""
	if explicit is None:
		return fallback or None
	explicit = str(explicit).strip()
	if explicit:
		return explicit
	if application:
		return None
	return fallback or None


def parties_optional(declaration_type, main_service=None) -> bool:
	"""Shipper and Consignee are optional on an Application customs job.

	``main_service`` is set on Sales Quote. Leave it empty on Declaration and
	Declaration Order, which are always customs documents.
	"""
	if not is_permit_application_only(declaration_type):
		return False
	service = (main_service or "").strip()
	if not service:
		return True
	return service in ("Customs", "Custom")
