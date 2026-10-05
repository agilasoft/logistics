# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

REGISTRY = {}


def register(cls):
	REGISTRY[cls.platform] = cls
	return cls


def get_adapter(platform, credentials):
	# Importing providers fills the registry.
	from logistics.order_management.integrations import providers  # noqa: F401

	cls = REGISTRY.get(platform)
	if cls is None:
		raise KeyError(f"No adapter for platform {platform}")
	return cls(credentials or {})
