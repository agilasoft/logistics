"""
Recognition Engine for WIP and Accrual Recognition

This module provides the core functionality for:
- WIP (Work In Progress) recognition for estimated revenue
- Accrual recognition for estimated costs
- Adjustments when actual revenue/costs are recognized
- Job closure handling
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, flt, nowdate
from datetime import datetime


class RecognitionEngine:
    """Core engine for revenue and cost recognition."""
    
    def __init__(self, job):
        """
        Initialize the Recognition Engine with a job document.
        
        Args:
            job: The job document (Air Shipment, Sea Shipment, Transport Job, etc.)
        """
        self.job = job
        self.job_type = job.doctype
        self.company = job.company
        self.settings = None
    
    def get_settings(self):
        """Get recognition settings for this job."""
        if not self.settings:
            self.settings = get_recognition_settings(self.job)
        return self.settings
    
    # ==================== WIP Recognition ====================
    
    def recognize_wip(self, recognition_date=None):
        """
        Recognize WIP for the job.
        
        Args:
            recognition_date: Optional date for recognition. If not provided,
                             will be determined based on settings.
        
        Returns:
            str: Name of the created Journal Entry, or None if skipped
        """
        settings = self.get_settings()
        
        if not settings.get("enable_wip_recognition", False):
            return None
        
        # Check minimum amount
        minimum_wip = settings.get("minimum_wip_amount", 0)
        estimated_revenue = self.calculate_estimated_revenue()
        
        if minimum_wip > 0 and estimated_revenue < minimum_wip:
            frappe.msgprint(_("Estimated revenue {0} is below minimum WIP amount {1}").format(
                estimated_revenue, minimum_wip
            ))
            return None
        
        if not recognition_date:
            recognition_date = self.get_wip_recognition_date()
        
        if not recognition_date:
            frappe.throw(_("Recognition date could not be determined"))
        
        if estimated_revenue <= 0:
            frappe.throw(_("Estimated revenue must be greater than zero"))
        
        # Check if already recognized
        if self.job.get("wip_journal_entry"):
            frappe.throw(_("WIP has already been recognized. Use adjust_wip() to make adjustments."))
        
        # Create Journal Entry
        je_name = self.create_wip_recognition_je(recognition_date, estimated_revenue)
        
        # Update job
        self.job.wip_amount = estimated_revenue
        self.job.wip_journal_entry = je_name
        self.job.save()
        
        return je_name
    
    def adjust_wip(self, adjustment_amount, adjustment_date=None):
        """
        Adjust WIP when actual revenue is recognized.
        
        Entry: Dr Revenue Liability, Cr WIP
        
        Args:
            adjustment_amount: The amount to adjust (close out)
            adjustment_date: Date for the adjustment (defaults to today)
        
        Returns:
            str: Name of the created Journal Entry
        """
        if not adjustment_date:
            adjustment_date = nowdate()
        
        if adjustment_amount <= 0:
            frappe.throw(_("Adjustment amount must be greater than zero"))
        
        current_wip = flt(self.job.get("wip_amount", 0))
        if adjustment_amount > current_wip:
            frappe.throw(_("Adjustment amount {0} exceeds current WIP balance {1}").format(
                adjustment_amount, current_wip
            ))
        
        je_name = self.create_wip_adjustment_je(adjustment_amount, adjustment_date)
        
        # Update job
        self.job.wip_amount = current_wip - adjustment_amount
        self.job.recognized_revenue = flt(self.job.get("recognized_revenue", 0)) + adjustment_amount
        self.job.wip_adjustment_journal_entry = je_name
        self.job.save()
        
        return je_name
    
    def close_wip(self, closure_date=None):
        """
        Close out all remaining WIP when job is closed.
        
        Args:
            closure_date: Date for the closure entry (defaults to today)
        
        Returns:
            str: Name of the created Journal Entry, or None if no WIP to close
        """
        if not closure_date:
            closure_date = nowdate()
        
        wip_amount = flt(self.job.get("wip_amount", 0))
        if wip_amount <= 0:
            return None
        
        je_name = self.create_wip_adjustment_je(wip_amount, closure_date, is_closure=True)
        
        # Update job
        self.job.wip_amount = 0
        self.job.recognized_revenue = flt(self.job.get("recognized_revenue", 0)) + wip_amount
        self.job.wip_closed = 1
        self.job.save()
        
        return je_name
    
    # ==================== Accrual Recognition ====================
    
    def recognize_accruals(self, recognition_date=None):
        """
        Recognize accruals for the job.
        
        Args:
            recognition_date: Optional date for recognition. If not provided,
                             will be determined based on settings.
        
        Returns:
            str: Name of the created Journal Entry, or None if skipped
        """
        settings = self.get_settings()
        
        if not settings.get("enable_accrual_recognition", False):
            return None
        
        # Check minimum amount
        minimum_accrual = settings.get("minimum_accrual_amount", 0)
        estimated_costs = self.calculate_estimated_costs()
        
        if minimum_accrual > 0 and estimated_costs < minimum_accrual:
            frappe.msgprint(_("Estimated costs {0} is below minimum accrual amount {1}").format(
                estimated_costs, minimum_accrual
            ))
            return None
        
        if not recognition_date:
            recognition_date = self.get_accrual_recognition_date()
        
        if not recognition_date:
            frappe.throw(_("Recognition date could not be determined"))
        
        if estimated_costs <= 0:
            frappe.throw(_("Estimated costs must be greater than zero"))
        
        # Check if already recognized
        if self.job.get("accrual_journal_entry"):
            frappe.throw(_("Accruals have already been recognized. Use adjust_accruals() to make adjustments."))
        
        # Create Journal Entry
        je_name = self.create_accrual_recognition_je(recognition_date, estimated_costs)
        
        # Update job
        self.job.accrual_amount = estimated_costs
        self.job.accrual_journal_entry = je_name
        self.job.save()
        
        return je_name
    
    def adjust_accruals(self, adjustment_amount, adjustment_date=None):
        """
        Adjust accruals when actual costs are recognized.
        
        Entry: Dr Accrued Cost Liability, Cr Cost Accrual
        
        Args:
            adjustment_amount: The amount to adjust (close out)
            adjustment_date: Date for the adjustment (defaults to today)
        
        Returns:
            str: Name of the created Journal Entry
        """
        if not adjustment_date:
            adjustment_date = nowdate()
        
        if adjustment_amount <= 0:
            frappe.throw(_("Adjustment amount must be greater than zero"))
        
        current_accrual = flt(self.job.get("accrual_amount", 0))
        if adjustment_amount > current_accrual:
            frappe.throw(_("Adjustment amount {0} exceeds current accrual balance {1}").format(
                adjustment_amount, current_accrual
            ))
        
        je_name = self.create_accrual_adjustment_je(adjustment_amount, adjustment_date)
        
        # Update job
        self.job.accrual_amount = current_accrual - adjustment_amount
        self.job.recognized_costs = flt(self.job.get("recognized_costs", 0)) + adjustment_amount
        self.job.accrual_adjustment_journal_entry = je_name
        self.job.save()
        
        return je_name
    
    def close_accruals(self, closure_date=None):
        """
        Close out all remaining accruals when job is closed.
        
        Args:
            closure_date: Date for the closure entry (defaults to today)
        
        Returns:
            str: Name of the created Journal Entry, or None if no accrual to close
        """
        if not closure_date:
            closure_date = nowdate()
        
        accrual_amount = flt(self.job.get("accrual_amount", 0))
        if accrual_amount <= 0:
            return None
        
        je_name = self.create_accrual_adjustment_je(accrual_amount, closure_date, is_closure=True)
        
        # Update job
        self.job.accrual_amount = 0
        self.job.recognized_costs = flt(self.job.get("recognized_costs", 0)) + accrual_amount
        self.job.accrual_closed = 1
        self.job.save()
        
        return je_name
    
    # ==================== Date Resolution ====================
    
    def get_wip_recognition_date(self):
        """Get the WIP recognition date based on settings."""
        settings = self.get_settings()
        basis = settings.get("wip_recognition_date_basis", "Job Booking Date")
        return self._resolve_date(basis)
    
    def get_accrual_recognition_date(self):
        """Get the accrual recognition date based on settings."""
        settings = self.get_settings()
        basis = settings.get("accrual_recognition_date_basis", "Job Booking Date")
        return self._resolve_date(basis)
    
    def _resolve_date(self, basis):
        """Resolve date based on the specified basis."""
        if basis == "ATA":
            return get_ata_date(self.job)
        elif basis == "ATD":
            return get_atd_date(self.job)
        elif basis == "Job Booking Date":
            return get_booking_date(self.job)
        elif basis == "Job Creation":
            return getdate(self.job.creation)
        elif basis == "User Specified":
            return self.job.get("recognition_date")
        return None
    
    # ==================== Calculations ====================
    
    def calculate_estimated_revenue(self):
        """
        Calculate estimated revenue from charges table.
        
        Returns:
            float: Total estimated revenue
        """
        total = 0
        charges_table = self._get_charges_table_name()
        
        if charges_table and hasattr(self.job, charges_table):
            for charge in self.job.get(charges_table, []):
                if hasattr(charge, 'estimated_revenue') and charge.estimated_revenue:
                    total += flt(charge.estimated_revenue)
                elif hasattr(charge, 'amount') and charge.amount:
                    # Fallback to amount if estimated_revenue not set
                    total += flt(charge.amount)
        
        # Also check job-level estimated_revenue field
        if not total and hasattr(self.job, 'estimated_revenue'):
            total = flt(self.job.estimated_revenue)
        
        return total
    
    def calculate_estimated_costs(self):
        """
        Calculate estimated costs from charges table.
        
        Returns:
            float: Total estimated costs
        """
        total = 0
        charges_table = self._get_charges_table_name()
        
        if charges_table and hasattr(self.job, charges_table):
            for charge in self.job.get(charges_table, []):
                if hasattr(charge, 'estimated_cost') and charge.estimated_cost:
                    total += flt(charge.estimated_cost)
                elif hasattr(charge, 'cost') and charge.cost:
                    # Fallback to cost if estimated_cost not set
                    total += flt(charge.cost)
        
        # Also check job-level estimated_costs field
        if not total and hasattr(self.job, 'estimated_costs'):
            total = flt(self.job.estimated_costs)
        
        return total
    
    def _get_charges_table_name(self):
        """Get the name of the charges child table for this job type."""
        charges_tables = {
            "Air Shipment": "charges",
            "Sea Shipment": "charges",
            "Transport Job": "charges",
            "Warehouse Job": "charges",
            "Customs Declaration": "charges",
            "General Job": "charges"
        }
        return charges_tables.get(self.job_type)
    
    # ==================== Journal Entry Creation ====================
    
    def create_wip_recognition_je(self, recognition_date, amount):
        """
        Create WIP recognition Journal Entry.
        
        Dr. WIP Account (Asset)
        Cr. Revenue Liability Account (Liability)
        """
        settings = self.get_settings()
        
        je = frappe.new_doc("Journal Entry")
        je.posting_date = recognition_date
        je.company = self.company
        je.voucher_type = "Journal Entry"
        je.user_remark = f"WIP Recognition for {self.job_type} {self.job.name}"
        
        # Debit: WIP Account
        je.append("accounts", {
            "account": settings.get("wip_account"),
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        # Credit: Revenue Liability Account
        je.append("accounts", {
            "account": settings.get("revenue_liability_account"),
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        je.insert()
        je.submit()
        
        return je.name
    
    def create_wip_adjustment_je(self, amount, adjustment_date, is_closure=False):
        """
        Create WIP adjustment Journal Entry.
        
        Dr. Revenue Liability Account (close out)
        Cr. WIP Account (close out)
        """
        settings = self.get_settings()
        remark_type = "Closure" if is_closure else "Adjustment"
        
        je = frappe.new_doc("Journal Entry")
        je.posting_date = adjustment_date
        je.company = self.company
        je.voucher_type = "Journal Entry"
        je.user_remark = f"WIP {remark_type} for {self.job_type} {self.job.name}"
        
        # Debit: Revenue Liability Account
        je.append("accounts", {
            "account": settings.get("revenue_liability_account"),
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        # Credit: WIP Account
        je.append("accounts", {
            "account": settings.get("wip_account"),
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        je.insert()
        je.submit()
        
        return je.name
    
    def create_accrual_recognition_je(self, recognition_date, amount):
        """
        Create Accrual recognition Journal Entry.
        
        Dr. Cost Accrual Account (Expense)
        Cr. Accrued Cost Liability Account (Liability)
        """
        settings = self.get_settings()
        
        je = frappe.new_doc("Journal Entry")
        je.posting_date = recognition_date
        je.company = self.company
        je.voucher_type = "Journal Entry"
        je.user_remark = f"Accrual Recognition for {self.job_type} {self.job.name}"
        
        # Debit: Cost Accrual Account
        je.append("accounts", {
            "account": settings.get("cost_accrual_account"),
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        # Credit: Accrued Cost Liability Account
        je.append("accounts", {
            "account": settings.get("accrued_cost_liability_account"),
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        je.insert()
        je.submit()
        
        return je.name
    
    def create_accrual_adjustment_je(self, amount, adjustment_date, is_closure=False):
        """
        Create Accrual adjustment Journal Entry.
        
        Dr. Accrued Cost Liability Account (close out)
        Cr. Cost Accrual Account (close out)
        """
        settings = self.get_settings()
        remark_type = "Closure" if is_closure else "Adjustment"
        
        je = frappe.new_doc("Journal Entry")
        je.posting_date = adjustment_date
        je.company = self.company
        je.voucher_type = "Journal Entry"
        je.user_remark = f"Accrual {remark_type} for {self.job_type} {self.job.name}"
        
        # Debit: Accrued Cost Liability Account
        je.append("accounts", {
            "account": settings.get("accrued_cost_liability_account"),
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        # Credit: Cost Accrual Account
        je.append("accounts", {
            "account": settings.get("cost_accrual_account"),
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            "reference_type": self.job_type,
            "reference_name": self.job.name
        })
        
        je.insert()
        je.submit()
        
        return je.name


# ==================== Settings Resolution ====================

def get_recognition_settings(job):
    """
    Get recognition settings for a job, applying hierarchy.
    
    Hierarchy (highest to lowest priority):
    1. Job-level overrides
    2. Recognition Policy Settings matched by Cost Center + Profit Center + Branch
    3. Company default (Recognition Policy Settings with blank Cost Center/Profit Center/Branch)
    
    Args:
        job: The job document
    
    Returns:
        dict: Settings with all applicable overrides applied
    """
    company = job.company
    
    # Initialize result with empty defaults
    result = {
        "enable_wip_recognition": False,
        "enable_accrual_recognition": False,
        "wip_recognition_date_basis": "Job Booking Date",
        "accrual_recognition_date_basis": "Job Booking Date",
        "wip_account": None,
        "revenue_liability_account": None,
        "cost_accrual_account": None,
        "accrued_cost_liability_account": None,
        "minimum_wip_amount": 0,
        "minimum_accrual_amount": 0
    }
    
    # Get settings via Job Costing Number (matched by Cost Center + Profit Center + Branch)
    policy = None
    if job.get("job_costing_number"):
        policy = get_recognition_policy_for_job(job.job_costing_number)
    
    if not policy:
        # Fallback: Try to match by job's own cost_center, profit_center, branch
        policy = get_recognition_policy_by_dimensions(
            company,
            job.get("cost_center"),
            job.get("profit_center"),
            job.get("branch")
        )
    
    if not policy:
        # Fallback: Get company default (settings with blank Cost Center/Profit Center/Branch)
        default_policies = frappe.get_all("Recognition Policy Settings", 
            filters={
                "company": company, 
                "enabled": 1,
                "cost_center": ["is", "not set"],
                "profit_center": ["is", "not set"],
                "branch": ["is", "not set"]
            },
            limit=1
        )
        if default_policies:
            policy = frappe.get_doc("Recognition Policy Settings", default_policies[0].name)
    
    if policy:
        result = {
            "enable_wip_recognition": policy.enable_wip_recognition,
            "enable_accrual_recognition": policy.enable_accrual_recognition,
            "wip_recognition_date_basis": policy.wip_recognition_date_basis,
            "accrual_recognition_date_basis": policy.accrual_recognition_date_basis,
            "wip_account": policy.wip_account,
            "revenue_liability_account": policy.revenue_liability_account,
            "cost_accrual_account": policy.cost_accrual_account,
            "accrued_cost_liability_account": policy.accrued_cost_liability_account,
            "minimum_wip_amount": policy.minimum_wip_amount or 0,
            "minimum_accrual_amount": policy.minimum_accrual_amount or 0
        }
    
    # Apply job-level overrides (highest priority)
    if hasattr(job, 'wip_recognition_enabled') and job.wip_recognition_enabled is not None:
        result["enable_wip_recognition"] = job.wip_recognition_enabled
    if hasattr(job, 'accrual_recognition_enabled') and job.accrual_recognition_enabled is not None:
        result["enable_accrual_recognition"] = job.accrual_recognition_enabled
    if hasattr(job, 'wip_recognition_date_basis') and job.wip_recognition_date_basis:
        result["wip_recognition_date_basis"] = job.wip_recognition_date_basis
    if hasattr(job, 'accrual_recognition_date_basis') and job.accrual_recognition_date_basis:
        result["accrual_recognition_date_basis"] = job.accrual_recognition_date_basis
    
    return result


def get_recognition_policy_for_job(job_costing_number):
    """
    Get the best matching Recognition Policy Settings for a Job Costing Number.
    Matches by combination of Cost Center, Profit Center, and Branch.
    
    Args:
        job_costing_number: Name of the Job Costing Number document
    
    Returns:
        Document or dict: The matching Recognition Policy Settings, or None
    """
    jcn = frappe.get_doc("Job Costing Number", job_costing_number)
    
    return get_recognition_policy_by_dimensions(
        jcn.company,
        jcn.get("cost_center"),
        jcn.get("profit_center"),
        jcn.get("branch")
    )


def get_recognition_policy_by_dimensions(company, cost_center=None, profit_center=None, branch=None):
    """
    Get the best matching Recognition Policy Settings by dimensions.
    
    Args:
        company: Company name
        cost_center: Cost Center name (optional)
        profit_center: Profit Center name (optional)
        branch: Branch name (optional)
    
    Returns:
        Document: The matching Recognition Policy Settings, or None
    """
    # Get all potentially matching policies
    policies = frappe.get_all("Recognition Policy Settings",
        filters={"company": company, "enabled": 1},
        fields=["name", "cost_center", "profit_center", "branch", "priority"],
        order_by="priority desc"
    )
    
    best_match = None
    best_score = -1
    
    for policy in policies:
        score = 0
        matches = True
        
        # Check Cost Center match
        if policy.cost_center:
            if policy.cost_center == cost_center:
                score += 10
            else:
                matches = False
                continue
        
        # Check Profit Center match
        if policy.profit_center:
            if policy.profit_center == profit_center:
                score += 10
            else:
                matches = False
                continue
        
        # Check Branch match
        if policy.branch:
            if policy.branch == branch:
                score += 10
            else:
                matches = False
                continue
        
        # Add priority to score
        score += (policy.priority or 0)
        
        if matches and score > best_score:
            best_score = score
            best_match = policy
    
    if best_match:
        return frappe.get_doc("Recognition Policy Settings", best_match.name)
    
    return None


# ==================== Date Resolution Helpers ====================

def get_ata_date(job):
    """Get Actual Time of Arrival date from job."""
    # Priority: ata > actual_arrival > arrival_date
    for field in ['ata', 'actual_arrival', 'arrival_date', 'actual_arrival_date']:
        if job.get(field):
            return getdate(job.get(field))
    return None


def get_atd_date(job):
    """Get Actual Time of Departure date from job."""
    # Priority: atd > actual_departure > departure_date
    for field in ['atd', 'actual_departure', 'departure_date', 'actual_departure_date']:
        if job.get(field):
            return getdate(job.get(field))
    return None


def get_booking_date(job):
    """Get booking date from job."""
    # Priority: booking_date > job_booking_date > job_open_date > creation
    for field in ['booking_date', 'job_booking_date', 'job_open_date']:
        if job.get(field):
            return getdate(job.get(field))
    return getdate(job.creation)


# ==================== API Functions ====================

@frappe.whitelist()
def recognize_wip(doctype, docname, recognition_date=None):
    """
    API to recognize WIP for a job.
    
    Args:
        doctype: The job document type
        docname: The job document name
        recognition_date: Optional recognition date
    
    Returns:
        str: Name of the created Journal Entry
    """
    job = frappe.get_doc(doctype, docname)
    engine = RecognitionEngine(job)
    return engine.recognize_wip(recognition_date)


@frappe.whitelist()
def recognize_accruals(doctype, docname, recognition_date=None):
    """
    API to recognize accruals for a job.
    
    Args:
        doctype: The job document type
        docname: The job document name
        recognition_date: Optional recognition date
    
    Returns:
        str: Name of the created Journal Entry
    """
    job = frappe.get_doc(doctype, docname)
    engine = RecognitionEngine(job)
    return engine.recognize_accruals(recognition_date)


@frappe.whitelist()
def adjust_wip(doctype, docname, adjustment_amount, adjustment_date=None):
    """
    API to adjust WIP for a job.
    
    Args:
        doctype: The job document type
        docname: The job document name
        adjustment_amount: Amount to adjust
        adjustment_date: Optional adjustment date
    
    Returns:
        str: Name of the created Journal Entry
    """
    job = frappe.get_doc(doctype, docname)
    engine = RecognitionEngine(job)
    return engine.adjust_wip(flt(adjustment_amount), adjustment_date)


@frappe.whitelist()
def adjust_accruals(doctype, docname, adjustment_amount, adjustment_date=None):
    """
    API to adjust accruals for a job.
    
    Args:
        doctype: The job document type
        docname: The job document name
        adjustment_amount: Amount to adjust
        adjustment_date: Optional adjustment date
    
    Returns:
        str: Name of the created Journal Entry
    """
    job = frappe.get_doc(doctype, docname)
    engine = RecognitionEngine(job)
    return engine.adjust_accruals(flt(adjustment_amount), adjustment_date)


@frappe.whitelist()
def close_job_recognition(doctype, docname, closure_date=None):
    """
    API to close all WIP and accruals for a job.
    
    Args:
        doctype: The job document type
        docname: The job document name
        closure_date: Optional closure date
    
    Returns:
        dict: Names of the created Journal Entries
    """
    job = frappe.get_doc(doctype, docname)
    engine = RecognitionEngine(job)
    
    wip_je = engine.close_wip(closure_date)
    accrual_je = engine.close_accruals(closure_date)
    
    return {
        "wip_journal_entry": wip_je,
        "accrual_journal_entry": accrual_je
    }


@frappe.whitelist()
def process_period_closing_adjustments(company, period_end_date):
    """
    Process WIP and Accrual adjustments for period closing.
    
    Args:
        company: Company name
        period_end_date: End date of the period
    
    Returns:
        dict: Summary of adjustments made
    """
    period_end_date = getdate(period_end_date)
    
    job_types = [
        "Air Shipment", "Sea Shipment", "Transport Job",
        "Warehouse Job", "Customs Declaration", "General Job"
    ]
    
    results = {
        "wip_adjustments": [],
        "accrual_adjustments": [],
        "errors": []
    }
    
    for job_type in job_types:
        if not frappe.db.exists("DocType", job_type):
            continue
        
        # Get jobs with pending WIP or accruals
        jobs = frappe.get_all(job_type,
            filters={
                "company": company,
                "docstatus": 1
            },
            or_filters=[
                ["wip_amount", ">", 0],
                ["accrual_amount", ">", 0]
            ],
            pluck="name"
        )
        
        for job_name in jobs:
            try:
                job = frappe.get_doc(job_type, job_name)
                engine = RecognitionEngine(job)
                
                # Calculate actual revenue/costs as of period end
                actual_revenue = calculate_actual_revenue_as_of(job, period_end_date)
                actual_costs = calculate_actual_costs_as_of(job, period_end_date)
                
                # Adjust WIP if there are actuals
                if actual_revenue > 0 and job.get("wip_amount", 0) > 0:
                    adjustment = min(actual_revenue, job.wip_amount)
                    je = engine.adjust_wip(adjustment, period_end_date)
                    results["wip_adjustments"].append({
                        "job": job_name,
                        "journal_entry": je,
                        "amount": adjustment
                    })
                
                # Adjust accruals if there are actuals
                if actual_costs > 0 and job.get("accrual_amount", 0) > 0:
                    adjustment = min(actual_costs, job.accrual_amount)
                    je = engine.adjust_accruals(adjustment, period_end_date)
                    results["accrual_adjustments"].append({
                        "job": job_name,
                        "journal_entry": je,
                        "amount": adjustment
                    })
                    
            except Exception as e:
                results["errors"].append({
                    "job": job_name,
                    "error": str(e)
                })
    
    return results


def calculate_actual_revenue_as_of(job, as_of_date):
    """Calculate actual revenue posted for a job as of a specific date."""
    total = 0
    
    # Get from Sales Invoices linked to this job
    invoices = frappe.get_all("Sales Invoice Item",
        filters={
            "reference_doctype": job.doctype,
            "reference_name": job.name,
            "docstatus": 1
        },
        fields=["parent"]
    )
    
    for inv in invoices:
        posting_date = frappe.db.get_value("Sales Invoice", inv.parent, "posting_date")
        if getdate(posting_date) <= getdate(as_of_date):
            amount = frappe.db.get_value("Sales Invoice", inv.parent, "grand_total")
            total += flt(amount)
    
    return total


def calculate_actual_costs_as_of(job, as_of_date):
    """Calculate actual costs posted for a job as of a specific date."""
    total = 0
    
    # Get from Purchase Invoices linked to this job
    invoices = frappe.get_all("Purchase Invoice Item",
        filters={
            "reference_doctype": job.doctype,
            "reference_name": job.name,
            "docstatus": 1
        },
        fields=["parent"]
    )
    
    for inv in invoices:
        posting_date = frappe.db.get_value("Purchase Invoice", inv.parent, "posting_date")
        if getdate(posting_date) <= getdate(as_of_date):
            amount = frappe.db.get_value("Purchase Invoice", inv.parent, "grand_total")
            total += flt(amount)
    
    return total
