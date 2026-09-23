# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from logistics.utils.transport_template_rules import (
	apply_transport_template_defaults,
	clear_incompatible_load_vehicle_for_template,
	filter_load_types_for_transport_job_type,
	get_template_constraints,
	suggest_allowed_load_types_from_legs,
	validate_against_transport_template,
	validate_template_allowed_load_types_vs_legs,
	validate_template_defaults,
)


class TransportTemplate(Document):
	def validate(self):
		validate_template_allowed_load_types_vs_legs(self)
		validate_template_defaults(self)


@frappe.whitelist()
def get_transport_template_constraints(
	template_name: str,
	transport_job_type: str | None = None,
) -> dict:
	constraints = get_template_constraints(template_name)
	if transport_job_type:
		constraints["allowed_load_types"] = filter_load_types_for_transport_job_type(
			constraints.get("allowed_load_types") or [],
			transport_job_type,
		)
	return constraints


@frappe.whitelist()
def suggest_load_types_for_template_legs(legs_json: str | list | None = None) -> dict:
	import json

	if isinstance(legs_json, str):
		legs = json.loads(legs_json) if legs_json else []
	elif isinstance(legs_json, list):
		legs = legs_json
	else:
		legs = []

	suggested = suggest_allowed_load_types_from_legs(legs)
	return {"suggested_load_types": suggested}


def validate_doc_transport_template(
	doc: Document,
	*,
	template_field: str = "transport_template",
	load_type_field: str = "load_type",
	vehicle_type_field: str = "vehicle_type",
	context: str | None = None,
) -> None:
	template_name = getattr(doc, template_field, None)
	if not template_name:
		return

	validate_against_transport_template(
		template_name=template_name,
		load_type=getattr(doc, load_type_field, None),
		vehicle_type=getattr(doc, vehicle_type_field, None),
		context=context,
	)


def on_transport_template_selected(
	doc: Document,
	*,
	force_defaults: bool = False,
	template_field: str = "transport_template",
	load_type_field: str = "load_type",
	vehicle_type_field: str = "vehicle_type",
) -> None:
	clear_incompatible_load_vehicle_for_template(
		doc,
		template_field=template_field,
		load_type_field=load_type_field,
		vehicle_type_field=vehicle_type_field,
	)
	apply_transport_template_defaults(
		doc,
		template_field=template_field,
		load_type_field=load_type_field,
		vehicle_type_field=vehicle_type_field,
		force=force_defaults,
	)
