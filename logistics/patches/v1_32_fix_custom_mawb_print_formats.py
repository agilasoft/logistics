"""Fix site-specific Master Air Waybill print formats (e.g. MAWB HTML on cloud)."""

from logistics.air_freight.print_format.mawb.install_print_format import install_mawb_print_formats


def execute():
	install_mawb_print_formats()
