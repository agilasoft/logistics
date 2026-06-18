"""DEPRECATED: this package has moved to ``goconnect.flight``.

Provider integration, the schedule aggregator and the scheduled tasks now
live in the GoConnect app. The modules here remain as thin shims that
re-export from ``goconnect.flight.*`` so that existing call sites inside
``logistics`` (Air Shipment / Master AWB / dashboards) keep working.

Removal of these shims is tracked separately; do not add new code here.
"""

from __future__ import unicode_literals
