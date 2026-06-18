"""Compat shim. See ``goconnect.land.providers.remora``.

Note: ``_get_field`` is explicitly imported by Transport Vehicle and the
debug API, so re-export it by name even though it starts with an
underscore (which ``import *`` would otherwise drop).
"""

from goconnect.land.providers.remora import *  # noqa: F401,F403
from goconnect.land.providers.remora import (  # noqa: F401
	RemoraProvider,
	_get_field,
)
