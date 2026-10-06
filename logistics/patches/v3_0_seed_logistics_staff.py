# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Logistics Staff from Employee role flags and existing document links.

Link values stay as the Employee name because Logistics Staff is named from that
Employee. Documents then resolve without rewriting sales_rep and related columns.
"""

from logistics.logistics.doctype.logistics_staff.logistics_staff import (
	seed_logistics_staff_from_employees_and_links,
)


def execute():
	seed_logistics_staff_from_employees_and_links()
