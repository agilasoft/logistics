#!/usr/bin/env python3

import frappe
from frappe import _

def test_periodic_billing_get_charges():
    """Test the periodic billing get charges function"""
    try:
        # Test with a sample periodic billing
        result = frappe.call('logistics.warehousing.billing.periodic_billing_get_charges', 
                           periodic_billing='PB-00001', 
                           clear_existing=1)
        print("Result:", result)
        return result
    except Exception as e:
        print("Error:", str(e))
        return {"error": str(e)}

if __name__ == "__main__":
    frappe.init(site='localhost')
    frappe.connect()
    result = test_periodic_billing_get_charges()
    print("Final result:", result)
