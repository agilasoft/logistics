# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class ContainerMovement(Document):
	def on_update(self):
		try:
			from logistics.container_management.api import sync_container_from_movement

			sync_container_from_movement(self)
		except Exception as e:
			frappe.log_error(
				title="Container Movement sync",
				message="Container Movement {0}: {1}".format(self.name or "", str(e)),
			)
