# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Special Project lifecycle validation."""

from __future__ import annotations

from logistics.utils.lifecycle_stage import FOR_SPECIAL_PROJECT, validate_lifecycle_stage_advance


def validate_special_project_lifecycle_stage_advance(doc):
	validate_lifecycle_stage_advance(
		doc,
		settings_doctype="Special Project Settings",
		module_filter=FOR_SPECIAL_PROJECT,
	)
