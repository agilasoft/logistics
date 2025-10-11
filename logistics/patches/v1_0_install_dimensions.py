# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from logistics.setup.install_dimensions import execute as install_dimensions


def execute():
    """Install dimensions for logistics GL Entry integration"""
    
    print("Installing logistics dimensions...")
    
    try:
        # Install dimensions
        result = install_dimensions()
        
        if result.get("success"):
            print(f"✅ {result.get('message')}")
            return True
        else:
            print(f"❌ Failed to install dimensions: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing dimensions: {e}")
        return False













