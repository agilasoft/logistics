#!/usr/bin/env python3
"""
Manual script to run the fix_item_deletion_parent_columns patch
Usage: bench --site your-site-name execute logistics.run_patch_manually.run
"""

import frappe
from logistics.patches.fix_item_deletion_parent_columns import execute

def run():
	"""Run the patch manually"""
	frappe.init()
	frappe.connect()
	
	try:
		execute()
		print("\n✅ Patch execution completed!")
	except Exception as e:
		print(f"\n❌ Patch execution failed: {str(e)}")
		raise
	finally:
		frappe.destroy()

