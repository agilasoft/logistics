# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Copy Customs commercial-invoice line items onto a Transport Order package table.

Customs stores the goods on line items. A linked Transport Order stores the same
goods on its Packing tab. This mapping is the reverse of copying shipment
packages onto a Declaration Order.
"""

from __future__ import annotations

DESCRIPTION_LIMIT = 140

_CARGO_TEXT_FIELDS = (
	"goods_description",
	"commodity_code",
	"tariff",
	"product_code",
	"item",
	"reference_no",
)
_CARGO_NUMBER_FIELDS = (
	"invoice_qty",
	"customs_qty",
	"no_of_packs",
	"gross_weight",
	"volume",
	"length",
	"width",
	"height",
)


def _text(value) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _positive(value):
	"""Return a number only when it is greater than zero."""
	if value is None or value == "":
		return None
	try:
		number = float(value)
	except (TypeError, ValueError):
		return None
	if number > 0:
		return number
	return None


def _present(value) -> bool:
	return value is not None and value != ""


def customs_line_has_cargo(line) -> bool:
	"""True when the line item describes goods worth copying."""
	for fieldname in _CARGO_TEXT_FIELDS:
		if _text(getattr(line, fieldname, None)):
			return True
	for fieldname in _CARGO_NUMBER_FIELDS:
		if _positive(getattr(line, fieldname, None)) is not None:
			return True
	return False


def customs_lines_for_transport(declaration, declaration_order=None):
	"""Line items on the declaration, or the linked declaration order when those are empty."""
	lines = list(getattr(declaration, "commercial_invoice_line_items", None) or [])
	if any(customs_line_has_cargo(line) for line in lines):
		return lines
	if declaration_order is not None:
		return list(getattr(declaration_order, "commercial_invoice_line_items", None) or [])
	return lines


def _short_description(line, idx: int) -> str:
	goods = _text(getattr(line, "goods_description", None))
	if goods:
		return goods.split("\n", 1)[0].strip()[:DESCRIPTION_LIMIT]
	for fieldname in ("product_code", "item", "commodity_code", "tariff", "reference_no"):
		label = _text(getattr(line, fieldname, None))
		if label:
			return label[:DESCRIPTION_LIMIT]
	return f"Line item {idx}"


def transport_package_from_customs_line(line, idx: int = 1):
	"""Build one Transport Order Package dict from a commercial invoice line item.

	Weight, length, and height are required on the package row. When the customs
	line does not have them, they are stored as 0 so the transport order can
	still be created and the goods stay visible.
	"""
	if not customs_line_has_cargo(line):
		return None

	row = {"description": _short_description(line, idx)}
	goods = _text(getattr(line, "goods_description", None))
	if goods:
		row["goods_description"] = goods

	commodity = _text(getattr(line, "commodity_code", None))
	if commodity:
		row["commodity"] = commodity
	tariff = _text(getattr(line, "tariff", None))
	if tariff:
		row["hs_code"] = tariff
	reference_no = _text(getattr(line, "reference_no", None))
	if reference_no:
		row["reference_no"] = reference_no

	quantity = _positive(getattr(line, "invoice_qty", None))
	if quantity is None:
		quantity = _positive(getattr(line, "customs_qty", None))
	if quantity is not None:
		row["quantity"] = quantity
	uom = _text(getattr(line, "invoice_qty_uom", None)) or _text(getattr(line, "customs_qty_uom", None))
	if uom:
		row["uom"] = uom

	packs = _positive(getattr(line, "no_of_packs", None))
	if packs is not None:
		row["no_of_packs"] = packs

	if _present(getattr(line, "gross_weight", None)):
		row["weight"] = getattr(line, "gross_weight")
	weight_uom = _text(getattr(line, "gross_weight_uom", None))
	if weight_uom:
		row["weight_uom"] = weight_uom

	if _present(getattr(line, "volume", None)):
		row["volume"] = getattr(line, "volume")
	volume_uom = _text(getattr(line, "volume_uom", None))
	if volume_uom:
		row["volume_uom"] = volume_uom

	for fieldname in ("length", "width", "height"):
		if _present(getattr(line, fieldname, None)):
			row[fieldname] = getattr(line, fieldname)
	dimension_uom = _text(getattr(line, "dimension_uom", None))
	if dimension_uom:
		row["dimension_uom"] = dimension_uom

	for fieldname in ("weight", "length", "height"):
		if not _present(row.get(fieldname)):
			row[fieldname] = 0

	return row
