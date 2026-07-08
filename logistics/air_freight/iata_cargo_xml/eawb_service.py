# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict, List

import frappe
from frappe import _
from frappe.utils import now_datetime

from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder
from logistics.air_freight.utils.iata_settings_utils import resolve_company


def submit_house_eawb(iata_transaction_name: str) -> Dict[str, Any]:
	tx = frappe.get_doc("Air Shipment IATA Transaction", iata_transaction_name)
	tx.check_permission("write")

	if not tx.eawb_enabled:
		frappe.throw(_("e-AWB is not enabled for this record"))
	if tx.eawb_status not in ("Signed", "Created"):
		frappe.throw(_("e-AWB must be signed before submission"))

	company = frappe.db.get_value("Air Shipment", tx.air_shipment, "company")
	builder = MessageBuilder(company=company)
	result = builder.send_house_eawb_message(tx.air_shipment)

	tx.eawb_status = "Submitted"
	if result.get("accepted"):
		tx.eawb_status = "Accepted"
	elif not result.get("success"):
		tx.eawb_status = "Rejected"

	if result.get("message_id"):
		tx.iata_message_id = result.get("message_id")
	tx.last_status_update = now_datetime()
	tx.flags.ignore_permissions = True
	tx.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": result.get("success"),
		"eawb_status": tx.eawb_status,
		"message_id": tx.iata_message_id,
		"result": result,
	}


def submit_consolidated_eawb(
	master_awb_name: str,
	*,
	include_house_manifest: bool = True,
	include_house_awbs: bool = False,
) -> Dict[str, Any]:
	"""Submit master XFWB and optional XFHL/FWB messages for all linked house shipments."""
	mawb = frappe.get_doc("Master Air Waybill", master_awb_name)
	mawb.check_permission("write")

	company = resolve_company(master_awb=master_awb_name)
	builder = MessageBuilder(company=company)

	results = {"master": None, "house_manifests": [], "house_awbs": []}

	master_result = mawb.submit_eawb()
	results["master"] = master_result

	if include_house_manifest:
		manifest_results = builder.send_xfhl_for_mawb(master_awb_name)
		results["house_manifests"] = manifest_results

	if include_house_awbs:
		for ship_name in frappe.get_all(
			"Air Shipment", filters={"master_awb": master_awb_name}, pluck="name"
		):
			tx_name = frappe.db.get_value(
				"Air Shipment IATA Transaction", {"air_shipment": ship_name}, "name"
			)
			if not tx_name:
				continue
			tx = frappe.get_doc("Air Shipment IATA Transaction", tx_name)
			if not tx.eawb_enabled:
				continue
			if tx.eawb_status in ("Signed", "Created"):
				results["house_awbs"].append(submit_house_eawb(tx_name))

	if master_awb_name:
		frappe.db.set_value(
			"Master Air Waybill",
			master_awb_name,
			{
				"manifest_sent": 1,
				"manifest_sent_date": now_datetime(),
			},
		)

	return results


def auto_send_eawb_for_mawb(master_awb_name: str) -> Dict[str, Any]:
	"""Send e-AWB when auto-send is enabled on MAWB or Air Freight Settings."""
	mawb = frappe.get_doc("Master Air Waybill", master_awb_name)
	if not getattr(mawb, "send_awb_to_airline", 0):
		company = resolve_company(master_awb=master_awb_name)
		settings_name = frappe.db.get_value("Air Freight Settings", {"company": company}, "name")
		if settings_name:
			default_auto = frappe.db.get_value(
				"Air Freight Settings", settings_name, "auto_send_eawb_default"
			)
			if not default_auto:
				return {"skipped": True, "reason": "Auto-send disabled"}
		else:
			return {"skipped": True, "reason": "Auto-send disabled"}

	return submit_consolidated_eawb(master_awb_name)


def auto_send_eawb_for_consolidation(consolidation_name: str) -> Dict[str, Any]:
	consol = frappe.get_doc("Air Consolidation", consolidation_name)
	if not getattr(consol, "auto_send_eawb", 0) or not consol.master_awb:
		return {"skipped": True, "reason": "Auto-send disabled or MAWB missing"}
	return submit_consolidated_eawb(consol.master_awb)
