"""Test volume calculation on Air Booking ABK-000000186.
Run: bench --site logistics.agilasoft.com execute logistics.utils.test_abk_volume.run
"""
from __future__ import print_function

import frappe


def run():
    name = "ABK-000000186"
    if not frappe.db.exists("Air Booking", name):
        print("Air Booking %s does not exist." % name)
        return
    doc = frappe.get_doc("Air Booking", name)
    packages = doc.get("packages") or []
    print("Air Booking %s has %s package(s)." % (name, len(packages)))
    for i, p in enumerate(packages[:5]):
        length = getattr(p, "length", None)
        width = getattr(p, "width", None)
        height = getattr(p, "height", None)
        volume_before = getattr(p, "volume", None)
        dim_uom = getattr(p, "dimension_uom", None)
        vol_uom = getattr(p, "volume_uom", None)
        print("  Row %s: L=%s, W=%s, H=%s (%s) -> volume=%s (%s)" % (i, length, width, height, dim_uom, volume_before, vol_uom))
    if not packages:
        print("  No packages to test.")
        return
    # Simulate user changing dims: set new dimensions and run calculate_volume
    p0 = packages[0]
    test_length, test_width, test_height = 100, 50, 30  # cm
    p0.length = test_length
    p0.width = test_width
    p0.height = test_height
    p0.calculate_volume()
    new_vol = p0.volume
    print("  After setting L=%s W=%s H=%s and calculate_volume(): volume=%s" % (test_length, test_width, test_height, new_vol))
    if new_vol is not None and float(new_vol) > 0:
        print("  PASS: Volume auto-calculated from dimensions.")
    else:
        print("  CHECK: Volume is 0 or None (might be UOM/defaults).")
