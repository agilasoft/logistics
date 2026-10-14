# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Decide which default Job Task Templates a site can seed.

``Applies to DocType`` is a Link to DocType. Inserting a template for a parent
that is not installed raises LinkValidationError and aborts the migrate, so
later parents in the same patch never get a checklist.
"""

from __future__ import annotations


def parents_to_seed(parents, default_tasks, installed_doctypes, existing_defaults, existing_names):
	"""Return ``(specs, skipped)`` for one default checklist per installed parent.

	``skipped`` is the parent DocTypes that are not installed. A parent that
	already has a default template, or whose template name is taken, is omitted
	from both lists.
	"""
	installed = set(installed_doctypes or ())
	defaults = set(existing_defaults or ())
	names = set(existing_names or ())
	specs = []
	skipped = []
	for doctype, (product_type, applies_to) in parents.items():
		if doctype not in installed:
			skipped.append(doctype)
			continue
		template_name = "{0} Tasks".format(doctype)
		if doctype in defaults or template_name in names:
			continue
		tasks = tuple(default_tasks.get(doctype) or ())
		if not tasks:
			continue
		specs.append(
			{
				"doctype": doctype,
				"product_type": product_type,
				"applies_to": applies_to,
				"template_name": template_name,
				"tasks": tasks,
			}
		)
	return specs, skipped
