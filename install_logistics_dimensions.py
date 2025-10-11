#!/usr/bin/env python3
"""
Installation script for Logistics GL Entry Dimensions.
Run this script from the bench directory: bench execute logistics.install_logistics_dimensions.install
"""

import frappe
from logistics.setup.install_dimensions import execute as install_dimensions
from logistics.setup.dimension_hooks import enhance_existing_gl_entries_with_dimensions


def install():
    """
    Install dimensions and enhance existing GL entries.
    """
    try:
        print("🚀 Installing Logistics GL Entry Dimensions...")
        print("=" * 50)
        
        # Step 1: Install dimensions
        print("📋 Step 1: Installing dimensions...")
        result = install_dimensions()
        
        if not result.get("success"):
            print(f"❌ Failed to install dimensions: {result.get('message')}")
            return False
        
        print(f"✅ {result.get('message')}")
        
        # Step 2: Enhance existing GL entries
        print("\\n📋 Step 2: Enhancing existing GL entries...")
        enhance_result = enhance_existing_gl_entries_with_dimensions()
        
        if enhance_result.get("error"):
            print(f"❌ Failed to enhance GL entries: {enhance_result.get('error')}")
            return False
        
        print(f"✅ {enhance_result.get('message')}")
        
        # Step 3: Verify installation
        print("\\n📋 Step 3: Verifying installation...")
        verify_result = verify_installation()
        
        if verify_result:
            print("✅ Installation verified successfully!")
        else:
            print("❌ Installation verification failed!")
            return False
        
        print("\\n🎉 Logistics GL Entry Dimensions installed successfully!")
        print("\\nNext steps:")
        print("1. Go to Accounting > Accounting Dimensions")
        print("2. Configure the dimensions as needed")
        print("3. New GL entries will automatically have dimensions populated")
        print("4. Use the dimension reports for analysis")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during installation: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_installation():
    """
    Verify that dimensions are properly installed and working.
    """
    try:
        # Check if dimensions exist
        dimensions = frappe.get_all("Accounting Dimension", 
            fields=["name", "document_type", "disabled"],
            filters={"name": ["in", ["Job Reference", "Item", "Profit Center"]]}
        )
        
        if len(dimensions) != 3:
            print(f"❌ Expected 3 dimensions, found {len(dimensions)}")
            return False
        
        print(f"✅ Found {len(dimensions)} dimensions:")
        for dim in dimensions:
            status = "Active" if not dim.disabled else "Disabled"
            print(f"  - {dim.name}: {dim.document_type} ({status})")
        
        # Check GL entries with dimensions
        gl_entries_with_dimensions = frappe.db.count("GL Entry", {
            "or": [
                ["job_reference", "is", "set"],
                ["item_code", "is", "set"],
                ["profit_center", "is", "set"]
            ]
        })
        
        total_gl_entries = frappe.db.count("GL Entry")
        coverage = (gl_entries_with_dimensions / total_gl_entries * 100) if total_gl_entries > 0 else 0
        
        print(f"✅ GL entries with dimensions: {gl_entries_with_dimensions}/{total_gl_entries} ({coverage:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying installation: {e}")
        return False


def test_dimension_hooks():
    """
    Test the dimension hooks to ensure they work correctly.
    """
    try:
        print("\\n🧪 Testing dimension hooks...")
        
        from logistics.setup.dimension_hooks import set_dimensions_in_gl_entry
        
        # Create a mock GL Entry
        class MockGLEntry:
            def __init__(self):
                self.voucher_type = 'Sales Invoice'
                self.voucher_no = 'TEST-SI-001'
                self.job_reference = None
                self.item_code = None
                self.profit_center = None
        
        # Test the hook
        gl_entry = MockGLEntry()
        set_dimensions_in_gl_entry(gl_entry, 'before_insert')
        
        print(f"✅ Hook test completed")
        print(f"  - Job Reference: {gl_entry.job_reference}")
        print(f"  - Item Code: {gl_entry.item_code}")
        print(f"  - Profit Center: {gl_entry.profit_center}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing hooks: {e}")
        return False


if __name__ == "__main__":
    install()













