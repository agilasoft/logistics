# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Allocation factors for Purchase Invoice lines created from Air/Sea Consolidation charges."""

from __future__ import annotations

from typing import Any

from frappe.utils import flt


def count_attached_jobs(consolidation_doc: Any) -> int:
    """Return number of rows in attached_air_freight_jobs or attached_sea_shipments."""
    dt = getattr(consolidation_doc, "doctype", None)
    if dt == "Air Consolidation":
        rows = getattr(consolidation_doc, "attached_air_freight_jobs", None) or []
    elif dt == "Sea Consolidation":
        rows = getattr(consolidation_doc, "attached_sea_shipments", None) or []
    else:
        return 0
    return len(rows)


def allocation_factor_for_attached_job(
    consolidation_doc: Any,
    charge_row: Any,
    attached_row: Any,
) -> float:
    """
    Per-job share of a consolidation charge (0–1), matching
    AirConsolidationShipments.calculate_individual_charges branching.

    - Equal: 1 / n jobs
    - Weight-based: job_weight / consolidation.total_weight
    - Otherwise (Volume-based, Value-based, Custom, etc.): attached_row.cost_allocation_percentage / 100
    """
    n = count_attached_jobs(consolidation_doc)
    if n <= 0:
        return 0.0

    method = (getattr(charge_row, "allocation_method", None) or "").strip()

    if method == "Equal":
        return 1.0 / float(n)

    if method == "Weight-based":
        tw = flt(getattr(consolidation_doc, "total_weight", None) or 0)
        jw = flt(getattr(attached_row, "weight", None) or 0)
        if tw > 0:
            return jw / tw
        return 0.0

    pct = flt(getattr(attached_row, "cost_allocation_percentage", None) or 0)
    return pct / 100.0


def distribute_amounts_with_rounding(amounts: list[float], target_total: float) -> list[float]:
    """
    Adjust the last positive line so that sum(lines) matches target_total after rounding noise.
    """
    if not amounts:
        return []
    target_total = flt(target_total, 2)
    out = [flt(x, 2) for x in amounts]
    diff = flt(target_total - sum(out), 2)
    for i in range(len(out) - 1, -1, -1):
        if out[i] > 0 and diff != 0:
            out[i] = flt(out[i] + diff, 2)
            break
    return out
