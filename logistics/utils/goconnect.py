"""Graceful-degradation helper for calls into the optional GoConnect app.

The `logistics` app (AGPL-3.0-or-later) MUST NOT import from `goconnect`
directly — doing so would create a Python-level coupling that pulls the
proprietary/commercial tracking app under our license terms. Instead, this
module looks up GoConnect endpoints at runtime via `frappe.get_attr` and
returns neutral values when the app is not installed.

Usage:

    from logistics.utils import goconnect as gc

    if gc.is_installed():
        result = gc.call("goconnect.api.sea.refresh_vessel_position",
                         sea_shipment=name)
    else:
        # tracking-disabled placeholder UI
        ...
"""

from __future__ import annotations

from typing import Any, Optional

import frappe


def is_installed() -> bool:
	"""True when the goconnect app is installed on this site."""
	try:
		return "goconnect" in frappe.get_installed_apps()
	except Exception:
		return False


def call(dotted_path: str, *args, **kwargs) -> Optional[Any]:
	"""Call a goconnect function by dotted path.

	Returns None silently when:
	  - goconnect is not installed
	  - the dotted path does not exist (e.g. older goconnect version)

	Raises any exception thrown by the underlying call (after logging) so the
	caller can decide whether to surface it.
	"""
	if not is_installed():
		return None
	if not dotted_path or not dotted_path.startswith("goconnect."):
		raise ValueError(
			f"Refusing to call non-goconnect path via this helper: {dotted_path!r}"
		)
	try:
		fn = frappe.get_attr(dotted_path)
	except (AttributeError, ImportError, frappe.DoesNotExistError):
		return None
	return fn(*args, **kwargs)


def safe_call(dotted_path: str, *args, default: Any = None, **kwargs) -> Any:
	"""Like `call` but never raises — logs and returns `default` instead."""
	try:
		result = call(dotted_path, *args, **kwargs)
		return default if result is None else result
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"logistics → goconnect call failed: {dotted_path}",
		)
		return default
