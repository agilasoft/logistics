# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CarbonEmissionFactor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		activity: DF.Data | None
		activity_type: DF.Link | None
		country: DF.Link | None
		emission_factor: DF.Float
		emission_factor_uom: DF.Link | None
		unit: DF.Data | None
	# end: auto-generated types

	pass
