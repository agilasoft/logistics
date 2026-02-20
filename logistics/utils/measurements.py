# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Global measurements API for the logistics module.

Single source for:
- Default and base UOMs: Logistics Settings only.
- All conversion logic: UOM Conversion Factor (dimension/volume/weight) and
  Dimension Volume UOM Conversion (dimension → volume from L×W×H).

When users change UOM on transaction docs, use convert_measurements_to_uom
to preserve physical quantity.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from typing import Optional, Dict, Any, Literal

UOM_TYPE = Literal["dimension", "volume", "weight", "chargeable_weight"]


class ConversionNotFoundError(Exception):
	"""Raised when a conversion factor cannot be found in Dimension Volume UOM Conversion."""
	pass


def get_base_uoms() -> Dict[str, Optional[str]]:
	"""
	Return base UOMs from Logistics Settings (pivot for conversions and reporting).

	Returns:
		Dict with keys: dimension, volume, weight. Values may be None if not set.
	"""
	out = {"dimension": None, "volume": None, "weight": None}
	try:
		settings = frappe.get_single("Logistics Settings")
		out["dimension"] = getattr(settings, "base_dimension_uom", None) or None
		out["volume"] = getattr(settings, "base_volume_uom", None) or None
		out["weight"] = getattr(settings, "base_weight_uom", None) or None
	except Exception:
		pass
	return out


def get_default_uoms(company: Optional[str] = None) -> Dict[str, Optional[str]]:
	"""
	Return default UOMs for new transaction lines from Logistics Settings only.
	No fallbacks: dimension, volume, and weight must be set in Logistics Settings.

	Returns:
		Dict with keys: dimension, volume, weight, chargeable_weight.
	"""
	settings = frappe.get_single("Logistics Settings")
	out = {
		"dimension": getattr(settings, "default_dimension_uom", None) or None,
		"volume": getattr(settings, "default_volume_uom", None) or None,
		"weight": getattr(settings, "default_weight_uom", None) or None,
		"chargeable_weight": getattr(settings, "default_chargeable_weight_uom", None) or None,
	}
	missing = []
	if not out["dimension"]:
		missing.append(_("Default Dimension UOM"))
	if not out["volume"]:
		missing.append(_("Default Volume UOM"))
	if not out["weight"]:
		missing.append(_("Default Weight UOM"))
	if missing:
		frappe.throw(
			_("Logistics Settings: please set {0}.").format(", ".join(missing)),
			title=_("UOM Required"),
		)
	return out


def get_aggregation_volume_uom(company: Optional[str] = None) -> Optional[str]:
	"""
	Return the volume UOM to use when aggregating package volumes (e.g. for chargeable weight).
	Uses Logistics Settings: base_volume_uom if set, else default_volume_uom.
	Callers must use UOM Conversion Factor to convert package volumes to this UOM.
	"""
	base = get_base_uoms()
	if base.get("volume"):
		return base["volume"]
	defaults = get_default_uoms(company=company)
	return defaults.get("volume")


def _normalize_uom_alias(uom: str) -> str:
	"""
	Normalize UOM aliases to their canonical form.
	Handles common abbreviations and variations (e.g., CBM -> CUBIC METER).
	"""
	if not uom:
		return uom
	uom = str(uom).strip().upper()
	
	# Common UOM aliases mapping
	aliases = {
		# Volume aliases
		"CBM": "CUBIC METER",
		"M³": "CUBIC METER",
		"M3": "CUBIC METER",
		"CUBIC M": "CUBIC METER",
		"CU M": "CUBIC METER",
		"CU.M": "CUBIC METER",
		"CFT": "CUBIC FOOT",
		"CU FT": "CUBIC FOOT",
		"CUBIC FT": "CUBIC FOOT",
		"CU.FT": "CUBIC FOOT",
		"L": "LITER",
		"LITRE": "LITER",
		# Dimension aliases
		"CM": "CENTIMETER",
		"MM": "MILLIMETER",
		"M": "METER",
		"METRE": "METER",
		"IN": "INCH",
		"INCHES": "INCH",
		"FT": "FOOT",
		"FEET": "FOOT",
		# Weight aliases
		"KG": "KILOGRAM",
		"KGS": "KILOGRAM",
		"G": "GRAM",
		"GR": "GRAM",
		"LB": "POUND",
		"LBS": "POUND",
	}
	
	# Return normalized alias if found, otherwise return original
	return aliases.get(uom, uom)


def get_uom_conversion_factor(from_uom: str, to_uom: str) -> float:
	"""
	Conversion factor between two UOMs from UOM Conversion Factor (Frappe).
	Multiply source value by this to get target value.
	Handles common UOM aliases (e.g., CBM = CUBIC METER).
	"""
	if not from_uom or not to_uom:
		return 1.0
	from_uom = str(from_uom).strip().upper()
	to_uom = str(to_uom).strip().upper()
	
	# Normalize aliases to canonical form
	from_uom_normalized = _normalize_uom_alias(from_uom)
	to_uom_normalized = _normalize_uom_alias(to_uom)
	
	# If normalized forms are the same, they're the same unit
	if from_uom_normalized == to_uom_normalized:
		return 1.0
	
	# Use normalized forms for database lookup
	from_uom = from_uom_normalized
	to_uom = to_uom_normalized
	try:
		conversion = frappe.db.get_value(
			"UOM Conversion Factor",
			{"from_uom": from_uom, "to_uom": to_uom},
			"value",
			as_dict=True,
		)
		if conversion and conversion.get("value"):
			return flt(conversion.get("value"))
	except Exception:
		pass
	try:
		conversion = frappe.db.get_value(
			"UOM Conversion Factor",
			{"from_uom": to_uom, "to_uom": from_uom},
			"value",
			as_dict=True,
		)
		if conversion and conversion.get("value"):
			return 1.0 / flt(conversion.get("value"))
	except Exception:
		pass
	frappe.throw(
		_("UOM conversion not found: {0} to {1}. Please add a UOM Conversion Factor record.").format(
			from_uom, to_uom
		),
		title=_("Conversion Not Found"),
	)


def get_volume_conversion_factor(
	dimension_uom: str,
	volume_uom: str,
	company: Optional[str] = None,
) -> float:
	"""
	Conversion factor from (dimension_uom)³ to volume_uom from Dimension Volume UOM Conversion.
	Multiply raw_volume (L×W×H in dimension_uom) by this to get volume in volume_uom.
	"""
	if not dimension_uom or not volume_uom:
		raise ConversionNotFoundError(_("Dimension UOM and Volume UOM are required"))
	dim_uom = (dimension_uom or "").strip()
	vol_uom = (volume_uom or "").strip()
	if dim_uom.upper() == vol_uom.upper():
		return 1.0
	# Query by UOM name as stored (Link to UOM stores doc name e.g. "Centimeter", "Cubic Meter")
	conversion = None
	try:
		conversion = frappe.db.get_value(
			"Dimension Volume UOM Conversion",
			{"dimension_uom": dim_uom, "volume_uom": vol_uom, "enabled": 1},
			"conversion_factor",
			as_dict=True,
		)
	except (frappe.DoesNotExistError, frappe.ValidationError):
		pass
	except Exception as e:
		frappe.log_error(
			_("Unexpected error fetching conversion: {0}").format(str(e)),
			"Volume Conversion Database Error",
		)
	if conversion and conversion.get("conversion_factor"):
		return flt(conversion.get("conversion_factor"))
	raise ConversionNotFoundError(
		_("No conversion factor found from {0} to {1}. Please create a Dimension Volume UOM Conversion record.").format(
			dimension_uom, volume_uom
		)
	)


def _get_uom_conversion_factor(from_uom: str, to_uom: str) -> float:
	"""Alias for get_uom_conversion_factor (UOM Conversion Factor table)."""
	return get_uom_conversion_factor(from_uom, to_uom)


def convert_dimension(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""Convert a dimension value (length/width/height). Uses UOM Conversion Factor."""
	if value is None or value == 0:
		return 0.0
	value = flt(value)
	defaults = get_default_uoms(company)
	from_uom = from_uom or defaults.get("dimension")
	to_uom = to_uom or defaults.get("dimension")
	if not from_uom or not to_uom:
		frappe.throw(
			_("Dimension UOM is required. Set default in Logistics Settings or pass from_uom and to_uom."),
			title=_("UOM Required"),
		)
	if str(from_uom).strip().upper() == str(to_uom).strip().upper():
		return value
	factor = _get_uom_conversion_factor(from_uom, to_uom)
	return value * factor


def convert_volume(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""Convert a volume value. Uses UOM Conversion Factor (or Dimension Volume UOM Conversion for dimension³→volume)."""
	if value is None or value == 0:
		return 0.0
	value = flt(value)
	defaults = get_default_uoms(company)
	from_uom = from_uom or defaults.get("volume")
	to_uom = to_uom or defaults.get("volume")
	if not from_uom or not to_uom:
		frappe.throw(
			_("Volume UOM is required. Set default in Logistics Settings or pass from_uom and to_uom."),
			title=_("UOM Required"),
		)
	if str(from_uom).strip().upper() == str(to_uom).strip().upper():
		return value
	factor = _get_uom_conversion_factor(from_uom, to_uom)
	return value * factor


def convert_weight(
	value: float,
	from_uom: Optional[str] = None,
	to_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""Convert a weight value. Uses UOM Conversion Factor."""
	if value is None or value == 0:
		return 0.0
	value = flt(value)
	defaults = get_default_uoms(company)
	from_uom = from_uom or defaults.get("weight")
	to_uom = to_uom or defaults.get("weight")
	if not from_uom or not to_uom:
		frappe.throw(
			_("Weight UOM is required. Set default in Logistics Settings or pass from_uom and to_uom."),
			title=_("UOM Required"),
		)
	if str(from_uom).strip().upper() == str(to_uom).strip().upper():
		return value
	factor = _get_uom_conversion_factor(from_uom, to_uom)
	return value * factor


def compute_density_factor(
	volume: float,
	weight: float,
	volume_uom: Optional[str] = None,
	weight_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> Optional[float]:
	"""
	Compute density factor as volume/weight in cm³ per kg (for freight: 1 = dense, 6000 = volumetric).
	Uses base volume UOM (treated as m³) and base weight UOM (treated as kg) from Logistics Settings
	when volume_uom/weight_uom are not provided (e.g. header aggregates).
	Returns None if weight is zero or missing.
	"""
	volume = flt(volume, 0)
	weight = flt(weight, 0)
	if not weight or weight <= 0:
		return None
	try:
		base = get_base_uoms()
		vol_uom = volume_uom or base.get("volume")
		wt_uom = weight_uom or base.get("weight")
		if not vol_uom:
			defaults = get_default_uoms(company=company)
			vol_uom = defaults.get("volume")
		if not wt_uom:
			defaults = get_default_uoms(company=company)
			wt_uom = defaults.get("weight")
		if not vol_uom or not wt_uom:
			return None
		volume_in_base = convert_volume(
			volume, from_uom=volume_uom or vol_uom, to_uom=vol_uom, company=company
		) if volume else 0
		weight_in_base = convert_weight(
			weight, from_uom=weight_uom or wt_uom, to_uom=wt_uom, company=company
		) if weight else 0
		if not weight_in_base:
			return None
		# Base volume UOM is assumed to be m³ (e.g. CBM); 1 m³ = 1e6 cm³
		volume_cm3 = volume_in_base * 1e6
		return volume_cm3 / weight_in_base
	except Exception:
		return None


def calculate_volume_from_dimensions(
	length: float,
	width: float,
	height: float,
	dimension_uom: Optional[str] = None,
	volume_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> float:
	"""
	Calculate volume from length, width, height using Dimension Volume UOM Conversion.
	UOMs from document or Logistics Settings (get_default_uoms(company)) when not provided.
	"""
	if not length or not width or not height:
		return 0.0
	length = flt(length)
	width = flt(width)
	height = flt(height)
	if length <= 0 or width <= 0 or height <= 0:
		return 0.0
	if not dimension_uom or not volume_uom:
		defaults = get_default_uoms(company)
		dimension_uom = dimension_uom or defaults.get("dimension")
		volume_uom = volume_uom or defaults.get("volume")
	if not dimension_uom or not volume_uom:
		frappe.throw(
			_("Dimension UOM and Volume UOM are required for volume calculation. Set them or configure Logistics Settings."),
			title=_("UOM Required"),
		)
	raw_volume = length * width * height
	factor = get_volume_conversion_factor(dimension_uom, volume_uom, company)
	return raw_volume * factor


def convert_measurements_to_uom(
	doc: Any,
	uom_type: UOM_TYPE,
	new_uom: str,
	old_uom: Optional[str] = None,
	company: Optional[str] = None,
) -> None:
	"""
	Convert measurement numeric fields to a new UOM and set the UOM field.
	Preserves physical quantity: new_value = old_value * factor(old_uom -> new_uom).
	Modifies doc in place (supports frappe document or dict with [] access).

	Args:
		doc: Document or dict with measurement fields (length, width, height, volume, weight, chargeable_weight, and corresponding _uom fields).
		uom_type: One of "dimension", "volume", "weight", "chargeable_weight".
		new_uom: Target UOM to convert to.
		old_uom: Current UOM (if None, read from doc's dimension_uom/volume_uom/weight_uom/chargeable_weight_uom).
		company: Optional company for default UOMs.
	"""
	if not new_uom:
		return
	def _get(key: str):
		if hasattr(doc, "get") and not hasattr(doc, "db_update"):
			return doc.get(key)
		return getattr(doc, key, None)

	def _set(key: str, val: Any):
		if hasattr(doc, "db_update") or hasattr(doc, "save"):
			setattr(doc, key, val)
		elif hasattr(doc, "__setitem__"):
			doc[key] = val
		else:
			setattr(doc, key, val)

	if uom_type == "dimension":
		old = old_uom or _get("dimension_uom")
		if not old or str(old).strip().upper() == str(new_uom).strip().upper():
			_set("dimension_uom", new_uom)
			return
		factor = _get_uom_conversion_factor(old, new_uom)
		for field in ("length", "width", "height"):
			v = _get(field)
			if v is not None and flt(v) != 0:
				_set(field, flt(v) * factor)
		_set("dimension_uom", new_uom)

	elif uom_type == "volume":
		old = old_uom or _get("volume_uom")
		if not old or str(old).strip().upper() == str(new_uom).strip().upper():
			_set("volume_uom", new_uom)
			return
		v = _get("volume")
		if v is not None and flt(v) != 0:
			factor = _get_uom_conversion_factor(old, new_uom)
			_set("volume", flt(v) * factor)
		_set("volume_uom", new_uom)

	elif uom_type == "weight":
		old = old_uom or _get("weight_uom")
		if not old or str(old).strip().upper() == str(new_uom).strip().upper():
			_set("weight_uom", new_uom)
			return
		v = _get("weight")
		if v is not None and flt(v) != 0:
			factor = _get_uom_conversion_factor(old, new_uom)
			_set("weight", flt(v) * factor)
		_set("weight_uom", new_uom)

	elif uom_type == "chargeable_weight":
		old = old_uom or _get("chargeable_weight_uom")
		if not old or str(old).strip().upper() == str(new_uom).strip().upper():
			_set("chargeable_weight_uom", new_uom)
			return
		v = _get("chargeable_weight")
		if v is not None and flt(v) != 0:
			factor = _get_uom_conversion_factor(old, new_uom)
			_set("chargeable_weight", flt(v) * factor)
		_set("chargeable_weight_uom", new_uom)

	else:
		frappe.throw(_("Invalid uom_type: {0}").format(uom_type), title=_("Invalid Argument"))


def apply_measurement_uom_conversion_to_children(
	doc: Any,
	child_table_fieldname: str,
	company: Optional[str] = None,
) -> None:
	"""
	When saving a document, convert child table measurement values if UOM was changed
	compared to DB (e.g. after import or API change). Call from parent's validate().

	Args:
		doc: Parent document with a child table (e.g. Transport Order with packages).
		child_table_fieldname: Field name of the child table (e.g. "packages").
		company: Optional company for default UOMs.
	"""
	children = getattr(doc, child_table_fieldname, None) or []
	if not children or not doc.get("name"):
		return
	try:
		existing = frappe.get_doc(doc.doctype, doc.name)
	except Exception:
		return
	existing_children = getattr(existing, child_table_fieldname, None) or []
	existing_by_name = {c.name: c for c in existing_children if c.get("name")}
	for row in children:
		name = row.get("name")
		if not name or str(name).startswith("new"):
			continue
		old_row = existing_by_name.get(name)
		if not old_row:
			continue
		for uom_type, uom_field in (
			("dimension", "dimension_uom"),
			("volume", "volume_uom"),
			("weight", "weight_uom"),
			("chargeable_weight", "chargeable_weight_uom"),
		):
			new_uom = row.get(uom_field)
			old_uom = old_row.get(uom_field)
			if not new_uom or new_uom == old_uom:
				continue
			convert_measurements_to_uom(row, uom_type, new_uom, old_uom=old_uom, company=company)


@frappe.whitelist()
def get_default_uoms_api(company: Optional[str] = None) -> Dict[str, Optional[str]]:
	"""Whitelisted API for client scripts to fetch default UOMs."""
	return get_default_uoms(company=company)


@frappe.whitelist()
def get_base_uoms_api() -> Dict[str, Optional[str]]:
	"""Whitelisted API for client scripts to fetch base UOMs."""
	return get_base_uoms()


@frappe.whitelist()
def get_converted_measurements_for_uom_change(
	uom_type: str,
	old_uom: str,
	new_uom: str,
	length: Optional[float] = None,
	width: Optional[float] = None,
	height: Optional[float] = None,
	volume: Optional[float] = None,
	weight: Optional[float] = None,
	chargeable_weight: Optional[float] = None,
) -> Dict[str, Any]:
	"""
	Return converted numeric values when user changes UOM (for client-side use).
	Preserves physical quantity: new_value = old_value * factor(old_uom -> new_uom).
	"""
	if not old_uom or not new_uom or str(old_uom).strip().upper() == str(new_uom).strip().upper():
		return {}
	uom_type = (uom_type or "").strip().lower()
	if uom_type not in ("dimension", "volume", "weight", "chargeable_weight"):
		return {}
	factor = _get_uom_conversion_factor(old_uom, new_uom)
	out = {}
	if uom_type == "dimension":
		for key in ("length", "width", "height"):
			val = length if key == "length" else (width if key == "width" else height)
			if val is not None and flt(val) != 0:
				out[key] = flt(val) * factor
	if uom_type == "volume" and volume is not None and flt(volume) != 0:
		out["volume"] = flt(volume) * factor
	if uom_type == "weight" and weight is not None and flt(weight) != 0:
		out["weight"] = flt(weight) * factor
	if uom_type == "chargeable_weight" and chargeable_weight is not None and flt(chargeable_weight) != 0:
		out["chargeable_weight"] = flt(chargeable_weight) * factor
	return out


@frappe.whitelist()
def convert_measurements_to_uom_api(
	doctype: str,
	docname: str,
	uom_type: str,
	new_uom: str,
	old_uom: Optional[str] = None,
	company: Optional[str] = None,
	child_doctype: Optional[str] = None,
	child_name: Optional[str] = None,
) -> None:
	"""
	Server API: load doc (or child row), run convert_measurements_to_uom, save.
	If child_doctype/child_name are set, load the child table row and convert there.
	"""
	uom_type = uom_type.strip().lower()
	if uom_type not in ("dimension", "volume", "weight", "chargeable_weight"):
		frappe.throw(_("Invalid uom_type."), title=_("Invalid Argument"))
	if child_doctype and child_name:
		child = frappe.get_doc(child_doctype, child_name)
		convert_measurements_to_uom(child, uom_type, new_uom, old_uom=old_uom, company=company)
		child.db_update()
	else:
		doc = frappe.get_doc(doctype, docname)
		convert_measurements_to_uom(doc, uom_type, new_uom, old_uom=old_uom, company=company)
		doc.save(ignore_permissions=True)


@frappe.whitelist()
def calculate_volume_from_dimensions_api(
	length, width, height, dimension_uom=None, volume_uom=None, company=None
) -> Dict[str, Any]:
	"""
	Whitelisted API: calculate volume from dimensions (for client scripts).
	Uses Dimension Volume UOM Conversion. Returns dict with "volume" key; on error returns "error" key.
	"""
	try:
		volume = calculate_volume_from_dimensions(
			length=float(length) if length else 0,
			width=float(width) if width else 0,
			height=float(height) if height else 0,
			dimension_uom=dimension_uom,
			volume_uom=volume_uom,
			company=company,
		)
		return {"volume": volume}
	except ConversionNotFoundError as e:
		return {"volume": 0, "error": str(e)}
	except Exception as e:
		frappe.log_error(title="Volume from dimensions API", message=frappe.get_traceback())
		return {"volume": 0, "error": str(e)}
