# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""AWB number helpers for CASSLink matching."""

from __future__ import unicode_literals

import re
from typing import List, Optional

_NON_DIGIT = re.compile(r"\D+")


def digits_only(value: Optional[str]) -> str:
	return _NON_DIGIT.sub("", value or "")


def normalize_awb(value: Optional[str], prefix: Optional[str] = None) -> str:
	"""Return an 11-digit AWB (3-digit prefix + 8-digit serial) when possible."""
	serial = digits_only(value)
	pfx = digits_only(prefix)
	if len(serial) >= 11:
		return serial[:11]
	if len(serial) == 8 and len(pfx) >= 3:
		return pfx[-3:] + serial
	if len(serial) == 10 and len(pfx) >= 3:
		return (pfx[-3:] + serial)[:11]
	if len(serial) == 8:
		return serial
	return serial


def format_awb_display(awb: Optional[str]) -> str:
	d = digits_only(awb)
	if len(d) == 11:
		return f"{d[:3]}-{d[3:]}"
	return (awb or "").strip()


def awb_lookup_candidates(awb: Optional[str], prefix: Optional[str] = None) -> List[str]:
	"""Distinct strings that may be stored on MAWB / Air Shipment."""
	normalized = normalize_awb(awb, prefix)
	out = []
	for candidate in (
		(awb or "").strip(),
		normalized,
		format_awb_display(normalized),
		digits_only(awb),
	):
		if candidate and candidate not in out:
			out.append(candidate)
	return out
