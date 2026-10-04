# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Quote critical deadline when the quote is time sensitive."""

from __future__ import annotations


def critical_deadline_missing(is_time_sensitive, critical_deadline):
	"""Return True when Time Sensitive is on and Critical Deadline is empty."""
	if not is_time_sensitive:
		return False
	return not critical_deadline
