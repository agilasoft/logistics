# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Sales Quote multimodal routing must name a Main Job."""

from __future__ import annotations


def multimodal_main_job_missing(is_main_job_flags):
	"""Return True when routing legs exist and none is the Main Job.

	An empty leg list is not multimodal, so it is not missing a Main Job.
	"""
	flags = list(is_main_job_flags or [])
	if not flags:
		return False
	return not any(flags)
