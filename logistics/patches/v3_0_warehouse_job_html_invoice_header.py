"""Warehouse Job HTML: match Sales Invoice header layout."""

from logistics.warehousing.print_format.warehouse_job.install_print_format import (
	install_warehouse_job_print_formats,
)


def execute():
	install_warehouse_job_print_formats()
