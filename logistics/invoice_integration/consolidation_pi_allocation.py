# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Allocation factors for Purchase Invoice lines created from Air/Sea Consolidation charges.

Per-shipment rows used for allocation and PI splitting are derived from ``consolidation_packages``
(one row per distinct shipment, with weight/volume/value summed across that shipment's package rows).
Air uses ``air_freight_job``; Sea uses ``sea_shipment``. When Sea has no package-linked shipments,
``attached_sea_shipments`` is used as a fallback (e.g. manually attached rows).

Weight-based and Volume-based splits use aggregated ``consolidation_packages`` weights/volumes
when those measures differ across shipments (what users enter on the consolidation). When package
lines show the same weight or volume per shipment, shipment billing fields are used instead
(``chargeable`` / ``total_weight`` or ``total_volume``) so equal package mirrors do not hide
different billable amounts (#875).
"""

from __future__ import annotations

from typing import Any, Optional

import frappe
from frappe.utils import flt

_WEIGHT_BASIS_CACHE = "_logistics_pi_weight_basis_v2"
_VOLUME_BASIS_CACHE = "_logistics_pi_volume_basis_v2"


def _shipment_doctype_for_consolidation(consolidation_doctype: Optional[str]) -> Optional[str]:
    if consolidation_doctype == "Air Consolidation":
        return "Air Shipment"
    if consolidation_doctype == "Sea Consolidation":
        return "Sea Shipment"
    return None


def _batch_billing_weights(shipment_doctype: str, names: list[str]) -> dict[str, float]:
    """Per shipment: chargeable if > 0 else total_weight (gross), for PI cost split (#875)."""
    if not names:
        return {}
    unique = list(dict.fromkeys(names))
    rows = frappe.get_all(
        shipment_doctype,
        filters={"name": ("in", unique)},
        fields=["name", "chargeable", "total_weight"],
    )
    out: dict[str, float] = {}
    for r in rows:
        chg = flt(r.get("chargeable") or 0)
        tw = flt(r.get("total_weight") or 0)
        out[r["name"]] = chg if chg > 0 else tw
    return out


def _batch_billing_volumes(shipment_doctype: str, names: list[str]) -> dict[str, float]:
    """Per shipment: total_volume when > 0, for PI volume split when package lines lack volume."""
    if not names:
        return {}
    unique = list(dict.fromkeys(names))
    rows = frappe.get_all(
        shipment_doctype,
        filters={"name": ("in", unique)},
        fields=["name", "total_volume"],
    )
    out: dict[str, float] = {}
    for r in rows:
        tv = flt(r.get("total_volume") or 0)
        if tv > 0:
            out[r["name"]] = tv
    return out


def _aggregated_row_weight(attached_row: Any) -> float:
    return flt(
        getattr(attached_row, "weight", None)
        or getattr(attached_row, "total_weight", None)
        or 0
    )


def _aggregated_row_volume(attached_row: Any) -> float:
    return flt(
        getattr(attached_row, "volume", None)
        or getattr(attached_row, "total_volume", None)
        or 0
    )


def _shipment_link_name(attached_row: Any, consolidation_doctype: Optional[str]) -> Optional[str]:
    if consolidation_doctype == "Air Consolidation":
        return getattr(attached_row, "air_freight_job", None)
    if consolidation_doctype == "Sea Consolidation":
        return getattr(attached_row, "sea_shipment", None)
    return None


def _measures_differ(values: list[float]) -> bool:
    """True when there are 2+ rows and not every non-zero measure is the same."""
    if len(values) < 2:
        return False
    rounded = [round(flt(v), 6) for v in values]
    return len(set(rounded)) > 1


def _pick_per_row_measures(agg_values: list[float], bill_values: list[float]) -> tuple[list[float], float]:
    """
    Choose per-shipment measures for allocation denominators.

    Prefer consolidation package aggregates when they differ across shipments; otherwise prefer
    shipment billing measures when those differ; else package aggregates; else billing.
    """
    agg_sum = sum(agg_values)
    bill_sum = sum(bill_values)
    if agg_sum > 0 and _measures_differ(agg_values):
        return agg_values, agg_sum
    if bill_sum > 0 and _measures_differ(bill_values):
        return bill_values, bill_sum
    if agg_sum > 0:
        return agg_values, agg_sum
    if bill_sum > 0:
        return bill_values, bill_sum
    return agg_values, agg_sum


def _resolve_attached_row_index(rows: list, attached_row: Any) -> Optional[int]:
    """Match attached_row to rows by object identity, child name, or shipment link."""
    try:
        return rows.index(attached_row)
    except ValueError:
        pass
    idx = next(
        (
            i
            for i, r in enumerate(rows)
            if getattr(r, "name", None)
            and getattr(attached_row, "name", None)
            and r.name == attached_row.name
        ),
        None,
    )
    if idx is not None:
        return idx
    target_air = getattr(attached_row, "air_freight_job", None)
    target_sea = getattr(attached_row, "sea_shipment", None)
    for i, r in enumerate(rows):
        if target_air and getattr(r, "air_freight_job", None) == target_air:
            return i
        if target_sea and getattr(r, "sea_shipment", None) == target_sea:
            return i
    return None


def _weight_based_basis(consolidation_doc: Any) -> dict[str, Any]:
    """
    Cached per-doc weights for Weight-based factors.

    Package aggregates win when they differ across shipments; otherwise shipment billing weight
    (chargeable else total_weight) when those differ; else whichever sum is available.
    """
    rows = _attached_shipment_rows(consolidation_doc)
    doctype = getattr(consolidation_doc, "doctype", None)
    shipment_dt = _shipment_doctype_for_consolidation(doctype)
    names = [n for n in (_shipment_link_name(r, doctype) for r in rows) if n]
    billing_map = _batch_billing_weights(shipment_dt, names) if shipment_dt and names else {}

    agg_weights: list[float] = []
    bill_weights: list[float] = []
    for r in rows:
        agg_weights.append(_aggregated_row_weight(r))
        link = _shipment_link_name(r, doctype)
        bill_weights.append(flt(billing_map.get(link, 0)) if link else 0.0)

    jws, tw = _pick_per_row_measures(agg_weights, bill_weights)
    if tw <= 0:
        tw = flt(getattr(consolidation_doc, "total_weight", None) or 0)
        if tw <= 0 and rows:
            tw = sum(jws)

    return {"rows": rows, "jws": jws, "tw": tw}


def _get_weight_basis(consolidation_doc: Any) -> dict[str, Any]:
    cached = getattr(consolidation_doc, _WEIGHT_BASIS_CACHE, None)
    if cached is None:
        cached = _weight_based_basis(consolidation_doc)
        setattr(consolidation_doc, _WEIGHT_BASIS_CACHE, cached)
    return cached


def _volume_based_basis(consolidation_doc: Any) -> dict[str, Any]:
    """
    Cached volumes for Volume-based factors (same package-vs-shipment pick as weight).
    """
    rows = _attached_shipment_rows(consolidation_doc)
    doctype = getattr(consolidation_doc, "doctype", None)
    shipment_dt = _shipment_doctype_for_consolidation(doctype)
    names = [n for n in (_shipment_link_name(r, doctype) for r in rows) if n]
    billing_map = _batch_billing_volumes(shipment_dt, names) if shipment_dt and names else {}

    agg_volumes: list[float] = []
    bill_volumes: list[float] = []
    for r in rows:
        agg_volumes.append(_aggregated_row_volume(r))
        link = _shipment_link_name(r, doctype)
        bill_volumes.append(flt(billing_map.get(link, 0)) if link else 0.0)

    jvs, tv = _pick_per_row_measures(agg_volumes, bill_volumes)
    if tv <= 0:
        tv = flt(getattr(consolidation_doc, "total_volume", None) or 0)
        if tv <= 0 and rows:
            tv = sum(jvs)

    return {"rows": rows, "jvs": jvs, "tv": tv}


def _get_volume_basis(consolidation_doc: Any) -> dict[str, Any]:
    cached = getattr(consolidation_doc, _VOLUME_BASIS_CACHE, None)
    if cached is None:
        cached = _volume_based_basis(consolidation_doc)
        setattr(consolidation_doc, _VOLUME_BASIS_CACHE, cached)
    return cached


def _sea_planning_allocation_pct_map(consolidation_doc: Any) -> dict[str, float]:
    """Per ``sea_shipment`` cost split % from ``consolidation_planning_lines`` (Custom allocation)."""
    out: dict[str, float] = {}
    for row in consolidation_doc.get("consolidation_planning_lines") or []:
        sh = getattr(row, "sea_shipment", None)
        if sh:
            out[sh] = flt(getattr(row, "cost_allocation_percentage", None) or 0)
    return out


def _derive_sea_planning_rows(consolidation_doc: Any) -> list:
    """Per-shipment rows from planned shipments when packages do not define cargo links."""
    rows = []
    for pl in consolidation_doc.get("consolidation_planning_lines") or []:
        sh = getattr(pl, "sea_shipment", None)
        if not sh:
            continue
        rows.append(
            frappe._dict(
                sea_shipment=sh,
                weight=flt(getattr(pl, "weight_est", None) or 0),
                volume=flt(getattr(pl, "volume_est", None) or 0),
                value=0.0,
                cost_allocation_percentage=flt(
                    getattr(pl, "cost_allocation_percentage", None) or 0
                ),
            )
        )
    return rows


def _derive_sea_attached_rows(consolidation_doc: Any) -> list:
    """Group Sea Consolidation Packages by ``sea_shipment`` into per-shipment summary rows."""
    pct_by_shipment = _sea_planning_allocation_pct_map(consolidation_doc)
    aggregates: "dict[str, Any]" = {}
    order: list = []
    for pkg in (consolidation_doc.get("consolidation_packages") or []):
        sh = getattr(pkg, "sea_shipment", None)
        if not sh:
            continue
        if sh not in aggregates:
            aggregates[sh] = frappe._dict(
                sea_shipment=sh,
                weight=0.0,
                volume=0.0,
                value=0.0,
                cost_allocation_percentage=pct_by_shipment.get(sh, 0.0),
            )
            order.append(sh)
        agg = aggregates[sh]
        agg.weight += flt(getattr(pkg, "package_weight", None) or 0)
        agg.volume += flt(getattr(pkg, "package_volume", None) or 0)
        agg.value += flt(getattr(pkg, "value", None) or 0)
    return [aggregates[name] for name in order]


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
    """Per-shipment rows used for allocation (derived from packages; Sea falls back to child table)."""
    dt = getattr(consolidation_doc, "doctype", None)
    if dt == "Air Consolidation":
        return _derive_air_attached_rows(consolidation_doc)
    if dt == "Sea Consolidation":
        derived = _derive_sea_attached_rows(consolidation_doc)
        if derived:
            return derived
        planning = _derive_sea_planning_rows(consolidation_doc)
        if planning:
            return planning
        return list(getattr(consolidation_doc, "attached_sea_shipments", None) or [])
    return []


def count_attached_jobs(consolidation_doc: Any) -> int:
    """Return number of distinct shipments attached to a consolidation.

    For Air Consolidation this is the count of distinct ``air_freight_job`` values across
    ``consolidation_packages``; for Sea Consolidation it is distinct ``sea_shipment`` on packages,
    or planned shipments on ``consolidation_planning_lines`` when no package-linked shipments exist.
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
    - Weight-based: aggregated package weights when they differ across shipments; otherwise shipment
      billing weight (chargeable else total_weight) when those differ; header fallback if all zero.
    - Volume-based: same rule using package volumes vs shipment ``total_volume``.
    - Value-based: row_value / sum(values); values fall back to linked shipment goods_value when row value is 0;
      if no value data at all, split equally across shipments.
    - Custom: cost_allocation_percentage per row; if all rows are 0%, split equally.

    Per-shipment rows are derived from ``consolidation_packages`` (Air: ``air_freight_job``,
    Sea: ``sea_shipment``); Sea falls back to ``attached_sea_shipments`` when packages have no links.
    """
    n = count_attached_jobs(consolidation_doc)
    if n <= 0:
        return 0.0

    method = (getattr(charge_row, "allocation_method", None) or "").strip()

    if not method or method == "Equal":
        return 1.0 / float(n)

    rows = _attached_shipment_rows(consolidation_doc)

    if method == "Weight-based":
        basis = _get_weight_basis(consolidation_doc)
        rws = basis["rows"]
        idx = _resolve_attached_row_index(rws, attached_row)
        if idx is None:
            return 0.0
        tw = flt(basis["tw"] or 0)
        if tw <= 0:
            return 0.0
        jw = flt(basis["jws"][idx])
        return jw / tw

    if method == "Volume-based":
        basis = _get_volume_basis(consolidation_doc)
        rws = basis["rows"]
        idx = _resolve_attached_row_index(rws, attached_row)
        if idx is None:
            return 0.0
        tv = flt(basis["tv"] or 0)
        if tv <= 0:
            return 0.0
        jv = flt(basis["jvs"][idx])
        return jv / tv

    if method == "Value-based":
        doctype = getattr(consolidation_doc, "doctype", None)
        row_values = [_resolved_cargo_value(r, doctype) for r in rows]
        total_val = sum(row_values)
        if total_val <= 0:
            return 1.0 / float(n)
        idx = _resolve_attached_row_index(rows, attached_row)
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
