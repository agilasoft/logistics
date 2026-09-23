# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict


def submit_cass_settlement(tx, settings) -> Dict[str, Any]:
	"""Legacy per-shipment POST is retired.

	CASSLink settlement is period-based: import a CASS File on a CASS Settlement Period.
	"""
	return {
		"success": False,
		"error": (
			"CASS settlement is not submitted per shipment. "
			"Import a CASSLink HOT/XLS/CSV file on a CASS Settlement Period "
			"(Air Freight → CASSLink)."
		),
	}
