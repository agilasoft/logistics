# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shim: DB may still reference Special Project Order until logistics rename patch runs."""

from logistics.special_projects.doctype.project_task_order.project_task_order import ProjectTaskOrder


class SpecialProjectOrder(ProjectTaskOrder):
	pass
