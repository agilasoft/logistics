# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.permission_studio.flags import as_flag, clean_text
from logistics.permission_studio.logic import (
	BLOCKED_USERS,
	collect_grants,
	default_conflicts,
	validate_group_shape,
)
from logistics.permission_studio.sync import _group_dict, reconcile


class HeroPermissionGroup(Document):
	def validate(self):
		self._normalize()
		self._fill_members()
		errors = validate_group_shape(_group_dict(self) | {"group_name": self.group_name, "color": self.color})
		errors.extend(self._existence_errors())
		if errors:
			frappe.throw("<br>".join(errors), title=_("Check the permission group"))
		self._reject_cross_group_conflicts()
		self.member_count = len([row for row in self.members if row.user])
		self.rule_count = len([row for row in self.rules if row.reference_doctype and row.for_value])
		if self.is_new():
			self.sync_status = "Pending"
			self.sync_summary = None
			self.last_synced = None

	def on_update(self):
		reconcile()

	def after_rename(self, old, new, merge=False):
		# Link fields move with the document. Source group text is a plain
		# string, so rebuild managed User Permissions under the new name.
		reconcile()

	def on_trash(self):
		reconcile(exclude_groups={self.name})
		# Drop any link that would block deletion if a row was left pointing here.
		if frappe.get_meta("User Permission").has_field("hero_permission_group"):
			for name in frappe.get_all(
				"User Permission",
				filters={"hero_permission_group": self.name},
				pluck="name",
				ignore_permissions=True,
			):
				frappe.db.set_value("User Permission", name, "hero_permission_group", None, update_modified=False)

	def _normalize(self):
		self.group_name = clean_text(self.group_name)
		if not self.color:
			self.color = "#2490ef"
		for rule in self.rules:
			if as_flag(rule.apply_to_all_doctypes):
				rule.apply_to_all_doctypes = 1
				rule.applicable_for = None
			else:
				rule.apply_to_all_doctypes = 0

	def _fill_members(self):
		users = [row.user for row in self.members if row.user]
		if not users:
			return
		details = {
			row.name: row
			for row in frappe.get_all(
				"User",
				filters={"name": ["in", users]},
				fields=["name", "full_name", "user_type"],
				limit_page_length=0,
				ignore_permissions=True,
			)
		}
		for member in self.members:
			info = details.get(member.user)
			if not info:
				continue
			member.full_name = info.full_name
			member.user_type = info.user_type

	def _existence_errors(self) -> list[str]:
		errors = []
		for member in self.members:
			if member.user and member.user not in BLOCKED_USERS and not frappe.db.exists("User", member.user):
				errors.append(_("User {0} does not exist.").format(member.user))
		for rule in self.rules:
			if not rule.reference_doctype or not rule.for_value:
				continue
			if not frappe.db.exists("DocType", rule.reference_doctype):
				errors.append(_("DocType {0} does not exist.").format(rule.reference_doctype))
				continue
			meta = frappe.get_meta(rule.reference_doctype)
			if meta.istable or meta.issingle:
				errors.append(_("{0} cannot be used in a User Permission.").format(rule.reference_doctype))
				continue
			if not frappe.db.exists(rule.reference_doctype, rule.for_value):
				errors.append(
					_("{0} {1} does not exist.").format(rule.reference_doctype, rule.for_value)
				)
			if rule.applicable_for and not frappe.db.exists("DocType", rule.applicable_for):
				errors.append(_("Applicable For {0} does not exist.").format(rule.applicable_for))
		return errors

	def _reject_cross_group_conflicts(self):
		others = []
		for name in frappe.get_all("Hero Permission Group", pluck="name"):
			if name == self.name:
				continue
			others.append(_group_dict(frappe.get_doc("Hero Permission Group", name)))
		current = _group_dict(self)
		current["group_name"] = self.group_name
		if self.enabled:
			others.append(current)
		grants, hide_conflicts = collect_grants(others)
		messages = []
		for item in hide_conflicts:
			if self.name not in item["groups"] and self.group_name not in item["groups"]:
				continue
			messages.append(
				_("{0} has disagreeing Hide Descendants settings for {1} {2}.").format(
					item["user"], item["allow"], item["for_value"]
				)
			)
		for conflict in default_conflicts(grants):
			groups = {name for grant in conflict["grants"] for name in grant["groups"]}
			if self.name not in groups and self.group_name not in groups:
				continue
			values = ", ".join(grant["for_value"] for grant in conflict["grants"])
			messages.append(
				_("{0} would have more than one default for {1}: {2}.").format(
					conflict["user"], conflict["allow"], values
				)
			)
		if messages:
			frappe.throw("<br>".join(messages), title=_("Permission groups disagree"))
