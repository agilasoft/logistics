# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from logistics.customs.child_row_virtual_mixin import PermitRequirementVirtualMixin


class DeclarationOrderPermitRequirement(Document, PermitRequirementVirtualMixin):
	pass
