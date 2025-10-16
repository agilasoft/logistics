#!/usr/bin/env python3
"""
Installation script for Logistics Accounting Dimensions.
Run this script from the bench directory: bench execute logistics.install_logistics_dimensions.install
"""

import frappe
from logistics.setup.install_dimensions import execute as install_dimensions


def install():
    """
    Install accounting dimensions for logistics integration.
    ERPNext will automatically handle field creation and population.
    """
    try:
        print("🚀 Installing Logistics Accounting Dimensions...")
        print("=" * 50)
        
        # Install dimensions
        print("📋 Installing accounting dimensions...")
        result = install_dimensions()
        
        if not result.get("success"):
            print(f"❌ Failed to install dimensions: {result.get('message')}")
            return False
        
        print(f"✅ {result.get('message')}")
        
        print("\\n🎉 Logistics Accounting Dimensions installed successfully!")
        print("\\nERPNext will automatically:")
        print("1. Add dimension fields to GL Entry and other relevant doctypes")
        print("2. Populate dimensions in GL entries when transactions are created")
        print("3. Enable dimension-wise reporting and analysis")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during installation: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    install()













