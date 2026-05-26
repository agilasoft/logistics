# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shim: DB may still reference Special Project Job until logistics rename patch runs."""

from logistics.special_projects.doctype.project_job.project_job import ProjectJob


class SpecialProjectJob(ProjectJob):
	pass
