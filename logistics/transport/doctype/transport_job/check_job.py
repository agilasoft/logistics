#!/usr/bin/env python3
"""
Check Transport Job field values
Run with: bench --site [site] execute logistics.transport.doctype.transport_job.check_job.check_job --kwargs '{"job_name": "TR000000069"}'
"""

import frappe

def check_job(job_name="TR000000069"):
    """Check a Transport Job's field values"""
    try:
        job = frappe.get_doc("Transport Job", job_name)
        
        print(f"\n=== Transport Job {job_name} ===")
        print(f"transport_job_type: {repr(job.get('transport_job_type'))}")
        print(f"container_type: {repr(job.get('container_type'))}")
        print(f"container_no: {repr(job.get('container_no'))}")
        print(f"\nTypes:")
        print(f"transport_job_type type: {type(job.get('transport_job_type'))}")
        print(f"container_type type: {type(job.get('container_type'))}")
        print(f"container_no type: {type(job.get('container_no'))}")
        
        # Check if values are "truthy"
        def has_value(val):
            if val is None:
                return False
            if isinstance(val, str):
                return bool(val.strip())
            return bool(val)
        
        print(f"\nHas values:")
        print(f"has transport_job_type: {has_value(job.get('transport_job_type'))}")
        print(f"has container_type: {has_value(job.get('container_type'))}")
        print(f"has container_no: {has_value(job.get('container_no'))}")
        
        return {
            "transport_job_type": job.get('transport_job_type'),
            "container_type": job.get('container_type'),
            "container_no": job.get('container_no'),
        }
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

