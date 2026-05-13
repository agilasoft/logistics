# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shim: DB may still reference Special Project Task Type until logistics rename patch runs."""

from logistics.special_projects.doctype.project_task_type.project_task_type import ProjectTaskType


class SpecialProjectTaskType(ProjectTaskType):
	pass
