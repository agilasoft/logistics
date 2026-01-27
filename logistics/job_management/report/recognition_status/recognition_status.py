"""
Recognition Status Report

Shows WIP and Accrual recognition status for all jobs.
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "job_type",
            "label": _("Job Type"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "job_name",
            "label": _("Job"),
            "fieldtype": "Dynamic Link",
            "options": "job_type",
            "width": 150
        },
        {
            "fieldname": "company",
            "label": _("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 120
        },
        {
            "fieldname": "cost_center",
            "label": _("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 120
        },
        {
            "fieldname": "estimated_revenue",
            "label": _("Est. Revenue"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "wip_amount",
            "label": _("WIP Amount"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "recognized_revenue",
            "label": _("Recognized Revenue"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "wip_status",
            "label": _("WIP Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "estimated_costs",
            "label": _("Est. Costs"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "accrual_amount",
            "label": _("Accrual Amount"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "recognized_costs",
            "label": _("Recognized Costs"),
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "accrual_status",
            "label": _("Accrual Status"),
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    data = []
    
    job_types = [
        "Air Shipment", "Sea Shipment", "Transport Job",
        "Warehouse Job", "Customs Declaration", "General Job"
    ]
    
    for job_type in job_types:
        if not frappe.db.exists("DocType", job_type):
            continue
        
        # Check if the doctype has recognition fields
        meta = frappe.get_meta(job_type)
        if not meta.has_field("wip_amount"):
            continue
        
        # Build filters
        job_filters = {"docstatus": 1}
        if filters.get("company"):
            job_filters["company"] = filters.get("company")
        if filters.get("cost_center"):
            job_filters["cost_center"] = filters.get("cost_center")
        
        # Get jobs
        jobs = frappe.get_all(job_type,
            filters=job_filters,
            fields=[
                "name", "company", "cost_center",
                "estimated_revenue", "wip_amount", "recognized_revenue", "wip_closed",
                "estimated_costs", "accrual_amount", "recognized_costs", "accrual_closed"
            ]
        )
        
        for job in jobs:
            # Determine WIP status
            if job.wip_closed:
                wip_status = "Closed"
            elif flt(job.wip_amount) > 0:
                wip_status = "Open"
            elif flt(job.recognized_revenue) > 0:
                wip_status = "Recognized"
            else:
                wip_status = "Not Started"
            
            # Determine Accrual status
            if job.accrual_closed:
                accrual_status = "Closed"
            elif flt(job.accrual_amount) > 0:
                accrual_status = "Open"
            elif flt(job.recognized_costs) > 0:
                accrual_status = "Recognized"
            else:
                accrual_status = "Not Started"
            
            # Filter by status if specified
            if filters.get("wip_status") and wip_status != filters.get("wip_status"):
                continue
            if filters.get("accrual_status") and accrual_status != filters.get("accrual_status"):
                continue
            
            data.append({
                "job_type": job_type,
                "job_name": job.name,
                "company": job.company,
                "cost_center": job.cost_center,
                "estimated_revenue": job.estimated_revenue,
                "wip_amount": job.wip_amount,
                "recognized_revenue": job.recognized_revenue,
                "wip_status": wip_status,
                "estimated_costs": job.estimated_costs,
                "accrual_amount": job.accrual_amount,
                "recognized_costs": job.recognized_costs,
                "accrual_status": accrual_status
            })
    
    return data
