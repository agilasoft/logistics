# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Permission Group stores the users and permitted values synchronized to User Permission."""

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.permissions.studio_logic import (
	abbreviation,
	clean,
	config_hash,
	desired_permissions,
	duplicate_names,
	duplicate_values,
	palette_color,
	stored_status,
	value_key,
)


class PermissionGroup(Document):
	def validate(self):
		self.group_name = clean(self.group_name)
		self.description = clean(self.description)
		self.category = clean(self.category)
		self.abbreviation = abbreviation(self.group_name, self.abbreviation)
		if not clean(self.color):
			self.color = palette_color(self.group_name)
		self._validate_members()
		self._validate_values()
		members = [row.user for row in self.members if row.user]
		values = [_value_dict(row) for row in self.permitted_values]
		self.config_hash = config_hash(self.enabled, members, values)
		if self.is_new() and not self.synced_hash and not desired_permissions(self.enabled, members, values):
			self.synced_hash = self.config_hash
		if self.sync_status != "Syncing":
			self.sync_status = stored_status(
				self.sync_status, self.config_hash, self.synced_hash, self.last_sync_error
			)

	def on_trash(self):
		from logistics.permissions.studio_api import remove_managed_permissions

		remove_managed_permissions(self.name)

	def _validate_members(self):
		names = [row.user for row in self.members if row.user]
		duplicates = duplicate_names(names)
		if duplicates:
			frappe.throw(_("Duplicate members: {0}").format(", ".join(duplicates)))
		for row in list(self.members):
			if not row.user:
				self.remove(row)
				continue
			if not frappe.db.exists("User", row.user):
				frappe.throw(_("User {0} does not exist.").format(row.user))

	def _validate_values(self):
		duplicates = duplicate_values([_value_dict(row) for row in self.permitted_values])
		if duplicates:
			labels = [f"{item.get('allow')} / {item.get('for_value')}" for item in duplicates]
			frappe.throw(_("Duplicate permitted values: {0}").format(", ".join(labels)))
		seen = set()
		for row in list(self.permitted_values):
			if not row.allow or not row.for_value:
				self.remove(row)
				continue
			if not frappe.db.exists("DocType", row.allow):
				frappe.throw(_("Document type {0} does not exist.").format(row.allow))
			if not frappe.db.exists(row.allow, row.for_value):
				frappe.throw(_("{0} {1} does not exist.").format(row.allow, row.for_value))
			if row.applicable_for and not frappe.db.exists("DocType", row.applicable_for):
				frappe.throw(_("Applicable For {0} does not exist.").format(row.applicable_for))
			key = value_key(_value_dict(row))
			if key in seen:
				self.remove(row)
				continue
			seen.add(key)


def _value_dict(row):
	return {
		"allow": row.allow,
		"for_value": row.for_value,
		"applicable_for": row.applicable_for,
		"is_default": row.is_default,
		"hide_descendants": row.hide_descendants,
	}
