"""Fill Sea Manifest HTML with the Master Shipment Manifest fields."""

from logistics.sea_freight.print_format.sea_manifest_html.install_print_format import (
	install_sea_manifest_html_print_format,
)


def execute():
	install_sea_manifest_html_print_format()
