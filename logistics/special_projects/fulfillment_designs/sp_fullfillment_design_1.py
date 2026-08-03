"""sp_fullfillment_design_1 — previous Fulfillment tab UI (throughput + filters + table).

Preserved so we can fall back if the ops-scan redesign does not fit ops needs.
Activate via ``ACTIVE_FULFILLMENT_DESIGN = "sp_fullfillment_design_1"``.
"""

from __future__ import annotations

from typing import Any

from frappe import _
from frappe.utils import escape_html

from logistics.special_projects.doctype.special_project.special_project import (
	_packages_fulfillment_empty_inner_html,
	_packages_fulfillment_wrap_html,
	_packages_summary_current_stage_throughput_html,
	_packages_summary_filter_chips_html,
)


def build_fulfillment_tab_html(doc: Any, ctx: dict[str, Any] | None) -> str:
	"""Current-stage throughput, status filter chips, and package summary table."""
	if not ctx or ctx.get("empty"):
		empty_key = (ctx or {}).get("empty") or "no_packages"
		return _packages_fulfillment_wrap_html(
			_packages_fulfillment_empty_inner_html(empty_key),
			outer_class="sp-packages-summary sp-packages-summary--design-1",
		)

	current_tp_html = ""
	if ctx.get("current_stage"):
		current_tp_html = _packages_summary_current_stage_throughput_html(
			ctx["current_stage"],
			ctx["current_stage_qty"],
			ctx["total_required"],
		)

	summary_col_template = (
		"40px 28px minmax(140px, 1.5fr) 72px 72px 72px 64px minmax(100px, 1fr) 116px"
	)
	summary_header_html = (
		f'<div class="sp-pfn-header">'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-rowno">#</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-warn" aria-hidden="true"></span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-package">{escape_html(_("Package"))}</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-required">{escape_html(_("Required"))}</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-delivered">{escape_html(_("Delivered"))}</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-remaining">{escape_html(_("Remaining"))}</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-pct">{escape_html(_("%"))}</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-current-stage">{escape_html(_("Current Stage"))}</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-status">{escape_html(_("Status"))}</span>'
		f"</div>"
	)
	summary_table_html = (
		f'<div class="sp-pfn-summary-panel" style="--sp-pfn-cols: {summary_col_template}">'
		f'<div class="sp-pfn-table">{summary_header_html}{"".join(ctx.get("summary_rows_html") or [])}</div>'
		f"</div>"
	)
	inner = (
		f'<div class="sp-pfn-card" data-sp-fulfillment-panel="1" data-sp-fulfillment-design="sp_fullfillment_design_1">'
		f"{current_tp_html}"
		f"{_packages_summary_filter_chips_html()}"
		f"{summary_table_html}"
		f"</div>"
	)
	return _packages_fulfillment_wrap_html(
		inner,
		outer_class="sp-packages-summary sp-packages-summary--design-1",
	)
