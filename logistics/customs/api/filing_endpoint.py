# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Decide whether a Manifest Settings value is a live customs endpoint.

Hardcoded fallback URLs in the filing clients are placeholders. They are not
a configured endpoint, and a mock response must not change the filing document.
"""

from __future__ import unicode_literals

PLACEHOLDER_FILING_ENDPOINTS = frozenset(
	{
		"https://api.cbp.gov/ams/v1",
		"https://api.cbp.gov/isf/v1",
		"https://api.cbsa-asfc.gc.ca/emanifest/v1",
		"https://api.customs.go.jp/afr/v1",
	}
)


def normalize_filing_endpoint(value) -> str:
	return (value or "").strip().rstrip("/").lower()


def is_configured_filing_endpoint(value) -> bool:
	"""True when Manifest Settings holds a URL that is not a built-in placeholder."""
	endpoint = normalize_filing_endpoint(value)
	if not endpoint:
		return False
	placeholders = {normalize_filing_endpoint(item) for item in PLACEHOLDER_FILING_ENDPOINTS}
	return endpoint not in placeholders


def filing_block_reason(api_name: str, endpoint) -> str:
	"""Why submit, amend, cancel, or status must leave the filing document unchanged."""
	if is_configured_filing_endpoint(endpoint):
		return (
			"{0} is not sent to the customs authority from this app yet. "
			"The document was not changed."
		).format(api_name)
	return (
		"Set a live endpoint for {0} on Manifest Settings before filing. "
		"The document was left unchanged."
	).format(api_name)
