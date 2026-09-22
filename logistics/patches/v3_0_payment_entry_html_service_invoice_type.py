"""Payment Entry HTML: show Service Invoice instead of Sales Invoice in TYPE."""

from logistics.print_format.payment_entry.install_payment_entry_print_format import (
	install_payment_entry_print_format,
)


def execute():
	install_payment_entry_print_format()
