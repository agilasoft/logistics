# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Default House AWB / House BL from shipment ID for export freight jobs."""

from __future__ import annotations

EXPORT_DIRECTION = "Export"

HOUSE_DOCUMENT_FIELD_BY_DOCTYPE = {
	"Air Shipment": "house_awb",
	"Sea Shipment": "house_bl",
}


def _is_empty(value) -> bool:
	if value is None:
		return True
	if isinstance(value, str) and not value.strip():
		return True
	return False


def auto_populate_export_house_document_from_shipment_id(doc) -> bool:
	"""Fill empty House AWB / House BL with the shipment document name for Export jobs."""
	fieldname = HOUSE_DOCUMENT_FIELD_BY_DOCTYPE.get(getattr(doc, "doctype", None))
	if not fieldname or not doc.meta.has_field(fieldname):
		return False
	if (getattr(doc, "direction", None) or "").strip() != EXPORT_DIRECTION:
		return False
	if not _is_empty(getattr(doc, fieldname, None)):
		return False
	if not getattr(doc, "name", None):
		return False

	doc.set(fieldname, doc.name)
	return True
