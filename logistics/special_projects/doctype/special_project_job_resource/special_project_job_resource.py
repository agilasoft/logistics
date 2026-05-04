# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shim: DB may still reference Special Project Job Resource until logistics rename patch runs."""

from logistics.special_projects.doctype.project_task_job_resource.project_task_job_resource import (
	ProjectTaskJobResource,
)


class SpecialProjectJobResource(ProjectTaskJobResource):
	pass
