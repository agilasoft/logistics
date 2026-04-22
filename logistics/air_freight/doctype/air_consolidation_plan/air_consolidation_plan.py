# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, get_time, getdate, today

from logistics.utils.consolidation_plan import (
	assert_air_plan_fields_for_strict_match,
	air_shipment_allowed_on_plan,
	conflicting_open_air_plan_line,
	get_strict_matching_air_shipment_names,
)


class AirConsolidationPlan(Document):
	def validate(self):
		self._validate_items()

	def _validate_items(self):
		seen = set()
		for row in self.get("items") or []:
			sh = row.air_shipment
			if not sh:
				continue
			if sh in seen:
				frappe.throw(_("Air Shipment {0} is duplicated in this plan.").format(sh))
			seen.add(sh)
			ok, msg = air_shipment_allowed_on_plan(sh)
			if not ok:
				frappe.throw(msg, title=_("Invalid Shipment"))
			origin = frappe.db.get_value("Air Shipment", sh, "origin_port")
			dest = frappe.db.get_value("Air Shipment", sh, "destination_port")
			if self.origin_airport and origin and origin != self.origin_airport:
				frappe.throw(
					_("Air Shipment {0} origin {1} does not match plan origin {2}.").format(
						sh, origin, self.origin_airport
					)
				)
			if self.destination_airport and dest and dest != self.destination_airport:
				frappe.throw(
					_("Air Shipment {0} destination {1} does not match plan destination {2}.").format(
						sh, dest, self.destination_airport
					)
				)
			if self.docstatus == 0 and conflicting_open_air_plan_line(sh, self.name if not self.is_new() else None):
				frappe.throw(
					_("Air Shipment {0} is already on another submitted consolidation plan (pending assignment).").format(
						sh
					),
					title=_("Consolidation Plan Conflict"),
				)

	def before_submit(self):
		if not self.get("items"):
			frappe.throw(_("Add at least one shipment before submitting the plan."), title=_("No Lines"))

	def before_cancel(self):
		for row in frappe.get_all(
			"Air Consolidation Plan Item",
			filters={"parent": self.name},
			fields=["linked_air_consolidation"],
		):
			if row.linked_air_consolidation:
				frappe.throw(
					_(
						"Cannot cancel: a line is linked to Air Consolidation {0}. Cancel the consolidation first or remove shipments."
					).format(row.linked_air_consolidation),
					title=_("Linked Consolidation"),
				)

	@frappe.whitelist()
	def fetch_matching_air_shipments(self):
		if self.is_new():
			frappe.throw(_("Save the plan before fetching shipments."), title=_("Save required"))
		if self.docstatus != 0:
			frappe.throw(_("Only draft plans can fetch shipments."), title=_("Not allowed"))
		assert_air_plan_fields_for_strict_match(self)
		candidates = get_strict_matching_air_shipment_names(self)
		present = {r.air_shipment for r in (self.get("items") or []) if getattr(r, "air_shipment", None)}
		added, already_present, skipped = [], [], []
		for name in candidates:
			if name in present:
				already_present.append(name)
				continue
			ok, msg = air_shipment_allowed_on_plan(name)
			if not ok:
				skipped.append({"shipment": name, "reason": msg})
				continue
			if conflicting_open_air_plan_line(name, self.name):
				skipped.append(
					{
						"shipment": name,
						"reason": _("Already on another submitted consolidation plan (pending assignment)."),
					}
				)
				continue
			self.append("items", {"air_shipment": name})
			added.append(name)
			present.add(name)
		self.save()
		return {"added": added, "already_present": already_present, "skipped": skipped}

	@frappe.whitelist()
	def create_air_consolidation_from_plan(self):
		"""Create a draft Air Consolidation from this submitted plan and link plan lines."""
		self.reload()
		if self.docstatus != 1:
			frappe.throw(_("Submit the plan before creating a consolidation."), title=_("Not Submitted"))
		for row in self.get("items") or []:
			if row.linked_air_consolidation:
				frappe.throw(
					_("Plan line for {0} is already linked to {1}.").format(
						row.air_shipment, row.linked_air_consolidation
					),
					title=_("Already Created"),
				)
		consol = _build_air_consolidation_from_plan_doc(self)
		consol.insert()
		self.reload()
		return consol.name


def _build_air_consolidation_from_plan_doc(plan):
	settings = None
	try:
		from logistics.air_freight.doctype.air_freight_settings.air_freight_settings import AirFreightSettings

		settings = AirFreightSettings.get_settings(plan.company)
	except Exception:
		pass

	cc = plan.company
	branch = plan.branch
	cost_center = None
	profit_center = None
	if settings:
		cost_center = getattr(settings, "default_cost_center", None)
		profit_center = getattr(settings, "default_profit_center", None)
	if not cost_center:
		frappe.throw(_("Set default Cost Center in Air Freight Settings for company {0}.").format(cc))
	if not profit_center:
		frappe.throw(_("Set default Profit Center in Air Freight Settings for company {0}.").format(cc))

	consol = frappe.new_doc("Air Consolidation")
	consol.naming_series = "AC-{MM}-{YYYY}-{####}"
	consol.consolidation_date = getdate(plan.plan_date) or getdate(today())
	consol.consolidation_type = plan.consolidation_type
	consol.status = "Draft"
	consol.company = cc
	consol.branch = branch
	consol.cost_center = cost_center
	consol.profit_center = profit_center
	consol.origin_airport = plan.origin_airport
	consol.destination_airport = plan.destination_airport
	def _split_dt(val):
		if not val:
			d = getdate(today())
			return d, "00:00:00"
		dt = get_datetime(val)
		return getdate(dt), get_time(dt).strftime("%H:%M:%S")

	dep_d, dep_t = _split_dt(plan.target_departure)
	arr_d, arr_t = _split_dt(plan.target_arrival)
	consol.departure_date = dep_d
	consol.arrival_date = arr_d

	consol.append(
		"consolidation_routes",
		{
			"route_sequence": 1,
			"route_type": "Direct",
			"origin_airport": plan.origin_airport,
			"destination_airport": plan.destination_airport,
			"airline": plan.airline,
			"flight_number": plan.flight_number or "TBA",
			"departure_date": dep_d,
			"departure_time": dep_t,
			"arrival_date": arr_d,
			"arrival_time": arr_t,
			"dangerous_goods_allowed": 1,
		},
	)

	idx = 0
	for line in plan.get("items") or []:
		idx += 1
		sh = line.air_shipment
		s = frappe.get_doc("Air Shipment", sh)
		pkg_ref = f"{sh}-{idx}"
		consol.append(
			"consolidation_packages",
			{
				"package_reference": pkg_ref,
				"air_freight_job": sh,
				"shipper": s.shipper,
				"consignee": s.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": s.weight or s.chargeable or 1,
				"package_volume": s.volume or 0,
			},
		)

	return consol
