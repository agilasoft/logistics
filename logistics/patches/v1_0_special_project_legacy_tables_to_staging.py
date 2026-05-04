# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""Snapshot legacy Special Project child tables before schema sync drops/alters them."""

from __future__ import unicode_literals

import frappe

LEGACY_COPY = [
	("tabSpecial Project Job", "_sp_legacy_special_project_job"),
	("tabSpecial Project Resource", "_sp_legacy_special_project_resource"),
	("tabSpecial Project Product", "_sp_legacy_special_project_product"),
	("tabSpecial Project Equipment", "_sp_legacy_special_project_equipment"),
	("tabSpecial Project Activity", "_sp_legacy_special_project_activity"),
	("tabSpecial Project Resource Request", "_sp_legacy_special_project_resource_request"),
	("tabSpecial Project Product Request", "_sp_legacy_special_project_product_request"),
	("tabSpecial Project Equipment Request", "_sp_legacy_special_project_equipment_request"),
]


def execute():
	for src, dst in LEGACY_COPY:
		if not frappe.db.table_exists(src):
			continue
		frappe.db.sql_ddl("DROP TABLE IF EXISTS `{}`".format(dst))
		frappe.db.sql("CREATE TABLE `{}` LIKE `{}`".format(dst, src))
		frappe.db.sql("INSERT INTO `{}` SELECT * FROM `{}`".format(dst, src))
	frappe.db.commit()
