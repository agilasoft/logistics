# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Server-rendered HTML shell for charge weight break editors (no DocType JSON options)."""

import frappe
from frappe.utils import cint


@frappe.whitelist()
def get_weight_break_editor_shell_html(include_save_button=None):
	"""
	Return the static table shell for selling/cost weight break UIs and the Manage dialog.

	Args:
		include_save_button: 1 to include inline Save (grid form); 0 for dialog (primary Save only).

	Returns:
		dict: { "html": str }
	"""
	include_save = cint(include_save_button)
	html = frappe.render_template(
		"templates/includes/weight_break_editor_shell.html",
		{"include_save_button": bool(include_save)},
	)
	return {"html": html}
