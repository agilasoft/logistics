# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
ISO 6346 Container Number Validation

Container numbers must conform to ISO 6346:
- 11 characters: 3-letter owner code + 1 category (U/J/Z) + 6-digit serial + 1 check digit
"""

from __future__ import unicode_literals

import re
import frappe
from frappe import _


# ISO 6346: Letter to numeric value (A=10, B=12, ... Z=38; I,O,Q omitted)
_LETTER_VALUES = {
    "A": 10, "B": 12, "C": 13, "D": 14, "E": 15, "F": 16, "G": 17, "H": 18,
    "I": 19, "J": 20, "K": 21, "L": 23, "M": 24, "N": 25, "O": 26, "P": 27,
    "Q": 28, "R": 29, "S": 30, "T": 31, "U": 32, "V": 34, "W": 35, "X": 36,
    "Y": 37, "Z": 38,
}


def normalize_container_number(value):
	"""Strip spaces, hyphens; convert to uppercase."""
	if not value or not isinstance(value, str):
		return ""
	return re.sub(r"[\s\-]", "", str(value).strip().upper())


def validate_container_number_format(container_no):
	"""
	Validate format only: length, owner code, category, serial.
	Returns (is_valid, error_message).
	"""
	container_no = normalize_container_number(container_no)
	if not container_no:
		return False, _("Container number is required")
	if len(container_no) != 11:
		return False, _("Container number must be exactly 11 characters (ISO 6346)")
	# Owner code: 3 letters
	if not container_no[:3].isalpha():
		return False, _("First 3 characters must be letters (owner code)")
	# Category: U, J, or Z
	if container_no[3] not in ("U", "J", "Z"):
		return False, _("4th character must be U (freight), J (equipment), or Z (trailer)")
	# Serial: 6 digits
	if not container_no[4:10].isdigit():
		return False, _("Characters 5-10 must be digits (serial number)")
	# Check digit: 1 digit
	if not container_no[10].isdigit():
		return False, _("11th character must be a digit (check digit)")
	return True, None


def calculate_iso6346_check_digit(container_no):
	"""
	Calculate ISO 6346 check digit for first 10 characters.
	Returns 0-9.
	"""
	container_no = normalize_container_number(container_no)
	if len(container_no) < 10:
		return None
	total = 0
	for i, c in enumerate(container_no[:10]):
		if c.isalpha():
			val = _LETTER_VALUES.get(c.upper())
			if val is None:
				return None
		else:
			val = int(c)
		total += val * (2 ** i)
	remainder = total % 11
	if remainder == 10:
		return 0
	return remainder


def validate_container_number(container_no, strict=True, allow_bypass=False):
	"""
	Validate container number per ISO 6346.
	:param container_no: Container number string
	:param strict: If True, validate check digit; if False, format only
	:param allow_bypass: If True and user has permission, skip validation (for admin override)
	:returns: (is_valid, error_message)
	"""
	if allow_bypass and frappe.has_permission("Logistics Settings", "write"):
		return True, None

	container_no = normalize_container_number(container_no)
	valid_format, err = validate_container_number_format(container_no)
	if not valid_format:
		return False, err

	if not strict:
		return True, None

	expected = calculate_iso6346_check_digit(container_no)
	if expected is None:
		return False, _("Invalid container number format")
	actual = int(container_no[10])
	if actual != expected:
		return False, _("Container number check digit is invalid (expected {0}, got {1})").format(
			expected, actual
		)
	return True, None


def get_strict_validation_setting():
	"""Get strict_container_validation from Logistics Settings."""
	try:
		settings = frappe.get_single("Logistics Settings")
		return getattr(settings, "strict_container_validation", True)
	except Exception:
		return True
