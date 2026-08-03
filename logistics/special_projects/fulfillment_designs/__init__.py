"""Special Project Fulfillment tab design variants.

Active design is selected by ``ACTIVE_FULFILLMENT_DESIGN``. Switch back to the
previous production UI by setting it to ``sp_fullfillment_design_1``.
"""

from __future__ import annotations

from typing import Any, Callable

# Named variants:
#   sp_fullfillment_design_1 — production UI before the ops-scan redesign
#   sp_fullfillment_design_2 — Alternative 1 ops-scan layout (lifecycle bar + KPIs + table)
ACTIVE_FULFILLMENT_DESIGN = "sp_fullfillment_design_2"

DESIGN_1 = "sp_fullfillment_design_1"
DESIGN_2 = "sp_fullfillment_design_2"


def render_fulfillment_tab(doc: Any, ctx: dict[str, Any] | None, *, design: str | None = None) -> str:
	"""Render the Fulfillment tab HTML for the selected design variant."""
	key = (design or ACTIVE_FULFILLMENT_DESIGN or DESIGN_2).strip()
	builder = _builders().get(key) or _builders()[DESIGN_2]
	return builder(doc, ctx)


def _builders() -> dict[str, Callable[[Any, dict[str, Any] | None], str]]:
	from logistics.special_projects.fulfillment_designs.sp_fullfillment_design_1 import (
		build_fulfillment_tab_html as build_design_1,
	)
	from logistics.special_projects.fulfillment_designs.sp_fullfillment_design_2 import (
		build_fulfillment_tab_html as build_design_2,
	)

	return {
		DESIGN_1: build_design_1,
		DESIGN_2: build_design_2,
	}
