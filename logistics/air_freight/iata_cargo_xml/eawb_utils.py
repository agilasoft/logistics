# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict, List, Optional

import frappe
from frappe.utils import flt

FSU_STATUS_MAP = {
	"ACC": "Accepted",
	"RCS": "Ready for Carriage",
	"FOH": "Freight on Hand",
	"DEP": "Departed",
	"ARR": "Arrived",
	"DLV": "Delivered",
	"RCF": "Ready for Collection",
	"CCO": "Customs Cleared",
	"NFD": "Notified for Delivery",
	"BKD": "Booked",
	"MAN": "Manifested",
	"DIS": "Discrepancy",
	"SPL": "Split Arrival",
}

SPLIT_FSU_CODES = {"SPL", "DIS"}


def map_fsu_status(status_code: str, status_description: str = "") -> str:
	code = (status_code or "").strip().upper()
	return FSU_STATUS_MAP.get(code, status_description or code or "Exception")


def resolve_special_handling_codes(
	*,
	airline: Optional[str] = None,
	direction: Optional[str] = None,
	paper_awb_required: bool = False,
	manual_codes: Optional[str] = None,
) -> List[str]:
	"""Return IATA SHC list for e-AWB (ECC electronic contract / ECP paper companion)."""
	if manual_codes:
		return [c.strip().upper() for c in manual_codes.split(",") if c.strip()]

	codes = ["ECC"] if not paper_awb_required else ["ECP"]
	if airline:
		extra = frappe.db.get_value("Airline", airline, "default_special_handling_codes")
		if extra:
			for code in extra.split(","):
				code = code.strip().upper()
				if code and code not in codes:
					codes.append(code)
	if direction == "Import":
		for code in ("IMP",):
			if code not in codes:
				codes.append(code)
	return codes


def resolve_airline_endpoint(
	settings,
	airline: Optional[str] = None,
	test_mode: bool = False,
) -> Optional[str]:
	"""Per-airline Cargo-XML endpoint override (Direct mode only)."""
	if not airline or test_mode:
		return None

	if test_mode:
		return frappe.db.get_value("Airline", airline, "cargo_xml_test_endpoint")

	return frappe.db.get_value("Airline", airline, "cargo_xml_endpoint")


def get_linked_shipments(master_awb_name: str) -> List[frappe.Document]:
	names = frappe.get_all(
		"Air Shipment",
		filters={"master_awb": master_awb_name},
		pluck="name",
	)
	return [frappe.get_doc("Air Shipment", name) for name in names]


def aggregate_mawb_totals(master_awb_name: str) -> Dict[str, Any]:
	shipments = get_linked_shipments(master_awb_name)
	total_weight = 0.0
	total_volume = 0.0
	total_chargeable = 0.0
	total_pieces = 0
	primary_shipment = shipments[0] if shipments else None

	for ship in shipments:
		total_weight += flt(ship.weight)
		total_volume += flt(ship.volume)
		total_chargeable += flt(ship.chargeable or ship.weight)
		if ship.packages:
			for pkg in ship.packages:
				total_pieces += int(pkg.no_of_packs or 1)

	return {
		"shipments": shipments,
		"primary_shipment": primary_shipment,
		"total_weight": total_weight,
		"total_volume": total_volume,
		"total_chargeable": total_chargeable or flt(
			frappe.db.get_value("Master Air Waybill", master_awb_name, "booked_weight_kg")
		),
		"total_pieces": total_pieces,
	}


def collect_packages_for_security(shipments: List[frappe.Document]) -> List[Any]:
	packages = []
	for ship in shipments:
		for pkg in ship.get("packages") or []:
			packages.append(pkg)
	return packages
