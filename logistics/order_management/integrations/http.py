# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""HTTP entry point. Tests patch ``request``."""

from __future__ import annotations


def request(method, url, **kwargs):
	import requests

	kwargs.setdefault("timeout", 30)
	response = requests.request(method, url, **kwargs)
	response.raise_for_status()
	if not response.content:
		return {}
	return response.json()
