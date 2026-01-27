"""
Migration script for existing jobs

Phase 6: Migrate existing data
- Identify existing jobs that need recognition
- Calculate historical WIP and accruals
- Create migration entries if needed
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
from logistics.job_management.recognition_engine import RecognitionEngine, get_recognition_settings


def execute():
    """
    Migrate existing jobs to the new recognition system.
    
    This is a data migration script that should be run once after
    the recognition system is deployed.
    """
    job_types = [
        "Air Shipment", "Sea Shipment", "Transport Job",
        "Warehouse Job", "Customs Declaration", "General Job"
    ]
    
    migrated = 0
    skipped = 0
    errors = []
    
    for job_type in job_types:
        if not frappe.db.exists("DocType", job_type):
            continue
        
        # Check if doctype has recognition fields
        meta = frappe.get_meta(job_type)
        if not meta.has_field("wip_amount"):
            print(f"Skipping {job_type}: No recognition fields")
            continue
        
        # Get submitted jobs without recognition
        jobs = frappe.get_all(job_type,
            filters={
                "docstatus": 1,
                "wip_journal_entry": ["is", "not set"],
                "accrual_journal_entry": ["is", "not set"]
            },
            pluck="name"
        )
        
        print(f"Found {len(jobs)} {job_type} jobs to migrate")
        
        for job_name in jobs:
            try:
                job = frappe.get_doc(job_type, job_name)
                settings = get_recognition_settings(job)
                
                if not settings.get("enable_wip_recognition") and not settings.get("enable_accrual_recognition"):
                    skipped += 1
                    continue
                
                # Calculate estimated amounts
                engine = RecognitionEngine(job)
                estimated_revenue = engine.calculate_estimated_revenue()
                estimated_costs = engine.calculate_estimated_costs()
                
                # Update job with estimates (without creating JEs for historical data)
                if estimated_revenue > 0:
                    job.db_set("estimated_revenue", estimated_revenue, update_modified=False)
                
                if estimated_costs > 0:
                    job.db_set("estimated_costs", estimated_costs, update_modified=False)
                
                migrated += 1
                
                if migrated % 100 == 0:
                    frappe.db.commit()
                    print(f"Migrated {migrated} jobs...")
                    
            except Exception as e:
                errors.append({"job": job_name, "error": str(e)})
    
    frappe.db.commit()
    
    print(f"\n=== Migration Complete ===")
    print(f"Migrated: {migrated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for err in errors[:10]:  # Show first 10 errors
            print(f"  - {err['job']}: {err['error']}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    
    return {
        "migrated": migrated,
        "skipped": skipped,
        "errors": errors
    }


@frappe.whitelist()
def run_migration():
    """API endpoint to run migration."""
    frappe.only_for("System Manager")
    return execute()
