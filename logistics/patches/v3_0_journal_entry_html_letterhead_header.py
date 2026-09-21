"""Reinstall Journal Entry HTML print format with ATN-style letterhead header."""

from logistics.print_format.journal_entry.install_print_format import (
	install_journal_entry_print_format,
)


def execute():
	install_journal_entry_print_format()
