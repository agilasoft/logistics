# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

"""
Shared Sea Shipment / Container penalty calculations.

Detention uses SF-DISCHARGED milestone actual_end when present, else ATA — never ETA.
Demurrage uses SF-GATE-IN milestone actual_end when present.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import flt, getdate


def _milestones_iter(shipment_doc):
	rows = getattr(shipment_doc, "milestones", None)
	if rows is None and hasattr(shipment_doc, "get"):
		rows = shipment_doc.get("milestones")
	return rows or []


def _containers_iter(shipment_doc):
	rows = getattr(shipment_doc, "containers", None)
	if rows is None and hasattr(shipment_doc, "get"):
		rows = shipment_doc.get("containers")
	return rows or []


def get_detention_reference_date(shipment_doc):
	"""
	Anchor date for detention: SF-DISCHARGED actual_end, else ATA. Never ETA.
	"""
	for row in _milestones_iter(shipment_doc):
		if getattr(row, "milestone", None) == "SF-DISCHARGED" and getattr(row, "actual_end", None):
			return getdate(row.actual_end)
	ata = getattr(shipment_doc, "ata", None)
	if ata is None and hasattr(shipment_doc, "get"):
		ata = shipment_doc.get("ata")
	if ata:
		return getdate(ata)
	return None


def get_gate_in_date_from_shipment(shipment_doc):
	"""Demurrage anchor: SF-GATE-IN milestone actual_end when present."""
	for row in _milestones_iter(shipment_doc):
		if getattr(row, "milestone", None) == "SF-GATE-IN" and getattr(row, "actual_end", None):
			return getdate(row.actual_end)
	return None


def get_shipment_penalty_dates(shipment_doc):
	"""Returns (detention_reference_date | None, gate_in_date | None)."""
	return get_detention_reference_date(shipment_doc), get_gate_in_date_from_shipment(shipment_doc)


def effective_free_time_days(container_doc, settings):
	"""
	Per-container free time: container value if set (non-zero), else Sea Freight default.
	Treats 0 as unset — same as existing Container penalty logic.
	"""
	default_ft = flt(getattr(settings, "default_free_time_days", 7))
	if container_doc is None:
		return default_ft
	c_ft = flt(getattr(container_doc, "free_time_days", 0) or 0)
	return c_ft if c_ft else default_ft


def compute_penalty_days(detention_reference_date, gate_in_date, today, free_time_days):
	"""
	Returns (detention_days, demurrage_days) for one container using the same formulas as legacy Sea Shipment.
	Either date may be None; missing anchor yields 0 for that component.
	"""
	detention_days = 0
	demurrage_days = 0
	ft = flt(free_time_days)

	if detention_reference_date:
		days_since = (today - detention_reference_date).days
		if days_since > ft:
			detention_days = days_since - ft

	if gate_in_date:
		days_at_port = (today - gate_in_date).days
		if days_at_port > ft:
			demurrage_days = days_at_port - ft

	return detention_days, demurrage_days


def estimated_penalty_amount_for_days(detention_days, demurrage_days, settings):
	detention_rate = flt(getattr(settings, "detention_rate_per_day", 0) or 0)
	demurrage_rate = flt(getattr(settings, "demurrage_rate_per_day", 0) or 0)
	return flt(detention_days) * detention_rate + flt(demurrage_days) * demurrage_rate


def resolve_container_doc_from_sea_row(row):
	"""Best-effort Container document for a Sea Freight Containers child row (read-only)."""
	from logistics.container_management.api import sea_container_row_field_to_doc_name

	link = getattr(row, "container", None)
	if link and frappe.db.exists("Container", link):
		return frappe.get_doc("Container", link)
	name = sea_container_row_field_to_doc_name(getattr(row, "container_no", None))
	if name and frappe.db.exists("Container", name):
		return frappe.get_doc("Container", name)
	return None


def min_effective_free_time_days_for_shipment(shipment_doc, settings):
	"""Minimum effective free time across container rows (strictest); default if no rows."""
	rows = [r for r in _containers_iter(shipment_doc) if getattr(r, "container_no", None) and str(getattr(r, "container_no", "")).strip()]
	if not rows:
		return flt(getattr(settings, "default_free_time_days", 7))
	fts = []
	for row in rows:
		cdoc = resolve_container_doc_from_sea_row(row)
		fts.append(effective_free_time_days(cdoc, settings))
	return min(fts) if fts else flt(getattr(settings, "default_free_time_days", 7))


def compute_penalty_totals_for_sea_shipment(shipment_doc, settings, today):
	"""
	Aggregate detention/demurrage days and estimated penalty amount for a Sea Shipment.
	Returns dict: detention_days, demurrage_days, estimated_penalty_amount, free_time_days_summary, has_any_anchor.
	"""
	det_ref, gate_in = get_shipment_penalty_dates(shipment_doc)
	default_ft = flt(getattr(settings, "default_free_time_days", 7))
	rows = [r for r in _containers_iter(shipment_doc) if getattr(r, "container_no", None) and str(getattr(r, "container_no", "")).strip()]

	total_det = 0.0
	total_dem = 0.0
	total_amount = 0.0
	max_ft = 0.0
	has_any_anchor = bool(det_ref or gate_in)

	if not has_any_anchor:
		return {
			"detention_days": 0.0,
			"demurrage_days": 0.0,
			"estimated_penalty_amount": 0.0,
			"free_time_days_summary": default_ft,
			"has_any_anchor": False,
		}

	if not rows:
		ft = default_ft
		d_det, d_dem = compute_penalty_days(det_ref, gate_in, today, ft)
		total_det = d_det
		total_dem = d_dem
		total_amount = estimated_penalty_amount_for_days(d_det, d_dem, settings)
		max_ft = ft
	else:
		for row in rows:
			cdoc = resolve_container_doc_from_sea_row(row)
			ft = effective_free_time_days(cdoc, settings)
			max_ft = max(max_ft, ft)
			d_det, d_dem = compute_penalty_days(det_ref, gate_in, today, ft)
			total_det += d_det
			total_dem += d_dem
			total_amount += estimated_penalty_amount_for_days(d_det, d_dem, settings)

	return {
		"detention_days": total_det,
		"demurrage_days": total_dem,
		"estimated_penalty_amount": total_amount,
		"free_time_days_summary": max_ft if rows else default_ft,
		"has_any_anchor": True,
	}


def compute_penalty_for_single_container(container_doc, shipment_doc, settings, today):
	"""Per-container demurrage/detention days and estimated amount (for sync / API)."""
	det_ref, gate_in = get_shipment_penalty_dates(shipment_doc)
	ft = effective_free_time_days(container_doc, settings)
	d_det, d_dem = compute_penalty_days(det_ref, gate_in, today, ft)
	amount = estimated_penalty_amount_for_days(d_det, d_dem, settings)
	return {
		"demurrage_days": d_dem,
		"detention_days": d_det,
		"estimated_penalty_amount": amount,
		"has_penalties": 1 if (d_det > 0 or d_dem > 0) else 0,
	}
