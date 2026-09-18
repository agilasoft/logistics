"""Copy Job Number from original invoices onto credit/debit notes.

Accounting Dimension Job Number is no_copy, so ERPNext returns omit it.
Also reinstalls Sales Invoice HTML so print falls back to return_against.
"""

from logistics.invoice_integration.job_number_dimension_sync import (
	backfill_job_number_on_existing_return_invoices,
)
from logistics.print_format.sales_invoice.install_print_format import (
	install_sales_invoice_print_format,
)


def execute():
	backfill_job_number_on_existing_return_invoices()
	install_sales_invoice_print_format()
