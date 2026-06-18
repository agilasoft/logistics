# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Patch: register Sales Quote (One-off) as an Internal Job parent.

This is a structural / docfield migration patch. The schema sync that runs alongside the migrate
adds the new ``internal_job_details`` Table on ``Sales Quote`` and the ``charge_scope`` + 
``internal_job`` fields on ``Sales Quote Charge``. This patch normalises pre-existing data so the
new validation does not throw on previously saved quotes:

* Default ``charge_scope = "Main"`` for every existing ``Sales Quote Charge`` row that has no value
  (NULL/empty string), so the desk loads cleanly without showing the "Internal Job Required" error
  when a user re-saves an old quote.

Existing One-off quotes that were converted to bookings before this patch keep their bookings'
``internal_job_details`` (auto-derived via the regular sync path). No backfill of SQ-side IJs is
attempted; users can add Internal Jobs on the quote and re-tag charges going forward.
"""

import frappe


def execute() -> None:
	if not frappe.db.has_column("Sales Quote Charge", "charge_scope"):
		return

	# Default empty / NULL charge_scope to "Main" on every existing charge row.
	frappe.db.sql(
		"""
		UPDATE `tabSales Quote Charge`
		SET charge_scope = 'Main'
		WHERE charge_scope IS NULL OR charge_scope = ''
		"""
	)

	# Belt-and-braces: clear stray internal_job links on Main-scoped rows so the post-migration
	# desk view never shows a tagged IJ outside the Internal Job scope.
	frappe.db.sql(
		"""
		UPDATE `tabSales Quote Charge`
		SET internal_job = NULL
		WHERE (charge_scope IS NULL OR charge_scope = '' OR charge_scope = 'Main')
		  AND internal_job IS NOT NULL
		  AND internal_job <> ''
		"""
	)
	frappe.db.commit()
