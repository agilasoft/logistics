# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Default Sales Quote scope title from the corridor and incoterm."""

from __future__ import annotations


def _strip(val):
	if val is None:
		return None
	text = str(val).strip()
	return text or None


def default_scope_title(scope_title, origin_port, destination_port, location_from, location_to, incoterm):
	"""Return the scope title to store.

	A title that already has text is kept. A blank title becomes
	``Origin → Destination (Incoterm)`` when both ends are known. Ports are
	used first. Location From and Location To are used when either port is
	blank. The stored value is left unchanged when neither pair is complete
	and no incoterm is set.
	"""
	if (scope_title or "").strip():
		return scope_title
	origin = _strip(origin_port)
	dest = _strip(destination_port)
	if not (origin and dest):
		origin = _strip(location_from)
		dest = _strip(location_to)
	parts = []
	if origin and dest:
		parts.append(f"{origin} → {dest}")
	inc = _strip(incoterm)
	if inc:
		parts.append(f"({inc})")
	if parts:
		return " ".join(parts)
	return scope_title
