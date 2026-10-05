# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Air and Sea Sales Quote charges need one complete corridor before submit."""

from __future__ import annotations


def air_sea_corridor_incomplete(charge_ports, doc_origin, doc_dest):
	"""Return True when Air/Sea charges exist and none has both ends.

	``charge_ports`` is ``(origin, destination)`` for each Air or Sea charge.
	A blank row end falls back to the quote origin or destination. An empty
	charge list is complete.
	"""
	ports = list(charge_ports or [])
	if not ports:
		return False
	for origin, destination in ports:
		if (origin or doc_origin) and (destination or doc_dest):
			return False
	return True
