# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Allocation factors for Purchase Invoice lines created from Air/Sea Consolidation charges.

Air Consolidation no longer keeps a separate "attached shipments" child table; the per-shipment
rows used for allocation and PI splitting are derived from `consolidation_packages` (one row per
distinct `air_freight_job`, with weight/volume/value summed across that job's package rows).
Sea Consolidation continues to use its `attached_sea_shipments` child table.
"""

from __future__ import annotations

from typing import Any, Optional

import frappe
from frappe.utils import flt


def _derive_air_attached_rows(consolidation_doc: Any) -> list:
    """Group Air Consolidation Packages by ``air_freight_job`` into per-shipment summary rows.

    Each derived row exposes the fields used by allocation factors and PI splitting:
    ``air_freight_job``, ``weight``, ``volume``, ``value``, ``cost_allocation_percentage``.
    Order follows first appearance in ``consolidation_packages``.
    """
    aggregates: "dict[str, Any]" = {}
    order: list = []
    for pkg in (consolidation_doc.get("consolidation_packages") or []):
        job = getattr(pkg, "air_freight_job", None)
        if not job:
            continue
        if job not in aggregates:
            aggregates[job] = frappe._dict(
                air_freight_job=job,
                weight=0.0,
                volume=0.0,
                value=0.0,
                cost_allocation_percentage=0.0,
            )
            order.append(job)
        agg = aggregates[job]
        agg.weight += flt(getattr(pkg, "package_weight", None) or 0)
        agg.volume += flt(getattr(pkg, "package_volume", None) or 0)
        agg.value += flt(getattr(pkg, "value", None) or 0)
        agg.cost_allocation_percentage += flt(getattr(pkg, "cost_allocation", None) or 0)
    return [aggregates[name] for name in order]


def _attached_shipment_rows(consolidation_doc: Any) -> list:
    """Per-shipment rows used for allocation (Air: derived from packages; Sea: child table)."""
    dt = getattr(consolidation_doc, "doctype", None)
    if dt == "Air Consolidation":
        return _derive_air_attached_rows(consolidation_doc)
    if dt == "Sea Consolidation":
        return list(getattr(consolidation_doc, "attached_sea_shipments", None) or [])
    return []


def count_attached_jobs(consolidation_doc: Any) -> int:
    """Return number of distinct shipments attached to a consolidation.

    For Air Consolidation this is the count of distinct ``air_freight_job`` values across
    ``consolidation_packages``; for Sea Consolidation it is ``len(attached_sea_shipments)``.
    """
    return len(_attached_shipment_rows(consolidation_doc))


def _resolved_cargo_value(attached_row: Any, consolidation_doctype: Optional[str]) -> float:
    """Numeric cargo value for allocation: child row `value`, else linked shipment `goods_value`."""
    v = flt(getattr(attached_row, "value", None) or 0)
    if v > 0:
        return v
    if consolidation_doctype == "Sea Consolidation":
        ss = getattr(attached_row, "sea_shipment", None)
        if ss:
            gv = frappe.db.get_value("Sea Shipment", ss, "goods_value")
            return flt(gv or 0)
    if consolidation_doctype == "Air Consolidation":
        aj = getattr(attached_row, "air_freight_job", None)
        if aj:
            gv = frappe.db.get_value("Air Shipment", aj, "goods_value")
            return flt(gv or 0)
    return 0.0


def _factor_from_row_percentages(attached_row: Any, rows: list, n: int) -> float:
    """
    Custom / %-split rows: use cost_allocation_percentage when set; if every row is 0%, split equally.
    If some rows have % and this row is 0%, factor is 0 (intentional exclusion).
    """
    pct_row = flt(getattr(attached_row, "cost_allocation_percentage", None) or 0)
    if pct_row > 0:
        return pct_row / 100.0
    total_pct = sum(flt(getattr(r, "cost_allocation_percentage", None) or 0) for r in rows)
    if total_pct <= 0:
        return 1.0 / float(n)
    return 0.0


def allocation_factor_for_attached_job(
    consolidation_doc: Any,
    charge_row: Any,
    attached_row: Any,
) -> float:
    """
    Per-shipment share of a consolidation charge (0–1).

    - Equal (or blank method): 1 / n shipments
    - Weight-based: row_weight / total_weight (header total, else sum of attached weights)
    - Volume-based: row_volume / total_volume (header total, else sum of attached volumes)
    - Value-based: row_value / sum(values); values fall back to linked shipment goods_value when row value is 0;
      if no value data at all, split equally across shipments.
    - Custom: cost_allocation_percentage per row; if all rows are 0%, split equally.

    For Air Consolidation the per-shipment rows are derived from ``consolidation_packages``
    (sums per ``air_freight_job``); for Sea Consolidation they come from ``attached_sea_shipments``.
    """
    n = count_attached_jobs(consolidation_doc)
    if n <= 0:
        return 0.0

    method = (getattr(charge_row, "allocation_method", None) or "").strip()

    if not method or method == "Equal":
        return 1.0 / float(n)

    rows = _attached_shipment_rows(consolidation_doc)

    if method == "Weight-based":
        jw = flt(
            getattr(attached_row, "weight", None)
            or getattr(attached_row, "total_weight", None)
            or 0
        )
        tw = flt(getattr(consolidation_doc, "total_weight", None) or 0)
        if tw <= 0 and rows:
            tw = sum(
                flt(getattr(r, "weight", None) or getattr(r, "total_weight", None) or 0) for r in rows
            )
        if tw > 0:
            return jw / tw
        return 0.0

    if method == "Volume-based":
        jv = flt(
            getattr(attached_row, "volume", None)
            or getattr(attached_row, "total_volume", None)
            or 0
        )
        tv = flt(getattr(consolidation_doc, "total_volume", None) or 0)
        if tv <= 0 and rows:
            tv = sum(
                flt(getattr(r, "volume", None) or getattr(r, "total_volume", None) or 0) for r in rows
            )
        if tv > 0:
            return jv / tv
        return 0.0

    if method == "Value-based":
        doctype = getattr(consolidation_doc, "doctype", None)
        row_values = [_resolved_cargo_value(r, doctype) for r in rows]
        total_val = sum(row_values)
        if total_val <= 0:
            return 1.0 / float(n)
        try:
            idx = rows.index(attached_row)
        except ValueError:
            idx = next(
                (
                    i
                    for i, r in enumerate(rows)
                    if getattr(r, "name", None) and getattr(attached_row, "name", None) and r.name == attached_row.name
                ),
                None,
            )
        if idx is None:
            # Fall back by matching air_freight_job / sea_shipment when identity differs (derived rows).
            target_air = getattr(attached_row, "air_freight_job", None)
            target_sea = getattr(attached_row, "sea_shipment", None)
            for i, r in enumerate(rows):
                if target_air and getattr(r, "air_freight_job", None) == target_air:
                    idx = i
                    break
                if target_sea and getattr(r, "sea_shipment", None) == target_sea:
                    idx = i
                    break
        if idx is None:
            return 1.0 / float(n)
        rv = row_values[idx]
        return (rv / total_val) if rv > 0 else 0.0

    return _factor_from_row_percentages(attached_row, rows, n)


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
