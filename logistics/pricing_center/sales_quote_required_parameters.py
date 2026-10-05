# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Required Sales Quote scope fields, as field names in form order."""

from __future__ import annotations


_AIR_SEA = ("origin_port", "destination_port")
_TRANSPORT = ("location_type", "location_from", "location_to")
_MICE = ("exhibit", "exhibit_show_open_date", "exhibit_show_close_date")

_ONE_OFF_FIELDS = {
	"Air": _AIR_SEA,
	"Sea": _AIR_SEA,
	"Transport": _TRANSPORT,
	"MICE": _MICE,
}


def _present(fieldname, value):
	if fieldname == "exhibit":
		if value is None:
			return False
		return bool(str(value).strip())
	return bool(value)


def _missing(fieldnames, values):
	return [name for name in fieldnames if not _present(name, values.get(name))]


def missing_one_off_scope_fields(quotation_type, main_service, additional_charge, values):
	"""Fields required on Regular and One-off quotes for the main service.

	Additional-charge quotes and other quotation types return an empty list.
	"""
	if quotation_type not in ("One-off", "Regular"):
		return []
	if additional_charge:
		return []
	fieldnames = _ONE_OFF_FIELDS.get(main_service)
	if not fieldnames:
		return []
	return _missing(fieldnames, values)


def missing_programme_scope_fields(main_service, additional_charge, values):
	"""Programme header fields. MICE requires the show link and dates."""
	if additional_charge:
		return []
	if main_service != "MICE":
		return []
	return _missing(_MICE, values)
