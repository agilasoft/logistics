# Copyright (c) 2025, Logistics and contributors
"""Add recognition_date_basis and copy from WIP/Accrual basis before old columns drop."""

import frappe


def execute():
	_child = "tabRecognition Policy Parameter"
	_parent = "tabRecognition Policy Settings"

	if frappe.db.table_exists(_child) and not frappe.db.has_column("Recognition Policy Parameter", "recognition_date_basis"):
		frappe.db.sql(
			"ALTER TABLE `tabRecognition Policy Parameter` ADD COLUMN `recognition_date_basis` VARCHAR(140)"
		)
	if frappe.db.table_exists(_child) and frappe.db.has_column("Recognition Policy Parameter", "wip_recognition_date_basis"):
		frappe.db.sql(
			"""
			UPDATE `tabRecognition Policy Parameter`
			SET recognition_date_basis = COALESCE(
				NULLIF(TRIM(COALESCE(wip_recognition_date_basis, '')), ''),
				NULLIF(TRIM(COALESCE(accrual_recognition_date_basis, '')), ''),
				'Job Booking Date'
			)
			WHERE recognition_date_basis IS NULL OR TRIM(COALESCE(recognition_date_basis, '')) = ''
			"""
		)

	if frappe.db.table_exists(_parent) and not frappe.db.has_column("Recognition Policy Settings", "recognition_date_basis"):
		frappe.db.sql(
			"ALTER TABLE `tabRecognition Policy Settings` ADD COLUMN `recognition_date_basis` VARCHAR(140)"
		)
	if frappe.db.table_exists(_parent) and frappe.db.has_column("Recognition Policy Settings", "wip_recognition_date_basis"):
		frappe.db.sql(
			"""
			UPDATE `tabRecognition Policy Settings`
			SET recognition_date_basis = COALESCE(
				NULLIF(TRIM(COALESCE(wip_recognition_date_basis, '')), ''),
				NULLIF(TRIM(COALESCE(accrual_recognition_date_basis, '')), ''),
				'Job Booking Date'
			)
			WHERE recognition_date_basis IS NULL OR TRIM(COALESCE(recognition_date_basis, '')) = ''
			"""
		)

	frappe.db.commit()
