# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_url


class CCSProvider(Document):
	def validate(self):
		if self.default_endpoint:
			validate_url(self.default_endpoint, throw=True, fieldname="default_endpoint")
		if self.test_endpoint:
			validate_url(self.test_endpoint, throw=True, fieldname="test_endpoint")
