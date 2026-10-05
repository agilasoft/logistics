# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Choose which country filing a Global Manifest sends.

The choice uses the manifest country and the enable flags already stored on
that company's Manifest Settings. It does not pick a filing provider. Each
country section on Manifest Settings is the one account for that company.
"""

from __future__ import unicode_literals


def country_key(country_name, country_code):
	"""Return US, CA, JP, or an empty string."""
	name = (country_name or "").strip()
	code = (country_code or "").strip().upper()
	if name == "United States" or code == "US":
		return "US"
	if name == "Canada" or code == "CA":
		return "CA"
	if name == "Japan" or code == "JP":
		return "JP"
	return ""


def _enabled(settings, fieldname):
	if isinstance(settings, dict):
		return bool(settings.get(fieldname))
	return bool(getattr(settings, fieldname, 0))


def plan_filings(country_name, country_code, settings):
	"""Return the filing DocTypes to create and submit, or why filing stops.

	US ISF is included only when US AMS is enabled as well. ISF is filed from
	the AMS document, so it is never a filing on its own.
	"""
	key = country_key(country_name, country_code)
	if key == "US":
		if not _enabled(settings, "enable_us_ams"):
			return {"filings": [], "reason": "disabled", "country_key": key}
		filings = ["US AMS"]
		if _enabled(settings, "enable_us_isf"):
			filings.append("US ISF")
		return {"filings": filings, "reason": "", "country_key": key}
	if key == "CA":
		if not _enabled(settings, "enable_ca_emanifest"):
			return {"filings": [], "reason": "disabled", "country_key": key}
		return {"filings": ["CA eManifest Forwarder"], "reason": "", "country_key": key}
	if key == "JP":
		if not _enabled(settings, "enable_jp_afr"):
			return {"filings": [], "reason": "disabled", "country_key": key}
		return {"filings": ["JP AFR"], "reason": "", "country_key": key}
	return {"filings": [], "reason": "unsupported", "country_key": ""}
