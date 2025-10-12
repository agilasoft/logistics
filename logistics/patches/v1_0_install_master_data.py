# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from logistics.setup.install_master_data import execute as install_master_data


def execute():
    """Install master data for logistics app"""
    
    print("Installing logistics master data...")
    
    try:
        # Install master data
        result = install_master_data()
        
        if result.get("success"):
            print(f"✅ {result.get('message')}")
            return True
        else:
            print(f"❌ Failed to install master data: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing master data: {e}")
        frappe.log_error(f"Master data installation error: {str(e)}")
        return False
