"""
Air Freight Hooks
"""

from .patches.v1_0_3.update_location_structure import execute as populate_unlocode_on_install

# Installation hooks
after_install = "logistics.air_freight.hooks.populate_unlocode_on_install"

def populate_unlocode_on_install():
    """Populate UNLOCO database on installation"""
    try:
        print("🌍 Installing UNLOCO Location Database...")
        populate_unlocode_on_install()
        print("✅ UNLOCO Location Database installed successfully!")
    except Exception as e:
        print(f"❌ Error installing UNLOCO database: {str(e)}")
        frappe.log_error(f"UNLOCO installation error: {str(e)}")
