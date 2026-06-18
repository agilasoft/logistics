"""Compat shim. See ``goconnect.land.resolve``.

Note: ``_provider_conf`` is an internal helper of the old module but is
explicitly imported by ``logistics.transport.doctype.transport_vehicle`` and
the telematics debug API. Re-export it explicitly so a star import is
unnecessary on the caller side.
"""

from goconnect.land.resolve import (  # noqa: F401
	_provider_conf,
	resolve_vehicle_provider,
)
