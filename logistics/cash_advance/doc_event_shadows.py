# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

"""Clear desk payload keys that shadow Document controller methods."""

from __future__ import unicode_literals

# Frappe run_method() prefers instance __dict__ over controller methods. A null value here
# (e.g. from a stale desk payload) causes TypeError: 'NoneType' object is not callable on submit.
DOC_EVENT_METHOD_SHADOWS = frozenset(
	{
		"before_validate",
		"validate",
		"before_save",
		"after_save",
		"before_submit",
		"on_submit",
		"before_cancel",
		"on_cancel",
		"on_update",
		"on_update_after_submit",
		"before_insert",
		"after_insert",
		"on_change",
		"onload",
	}
)


def clear_doc_event_method_shadows(doc) -> None:
	for key in DOC_EVENT_METHOD_SHADOWS:
		if key in doc.__dict__ and not callable(doc.__dict__[key]):
			del doc.__dict__[key]
