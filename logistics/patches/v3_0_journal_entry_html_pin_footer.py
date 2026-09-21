"""Reinstall Journal Entry HTML so the BIR footer pins to the bottom of page 1."""

from logistics.print_format.journal_entry.install_print_format import (
	install_journal_entry_print_format,
)


def execute():
	install_journal_entry_print_format()
