# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import xml.etree.ElementTree as ET
from typing import Any, Iterable, List, Optional


def add_special_handling_codes(parent: ET.Element, codes: Iterable[str]) -> None:
	shc_parent = ET.SubElement(parent, "SpecialHandlingCodes")
	for code in codes:
		code = (code or "").strip().upper()
		if code:
			item = ET.SubElement(shc_parent, "SpecialHandlingCode")
			item.set("Code", code)


def add_oci_security(parent: ET.Element, packages: List[Any]) -> None:
	"""Add e-CSD / OCI security declaration entries from package DG/security fields."""
	oci = ET.SubElement(parent, "OtherCustomsInformation")
	for pkg in packages:
		if not getattr(pkg, "dg_substance", None) and not getattr(pkg, "un_number", None):
			continue
		entry = ET.SubElement(oci, "OCIEntry")
		entry.set("CountryCode", "XX")
		entry.set("InformationIdentifier", "CSD")
		entry.set("ControlInformation", "SECURITY")
		if getattr(pkg, "un_number", None):
			entry.set("SupplementaryInformation", str(pkg.un_number))
		if getattr(pkg, "dg_class", None):
			entry.set("Note", f"Class {pkg.dg_class}")


def add_charges(parent: ET.Element, charges: List[Any]) -> None:
	if not charges:
		return
	charges_elem = ET.SubElement(parent, "Charges")
	total = 0.0
	for charge in charges:
		amount = float(getattr(charge, "base_amount", None) or getattr(charge, "amount", 0) or 0)
		if not amount:
			continue
		row = ET.SubElement(charges_elem, "Charge")
		row.set("Code", getattr(charge, "charge_code", None) or getattr(charge, "item_code", None) or "FREIGHT")
		row.set("Amount", str(amount))
		row.set("Currency", getattr(charge, "currency", None) or "USD")
		total += amount
	charges_elem.set("TotalAmount", str(total))
