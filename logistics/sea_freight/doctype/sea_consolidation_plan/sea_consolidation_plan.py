# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

from logistics.utils.consolidation_plan import (
	assert_sea_plan_fields_for_strict_match,
	conflicting_open_sea_plan_line,
	get_strict_matching_sea_shipment_names,
	sea_shipment_allowed_on_plan,
)


class SeaConsolidationPlan(Document):
	def validate(self):
		self._validate_items()

	def _validate_items(self):
		seen = set()
		for row in self.get("items") or []:
			sh = row.sea_shipment
			if not sh:
				continue
			if sh in seen:
				frappe.throw(_("Sea Shipment {0} is duplicated in this plan.").format(sh))
			seen.add(sh)
			ok, msg = sea_shipment_allowed_on_plan(sh)
			if not ok:
				frappe.throw(msg, title=_("Invalid Shipment"))
			origin = frappe.db.get_value("Sea Shipment", sh, "origin_port")
			dest = frappe.db.get_value("Sea Shipment", sh, "destination_port")
			if self.origin_port and origin and origin != self.origin_port:
				frappe.throw(
					_("Sea Shipment {0} origin {1} does not match plan origin {2}.").format(
						sh, origin, self.origin_port
					)
				)
			if self.destination_port and dest and dest != self.destination_port:
				frappe.throw(
					_("Sea Shipment {0} destination {1} does not match plan destination {2}.").format(
						sh, dest, self.destination_port
					)
				)
			if self.docstatus == 0 and conflicting_open_sea_plan_line(sh, self.name if not self.is_new() else None):
				frappe.throw(
					_("Sea Shipment {0} is already on another submitted consolidation plan (pending assignment).").format(
						sh
					),
					title=_("Consolidation Plan Conflict"),
				)

	def before_submit(self):
		if not self.get("items"):
			frappe.throw(_("Add at least one shipment before submitting the plan."), title=_("No Lines"))

	def before_cancel(self):
		for row in frappe.get_all(
			"Sea Consolidation Plan Item",
			filters={"parent": self.name},
			fields=["linked_sea_consolidation"],
		):
			if row.linked_sea_consolidation:
				frappe.throw(
					_("Cannot cancel: a line is linked to Sea Consolidation {0}.").format(
						row.linked_sea_consolidation
					),
					title=_("Linked Consolidation"),
				)

	@frappe.whitelist()
	def fetch_matching_sea_shipments(self):
		if self.is_new():
			frappe.throw(_("Save the plan before fetching shipments."), title=_("Save required"))
		if self.docstatus != 0:
			frappe.throw(_("Only draft plans can fetch shipments."), title=_("Not allowed"))
		assert_sea_plan_fields_for_strict_match(self)
		candidates = get_strict_matching_sea_shipment_names(self)
		present = {r.sea_shipment for r in (self.get("items") or []) if getattr(r, "sea_shipment", None)}
		added, already_present, skipped = [], [], []
		for name in candidates:
			if name in present:
				already_present.append(name)
				continue
			ok, msg = sea_shipment_allowed_on_plan(name)
			if not ok:
				skipped.append({"shipment": name, "reason": msg})
				continue
			if conflicting_open_sea_plan_line(name, self.name):
				skipped.append(
					{
						"shipment": name,
						"reason": _("Already on another submitted consolidation plan (pending assignment)."),
					}
				)
				continue
			self.append("items", {"sea_shipment": name})
			added.append(name)
			present.add(name)
		self.save()
		return {"added": added, "already_present": already_present, "skipped": skipped}

	@frappe.whitelist()
	def create_sea_consolidation_from_plan(self):
		self.reload()
		if self.docstatus != 1:
			frappe.throw(_("Submit the plan before creating a consolidation."), title=_("Not Submitted"))
		for row in self.get("items") or []:
			if row.linked_sea_consolidation:
				frappe.throw(
					_("Plan line for {0} is already linked to {1}.").format(
						row.sea_shipment, row.linked_sea_consolidation
					),
					title=_("Already Created"),
				)
		consol = _build_sea_consolidation_from_plan_doc(self)
		consol.insert()
		self.reload()
		return consol.name


def _build_sea_consolidation_from_plan_doc(plan):
	cost_center = frappe.db.get_single_value("Sea Freight Settings", "default_cost_center")
	profit_center = frappe.db.get_single_value("Sea Freight Settings", "default_profit_center")
	if not cost_center:
		frappe.throw(_("Set Default Cost Center in Sea Freight Settings."))
	if not profit_center:
		frappe.throw(_("Set Default Profit Center in Sea Freight Settings."))

	consol = frappe.new_doc("Sea Consolidation")
	consol.naming_series = "SC-{MM}-{YYYY}-{####}"
	consol.consolidation_date = getdate(plan.plan_date) or getdate(today())
	consol.consolidation_type = plan.consolidation_type
	consol.status = "Draft"
	consol.company = plan.company
	consol.branch = plan.branch
	consol.cost_center = cost_center
	consol.profit_center = profit_center
	consol.origin_port = plan.origin_port
	consol.destination_port = plan.destination_port
	consol.etd = plan.target_etd
	consol.eta = plan.target_eta
	consol.shipping_line = plan.shipping_line
	consol.vessel_name = plan.vessel_name or "TBA"
	consol.voyage_number = plan.voyage_number or "TBA"

	consol.append(
		"consolidation_routes",
		{
			"route_type": "Direct",
			"origin_port": plan.origin_port,
			"destination_port": plan.destination_port,
			"shipping_line": plan.shipping_line,
			"vessel_name": plan.vessel_name or "TBA",
			"voyage_number": plan.voyage_number or "TBA",
			"etd": plan.target_etd,
			"eta": plan.target_eta,
			"dangerous_goods_allowed": 1,
		},
	)

	idx = 0
	for line in plan.get("items") or []:
		idx += 1
		sh = line.sea_shipment
		s = frappe.get_doc("Sea Shipment", sh)
		pkg_ref = f"{sh}-{idx}"
		consol.append(
			"consolidation_packages",
			{
				"package_reference": pkg_ref,
				"sea_shipment": sh,
				"shipper": s.shipper,
				"consignee": s.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": s.weight or 1,
				"package_volume": s.volume or 0,
			},
		)

	return consol
