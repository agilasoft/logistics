"""Install Warehouse Job - Cross Dock print format (and refresh shared HTML)."""

from logistics.warehousing.print_format.warehouse_job.install_print_format import (
	install_warehouse_job_print_formats,
)


def execute():
	install_warehouse_job_print_formats()
