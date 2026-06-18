"""Push latest House Bill of Lading HTML to both Sea Shipment print formats."""

from logistics.sea_freight.print_format.house_bill_of_lading.install_print_format import (
	install_house_bl_print_format,
)


def execute():
	install_house_bl_print_format()
