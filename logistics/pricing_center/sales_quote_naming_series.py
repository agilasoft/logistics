# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Quote naming series must match the quotation type."""

from __future__ import annotations


NAMING_SERIES_PREFIXES = {
	"Regular": ("SQU.", "SQU-"),
	"One-off": ("OOQ.", "OOQ-"),
	"Project": ("PQ.", "PQ-"),
}

NAMING_SERIES_EXAMPLES = {
	"Regular": "SQU.#########",
	"One-off": "OOQ.#####",
	"Project": "PQ.#####",
}


def naming_series_mismatch(quotation_type, naming_series):
	"""Return the expected prefix text when the series does not match.

	An empty type, an empty series, and an unknown type are accepted.
	Dot and hyphen prefixes are both accepted.
	"""
	if not quotation_type or not naming_series:
		return None
	prefixes = NAMING_SERIES_PREFIXES.get(quotation_type)
	if not prefixes:
		return None
	if any(naming_series.startswith(prefix) for prefix in prefixes):
		return None
	return {
		"expected_display": " / ".join(prefixes),
		"expected_example": NAMING_SERIES_EXAMPLES.get(quotation_type, ""),
	}
