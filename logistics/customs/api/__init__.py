# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Customs filing clients.

Imports stay lazy so loading this package does not import Frappe until a
client class is requested.
"""

__all__ = [
	"BaseCustomsAPI",
	"USAMSAPI",
	"USISFAPI",
	"CAeManifestAPI",
	"JPAFRAPI",
]

_EXPORTS = {
	"BaseCustomsAPI": (".base_api", "BaseCustomsAPI"),
	"USAMSAPI": (".us_ams_api", "USAMSAPI"),
	"USISFAPI": (".us_isf_api", "USISFAPI"),
	"CAeManifestAPI": (".ca_emanifest_api", "CAeManifestAPI"),
	"JPAFRAPI": (".jp_afr_api", "JPAFRAPI"),
}


def __getattr__(name):
	if name not in _EXPORTS:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
	module_name, attr = _EXPORTS[name]
	from importlib import import_module

	module = import_module(module_name, __name__)
	value = getattr(module, attr)
	globals()[name] = value
	return value
