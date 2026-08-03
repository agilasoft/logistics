# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

_WORD_SPLIT = re.compile(r"[^A-Za-z0-9]+")
_VOWELS = set("AEIOU")
_STOP_WORDS = frozenset({"AND", "OF", "THE", "FOR", "TO", "A", "AN", "&"})


def abbreviate_word(word: str) -> str:
	"""Compress one word for the item-code abbreviation.

	Words with 3 or fewer characters are kept as-is (uppercased).
	Longer words keep the first letter, drop vowels from the rest, then
	truncate to a maximum of 4 characters.
	"""
	word = (word or "").upper()
	if not word:
		return ""
	if len(word) <= 3:
		return word
	rest = "".join(ch for ch in word[1:] if ch not in _VOWELS)
	return (word[0] + rest)[:4]


def abbreviate_item_name(item_name: str | None) -> str:
	"""Build the hyphenated item abbreviation from an Item Name."""
	parts: list[str] = []
	for raw in _WORD_SPLIT.split(item_name or ""):
		token = raw.upper()
		if not token or token in _STOP_WORDS:
			continue
		abbr = abbreviate_word(token)
		if abbr:
			parts.append(abbr)
	return "-".join(parts) or "ITEM"


def build_item_code(customer_code: str | None, item_name: str | None) -> str:
	"""Format ``<CUSTOMER_CODE>-<ABBREVIATED_ITEM_NAME>``."""
	customer = (customer_code or "").strip().upper() or "ITEM"
	return f"{customer}-{abbreviate_item_name(item_name)}"


def ensure_unique_item_code(
	base: str,
	customer: str,
	doc_name: str | None,
) -> str:
	"""Keep ``code`` unique within the same customer; append -2, -3, … on collision."""
	base = (base or "ITEM").strip() or "ITEM"
	candidate = base
	seq = 1
	while True:
		filters: dict = {"code": candidate, "customer": customer}
		if doc_name:
			filters["name"] = ["!=", doc_name]
		if not frappe.db.exists("Warehouse Item", filters):
			return candidate
		seq += 1
		if seq > 999:
			frappe.throw(
				_("Could not allocate a unique item code after many attempts; adjust the Item Name."),
				title=_("Item Code"),
			)
		candidate = f"{base}-{seq}"


@frappe.whitelist()
def suggest_warehouse_item_code(
	item_name: str | None = None,
	customer: str | None = None,
	customer_code: str | None = None,
	doc_name: str | None = None,
) -> str:
	"""Return a unique suggested Code for the given customer and item name."""
	if not (item_name or "").strip():
		frappe.throw(_("Item Name is required to generate Item Code."), title=_("Item Code"))
	if not customer:
		frappe.throw(_("Customer is required to generate Item Code."), title=_("Item Code"))

	code_prefix = (customer_code or "").strip()
	if not code_prefix:
		code_prefix = frappe.db.get_value("Customer", customer, "logistics_party_code") or ""

	base = build_item_code(code_prefix, item_name)
	return ensure_unique_item_code(base, customer, doc_name or None)


class WarehouseItem(Document):
	def before_insert(self):
		# Autoname is ``{code}`` and runs after before_insert.
		self.ensure_customer_code()
		self.maybe_set_item_code()

	def validate(self):
		self.ensure_customer_code()
		self.maybe_set_item_code()
		self.validate_volume_calculation()
		self.validate_tracking_exclusivity()

	def ensure_customer_code(self):
		"""Fill ``customer_code`` from Customer when missing (needed for autoname / API creates)."""
		if not self.customer:
			return
		if (self.customer_code or "").strip():
			return
		self.customer_code = (
			frappe.db.get_value("Customer", self.customer, "logistics_party_code") or ""
		)

	def maybe_set_item_code(self):
		"""Auto-generate ``code`` from Customer Code + abbreviated Item Name when blank."""
		if (self.code or "").strip():
			self.validate_item_code_unique()
			return
		if not (self.item_name or "").strip():
			frappe.throw(_("Item Name is required to generate Item Code."), title=_("Item Code"))
		if not self.customer:
			frappe.throw(_("Customer is required to generate Item Code."), title=_("Item Code"))
		base = build_item_code(self.customer_code, self.item_name)
		self.code = ensure_unique_item_code(base, self.customer, self.name)

	def validate_item_code_unique(self):
		"""Reject a manually entered code that already exists for this customer."""
		if not self.code or not self.customer:
			return
		filters: dict = {"code": self.code, "customer": self.customer}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("Warehouse Item", filters):
			frappe.throw(
				_("Item Code {0} already exists for this customer.").format(frappe.bold(self.code)),
				title=_("Duplicate Item Code"),
			)

	def validate_volume_calculation(self):
		"""Validate that volume matches calculated volume from dimensions"""
		if self.length and self.width and self.height:
			from logistics.warehousing.utils.volume_conversion import calculate_volume_from_dimensions

			# Get UOMs from item or warehouse settings
			dimension_uom = getattr(self, "dimension_uom", None)
			volume_uom = getattr(self, "volume_uom", None)

			# Get defaults from warehouse settings if not in item
			# Try to get company from customer if available
			company = None
			if not dimension_uom or not volume_uom:
				try:
					if self.customer:
						# Try to get company from customer's default company
						customer_doc = frappe.get_cached_doc("Customer", self.customer)
						company = customer_doc.default_company

					if company:
						warehouse_settings = frappe.get_cached_doc("Warehouse Settings", company)
						if not dimension_uom:
							dimension_uom = warehouse_settings.default_dimension_uom
						if not volume_uom:
							volume_uom = warehouse_settings.default_volume_uom
				except Exception:
					pass

			calculated_volume = calculate_volume_from_dimensions(
				length=self.length,
				width=self.width,
				height=self.height,
				dimension_uom=dimension_uom,
				volume_uom=volume_uom,
				company=company,
			)

			# If volume is provided, check if it matches calculated volume (with tolerance for UOM conversion)
			if self.volume:
				entered_volume = flt(self.volume)
				calculated_vol = flt(calculated_volume)

				# Check for potential unit mismatch (difference is more than 1000x)
				# This suggests the entered volume might be in a different unit
				if entered_volume > 0 and calculated_vol > 0:
					ratio1 = entered_volume / calculated_vol
					ratio2 = calculated_vol / entered_volume
					if ratio1 > 1000 or ratio2 > 1000:
						frappe.msgprint(
							_(
								"Volume ({0}) appears to be in a different unit than calculated volume ({1}). Please verify the volume UOM settings or clear the volume field to auto-calculate."
							).format(entered_volume, calculated_vol),
							title=_("Volume Unit Mismatch"),
							indicator="orange",
						)
					# Normal validation with tolerance (only if not a unit mismatch)
					elif abs(entered_volume - calculated_vol) > 0.001:
						# Use relative tolerance for large volumes, absolute tolerance for small volumes
						relative_diff = abs(entered_volume - calculated_vol) / max(abs(calculated_vol), 1.0)
						if relative_diff > 0.01:  # 1% tolerance
							frappe.msgprint(
								_(
									"Volume ({0}) does not match calculated volume ({1}) from dimensions. Please verify your entries."
								).format(entered_volume, calculated_vol),
								title=_("Volume Mismatch"),
								indicator="orange",
							)
				elif entered_volume != calculated_vol:
					# Handle case where one volume is zero or negative
					frappe.msgprint(
						_(
							"Volume ({0}) does not match calculated volume ({1}) from dimensions. Please verify your entries."
						).format(entered_volume, calculated_vol),
						title=_("Volume Mismatch"),
						indicator="orange",
					)
			elif not self.volume:
				# Auto-calculate volume if not provided
				self.volume = calculated_volume

	def validate_tracking_exclusivity(self):
		"""Validate that batch tracking and serial tracking cannot both be enabled"""
		if self.batch_tracking and self.serial_tracking:
			frappe.throw(
				_(
					"Batch Tracking and Serial Tracking cannot both be enabled. Please enable only one tracking method."
				),
				title=_("Invalid Tracking Configuration"),
			)
