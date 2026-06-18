"""Fix print formats and letter heads that call get_doc('Company', doc.company) without guards."""

from logistics.print_format.sync_company_safe_print_formats import sync_company_safe_print_formats
from logistics.transport.print_format.proof_of_delivery.install_print_format import (
	fix_cargonext_letter_head,
)


def execute():
	sync_company_safe_print_formats()
	fix_cargonext_letter_head()
