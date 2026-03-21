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
from frappe.utils import getdate, today, flt, nowdate, cint
from datetime import datetime

from logistics.job_management.gl_item_dimension import item_row_dict


class RecognitionEngine:
    """Core engine for revenue and cost recognition."""

    # Journal Entry Account.reference_type only allows these ERPNext doctypes.
    # Logistics jobs (Sea Shipment, Air Shipment, etc.) are not valid — leave ref blank.
    _JE_ACCOUNT_REFERENCE_DOCTYPES = frozenset(
        (
            "Sales Invoice",
            "Purchase Invoice",
            "Journal Entry",
            "Sales Order",
            "Purchase Order",
            "Expense Claim",
            "Asset",
            "Loan",
            "Payroll Entry",
            "Employee Advance",
            "Exchange Rate Revaluation",
            "Invoice Discounting",
            "Fees",
            "Full and Final Statement",
            "Payment Entry",
        )
    )

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

    def _je_account_reference_fields(self):
        """reference_type on JE rows must be an ERPNext-allowed doctype or empty."""
        if self.job_type in self._JE_ACCOUNT_REFERENCE_DOCTYPES:
            return {"reference_type": self.job_type, "reference_name": self.job.name}
        return {"reference_type": "", "reference_name": ""}

    def _item_dimension_je_row(self, item_code):
        """Set the site Item accounting dimension on Journal Entry Account rows (if configured)."""
        return item_row_dict("Journal Entry Account", item_code)

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

        Entry: Dr WIP Account, Cr Revenue Liability (reverses initial WIP recognition)
        
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
        accrual_lines = self._get_accrual_lines_from_charges()
        estimated_costs = sum(flt(x.get("amount")) for x in accrual_lines)
        if not accrual_lines or estimated_costs <= 0:
            estimated_costs = self.calculate_estimated_costs()
            if estimated_costs > 0:
                accrual_lines = [{"amount": estimated_costs, "item_code": None}]
        
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
        
        # Create Journal Entry (one Dr/Cr pair per charge line when item/amounts are split)
        je_name = self.create_accrual_recognition_je(recognition_date, accrual_lines)
        
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
    
    def get_recognition_date(self):
        """Single posting date for WIP and accrual (same recognition date basis)."""
        settings = self.get_settings()
        basis = settings.get("recognition_date_basis") or "Job Booking Date"
        return self._resolve_date(basis)

    def get_wip_recognition_date(self):
        return self.get_recognition_date()

    def get_accrual_recognition_date(self):
        return self.get_recognition_date()
    
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
    
    def _charge_excluded_from_recognition(self, charge):
        """Disbursement charges are not included in WIP/accrual recognition."""
        ct = (getattr(charge, "charge_type", None) or "").strip().lower()
        return ct == "disbursement"

    def calculate_estimated_revenue(self):
        """
        Calculate estimated revenue from charges table.
        Excludes Disbursement charge lines.

        Returns:
            float: Total estimated revenue
        """
        total = 0
        charges_table = self._get_charges_table_name()

        if charges_table and hasattr(self.job, charges_table):
            for charge in self.job.get(charges_table, []):
                if self._charge_excluded_from_recognition(charge):
                    continue
                if hasattr(charge, "estimated_revenue") and charge.estimated_revenue:
                    total += flt(charge.estimated_revenue)
                elif hasattr(charge, "amount") and charge.amount:
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
                if self._charge_excluded_from_recognition(charge):
                    continue
                if hasattr(charge, "estimated_cost") and charge.estimated_cost:
                    total += flt(charge.estimated_cost)
                elif hasattr(charge, "cost") and charge.cost:
                    total += flt(charge.cost)
        
        # Also check job-level estimated_costs field
        if not total and hasattr(self.job, 'estimated_costs'):
            total = flt(self.job.estimated_costs)
        
        return total

    def _get_accrual_lines_from_charges(self):
        """
        Build accrual JE lines from charge rows (amount + item_code for Item dimension).
        Falls back to a single line from job-level estimated_costs when charge lines have no cost.
        """
        lines = []
        charges_table = self._get_charges_table_name()

        if charges_table and hasattr(self.job, charges_table):
            for charge in self.job.get(charges_table, []):
                if self._charge_excluded_from_recognition(charge):
                    continue
                amt = flt(getattr(charge, "estimated_cost", None) or getattr(charge, "cost", None) or 0)
                if amt <= 0:
                    continue
                item_code = (
                    getattr(charge, "item_code", None)
                    or getattr(charge, "charge_item", None)
                    or None
                )
                lines.append({"amount": amt, "item_code": item_code})

        if not lines and hasattr(self.job, "estimated_costs") and flt(self.job.estimated_costs) > 0:
            lines.append({"amount": flt(self.job.estimated_costs), "item_code": None})

        return lines
    
    def _get_charges_table_name(self):
        """Get the name of the charges child table for this job type."""
        charges_tables = {
            "Air Shipment": "charges",
            "Sea Shipment": "charges",
            "Transport Job": "charges",
            "Warehouse Job": "charges",
            "Declaration": "charges",
            "General Job": "charges"
        }
        return charges_tables.get(self.job_type)
    
    # ==================== Journal Entry Creation ====================
    
    def create_wip_recognition_je(self, recognition_date, amount):
        """
        WIP recognition Journal Entry.

        Dr. Revenue Liability Account (WIP / deferred revenue liability)
        Cr. WIP Account (Income, Job Profit WIP)
        """
        settings = self.get_settings()
        
        je = frappe.new_doc("Journal Entry")
        je.posting_date = recognition_date
        je.company = self.company
        je.voucher_type = "Journal Entry"
        je.user_remark = f"WIP Recognition for {self.job_type} {self.job.name}"
        jcn = self.job.get("job_costing_number")

        # Debit: Revenue Liability (WIP liability) Account
        row = {
            "account": settings.get("revenue_liability_account"),
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            **self._je_account_reference_fields(),
        }
        if jcn:
            row["job_costing_number"] = jcn
        je.append("accounts", row)

        # Credit: WIP Account
        row = {
            "account": settings.get("wip_account"),
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            **self._je_account_reference_fields(),
        }
        if jcn:
            row["job_costing_number"] = jcn
        je.append("accounts", row)

        je.insert()
        je.submit()

        return je.name

    def create_wip_adjustment_je(self, amount, adjustment_date, is_closure=False):
        """
        Create WIP adjustment Journal Entry (reverses WIP recognition).

        Dr. WIP Account
        Cr. Revenue Liability Account
        """
        settings = self.get_settings()
        remark_type = "Closure" if is_closure else "Adjustment"
        
        je = frappe.new_doc("Journal Entry")
        je.posting_date = adjustment_date
        je.company = self.company
        je.voucher_type = "Journal Entry"
        je.user_remark = f"WIP {remark_type} for {self.job_type} {self.job.name}"
        jcn = self.job.get("job_costing_number")

        # Debit: WIP Account
        row = {
            "account": settings.get("wip_account"),
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            **self._je_account_reference_fields(),
        }
        if jcn:
            row["job_costing_number"] = jcn
        je.append("accounts", row)

        # Credit: Revenue Liability Account
        row = {
            "account": settings.get("revenue_liability_account"),
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            **self._je_account_reference_fields(),
        }
        if jcn:
            row["job_costing_number"] = jcn
        je.append("accounts", row)

        je.insert()
        je.submit()

        return je.name

    def create_accrual_recognition_je(self, recognition_date, lines):
        """
        Create Accrual recognition Journal Entry.

        Dr. Cost Accrual Account (Expense)
        Cr. Accrued Cost Liability Account (Liability)

        :param lines: list of dicts ``{"amount": float, "item_code": str|None}`` (Item dimension when configured)
        """
        settings = self.get_settings()

        if isinstance(lines, (int, float)):
            lines = [{"amount": flt(lines), "item_code": None}]
        normalized = []
        for row in lines or []:
            if isinstance(row, (int, float)):
                normalized.append({"amount": flt(row), "item_code": None})
            else:
                normalized.append(
                    {
                        "amount": flt(row.get("amount")),
                        "item_code": row.get("item_code"),
                    }
                )
        normalized = [x for x in normalized if flt(x.get("amount")) > 0]
        if not normalized:
            frappe.throw(_("No accrual amounts to post"))

        je = frappe.new_doc("Journal Entry")
        je.posting_date = recognition_date
        je.company = self.company
        je.voucher_type = "Journal Entry"
        je.user_remark = _("Accrual Recognition for {0} {1}").format(self.job_type, self.job.name)
        jcn = self.job.get("job_costing_number")

        for line in normalized:
            amt = flt(line["amount"])
            item_extra = self._item_dimension_je_row(line.get("item_code"))

            row_dr = {
                "account": settings.get("cost_accrual_account"),
                "debit_in_account_currency": amt,
                "credit_in_account_currency": 0,
                "cost_center": self.job.get("cost_center"),
                "profit_center": self.job.get("profit_center"),
                **self._je_account_reference_fields(),
                **item_extra,
            }
            if jcn:
                row_dr["job_costing_number"] = jcn
            je.append("accounts", row_dr)

            row_cr = {
                "account": settings.get("accrued_cost_liability_account"),
                "debit_in_account_currency": 0,
                "credit_in_account_currency": amt,
                "cost_center": self.job.get("cost_center"),
                "profit_center": self.job.get("profit_center"),
                **self._je_account_reference_fields(),
                **item_extra,
            }
            if jcn:
                row_cr["job_costing_number"] = jcn
            je.append("accounts", row_cr)

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
        jcn = self.job.get("job_costing_number")

        # Debit: Accrued Cost Liability Account
        row = {
            "account": settings.get("accrued_cost_liability_account"),
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            **self._je_account_reference_fields(),
        }
        if jcn:
            row["job_costing_number"] = jcn
        je.append("accounts", row)

        # Credit: Cost Accrual Account
        row = {
            "account": settings.get("cost_accrual_account"),
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount,
            "cost_center": self.job.get("cost_center"),
            "profit_center": self.job.get("profit_center"),
            **self._je_account_reference_fields(),
        }
        if jcn:
            row["job_costing_number"] = jcn
        je.append("accounts", row)

        je.insert()
        je.submit()

        return je.name


# ==================== Settings Resolution ====================

def get_recognition_policy_document(company):
    """Single Revenue Recognition Policy document per company (enabled preferred)."""
    if not company:
        return None
    name = frappe.db.get_value(
        "Recognition Policy Settings",
        {"company": company, "enabled": 1},
        "name",
        order_by="modified desc",
    )
    if not name:
        name = frappe.db.get_value(
            "Recognition Policy Settings",
            {"company": company},
            "name",
            order_by="modified desc",
        )
    if name:
        return frappe.get_doc("Recognition Policy Settings", name)
    return None


def _job_dimensions_for_match(job):
    """Resolve cost_center, profit_center, branch, direction, transport_mode for matching."""
    cc = job.get("cost_center")
    pc = job.get("profit_center")
    br = job.get("branch")
    jcn = job.get("job_costing_number")
    if jcn and frappe.db.exists("Job Costing Number", jcn):
        j = frappe.db.get_value(
            "Job Costing Number",
            jcn,
            ["cost_center", "profit_center", "branch"],
            as_dict=True,
        )
        if j:
            cc = cc or j.cost_center
            pc = pc or j.profit_center
            br = br or j.branch
    direction = (job.get("direction") or "").strip() or None
    mode = job.get("transport_mode") or None
    return cc, pc, br, direction, mode


def _parameter_row_specificity(row):
    n = 0
    for f in ("branch", "profit_center", "cost_center", "direction", "transport_mode"):
        if row.get(f):
            n += 1
    return n


def _row_matches_dimensions(row, cc, pc, br, direction, mode):
    if row.get("branch") and row.branch != br:
        return False
    if row.get("profit_center") and row.profit_center != pc:
        return False
    if row.get("cost_center") and row.cost_center != cc:
        return False
    if row.get("direction") and row.direction != direction:
        return False
    if row.get("transport_mode") and row.transport_mode != mode:
        return False
    return True


def _basis_from_row(row):
    if not row:
        return "Job Booking Date"
    b = (
        row.get("recognition_date_basis")
        or row.get("wip_recognition_date_basis")
        or row.get("accrual_recognition_date_basis")
    )
    return (b or "Job Booking Date").strip() or "Job Booking Date"


def _legacy_parameter_dict(policy_doc):
    """Build virtual parameter row from pre–child-table header fields."""
    if not policy_doc.get("wip_account"):
        return None
    return frappe._dict(
        recognition_date_basis=_basis_from_row(policy_doc),
        wip_account=policy_doc.wip_account,
        revenue_liability_account=policy_doc.revenue_liability_account,
        cost_accrual_account=policy_doc.cost_accrual_account,
        accrued_cost_liability_account=policy_doc.accrued_cost_liability_account,
        branch=policy_doc.get("branch"),
        profit_center=policy_doc.get("profit_center"),
        cost_center=policy_doc.get("cost_center"),
        direction=None,
        transport_mode=None,
        priority=policy_doc.get("priority") or 0,
    )


def match_parameter_row_for_job(policy_doc, job):
    """
    Pick the best Recognition Policy Parameter row for this job.
    More specific rows (more non-blank match fields) win; then higher priority.
    """
    rows = list(policy_doc.get("recognition_parameters") or [])
    if not rows:
        leg = _legacy_parameter_dict(policy_doc)
        return leg

    cc, pc, br, direction, mode = _job_dimensions_for_match(job)
    candidates = []
    for row in rows:
        if _row_matches_dimensions(row, cc, pc, br, direction, mode):
            spec = _parameter_row_specificity(row)
            pri = row.priority or 0
            candidates.append((spec, pri, row))

    if not candidates:
        blank = [r for r in rows if _parameter_row_specificity(r) == 0]
        if blank:
            row = max(blank, key=lambda r: (r.priority or 0, -rows.index(r)))
            return row
        return rows[0]

    candidates.sort(key=lambda x: (-x[0], -x[1], rows.index(x[2])))
    return candidates[0][2]


def resolve_policy_row_for_job(job):
    policy = get_recognition_policy_document(job.company)
    if not policy:
        return None, None
    row = match_parameter_row_for_job(policy, job)
    return policy, row


def _row_to_settings_map(row):
    if not row:
        return None
    return {
        "recognition_date_basis": _basis_from_row(row),
        "wip_account": row.get("wip_account"),
        "revenue_liability_account": row.get("revenue_liability_account"),
        "cost_accrual_account": row.get("cost_accrual_account"),
        "accrued_cost_liability_account": row.get("accrued_cost_liability_account"),
    }


def get_recognition_settings(job):
    """
    Recognition settings for a job: company policy + best-matching parameter row.
    """
    company = job.company
    result = {
        "enable_wip_recognition": False,
        "enable_accrual_recognition": False,
        "recognition_date_basis": "Job Booking Date",
        "wip_account": None,
        "revenue_liability_account": None,
        "cost_accrual_account": None,
        "accrued_cost_liability_account": None,
        "minimum_wip_amount": 0,
        "minimum_accrual_amount": 0,
        "recognition_policy_name": None,
        "matched_parameter_label": None,
    }

    policy, row = resolve_policy_row_for_job(job)
    if policy and policy.enabled:
        result["enable_wip_recognition"] = bool(policy.enable_wip_recognition)
        result["enable_accrual_recognition"] = bool(policy.enable_accrual_recognition)
        result["minimum_wip_amount"] = flt(policy.minimum_wip_amount) or 0
        result["minimum_accrual_amount"] = flt(policy.minimum_accrual_amount) or 0
        result["recognition_policy_name"] = policy.name
        sm = _row_to_settings_map(row)
        if sm:
            result.update(sm)
        parts = []
        if row:
            for label, f in (
                ("Branch", "branch"),
                ("PC", "profit_center"),
                ("CC", "cost_center"),
                ("Dir", "direction"),
                ("Mode", "transport_mode"),
            ):
                v = row.get(f)
                if v:
                    parts.append(f"{label}:{v}")
        result["matched_parameter_label"] = ", ".join(parts) if parts else _("Default parameters")

    if hasattr(job, "wip_recognition_enabled") and job.wip_recognition_enabled is not None:
        result["enable_wip_recognition"] = bool(job.wip_recognition_enabled)
    if hasattr(job, "accrual_recognition_enabled") and job.accrual_recognition_enabled is not None:
        result["enable_accrual_recognition"] = bool(job.accrual_recognition_enabled)
    if getattr(job, "recognition_date_basis", None):
        result["recognition_date_basis"] = job.recognition_date_basis
    elif getattr(job, "wip_recognition_date_basis", None):
        result["recognition_date_basis"] = job.wip_recognition_date_basis
    elif getattr(job, "accrual_recognition_date_basis", None):
        result["recognition_date_basis"] = job.accrual_recognition_date_basis

    return result


def get_recognition_policy_for_job(job_costing_number):
    """
    Parameter row + accounts for a Job Costing Number (JCN dimensions only;
    Direction/Mode are not on JCN — matching uses wildcard for those).
    """
    if not job_costing_number or not frappe.db.exists("Job Costing Number", job_costing_number):
        return None
    jcn = frappe.get_doc("Job Costing Number", job_costing_number)
    job = frappe._dict(
        company=jcn.company,
        cost_center=jcn.get("cost_center"),
        profit_center=jcn.get("profit_center"),
        branch=jcn.get("branch"),
        job_costing_number=job_costing_number,
        direction=None,
        transport_mode=None,
    )
    policy, row = resolve_policy_row_for_job(job)
    if not row:
        return None
    return frappe._dict(
        name=policy.name if policy else None,
        wip_account=row.get("wip_account"),
        revenue_liability_account=row.get("revenue_liability_account"),
        cost_accrual_account=row.get("cost_accrual_account"),
        accrued_cost_liability_account=row.get("accrued_cost_liability_account"),
    )


def get_recognition_policy_by_dimensions(company, cost_center=None, profit_center=None, branch=None):
    """Backward-compatible: return a dict-like object with account fields from best row."""
    job = frappe._dict(
        company=company,
        cost_center=cost_center,
        profit_center=profit_center,
        branch=branch,
        job_costing_number=None,
        direction=None,
        transport_mode=None,
    )
    policy, row = resolve_policy_row_for_job(job)
    if not policy or not row:
        return None
    return frappe._dict(
        name=policy.name,
        company=policy.company,
        enable_wip_recognition=policy.enable_wip_recognition,
        enable_accrual_recognition=policy.enable_accrual_recognition,
        wip_account=row.get("wip_account"),
        revenue_liability_account=row.get("revenue_liability_account"),
        cost_accrual_account=row.get("cost_accrual_account"),
        accrued_cost_liability_account=row.get("accrued_cost_liability_account"),
    )


@frappe.whitelist()
def get_recognition_policy_display(
    doctype=None,
    docname=None,
    company=None,
    cost_center=None,
    profit_center=None,
    branch=None,
    job_costing_number=None,
    recognition_date_override=None,
):
    """Populate Revenue & Cost Recognition section (policy reference + resolved dates)."""
    if doctype and docname and frappe.db.exists(doctype, docname):
        job = frappe.get_doc(doctype, docname)
    else:
        job = frappe._dict(
            doctype="General Job",
            name="preview",
            company=company,
            cost_center=cost_center or None,
            profit_center=profit_center or None,
            branch=branch or None,
            job_costing_number=job_costing_number or None,
            direction=None,
            transport_mode=None,
            creation=nowdate(),
        )
    if recognition_date_override:
        job.recognition_date = recognition_date_override

    policy, row = resolve_policy_row_for_job(job)
    out = {
        "wip_recognition_enabled": 0,
        "accrual_recognition_enabled": 0,
        "recognition_date_basis": "Job Booking Date",
        "recognition_policy_reference": "",
        "recognition_date": None,
    }

    if not policy:
        return out

    out["wip_recognition_enabled"] = 1 if policy.enable_wip_recognition else 0
    out["accrual_recognition_enabled"] = 1 if policy.enable_accrual_recognition else 0
    if row:
        out["recognition_date_basis"] = _basis_from_row(row)

    label = get_recognition_settings(job).get("matched_parameter_label") or ""
    out["recognition_policy_reference"] = f"{policy.name}"
    if label:
        out["recognition_policy_reference"] += f" — {label}"

    try:
        eng = RecognitionEngine(job)
        rd = eng.get_recognition_date()
        if rd:
            out["recognition_date"] = str(getdate(rd))
    except Exception:
        pass

    return out


def sync_job_recognition_fields_from_policy(doc):
    """
    Persist Revenue & Cost Recognition fields from policy (same data as client
    recognition_policy_fields.js). Keeps DB/list views aligned with policy.
    """
    if not doc:
        return
    try:
        company = doc.get("company")
        if not company:
            doc.wip_recognition_enabled = 0
            doc.accrual_recognition_enabled = 0
            doc.recognition_date_basis = "Job Booking Date"
            doc.recognition_policy_reference = ""
            if doc.meta.has_field("recognition_date"):
                doc.recognition_date = None
            return

        doctype_, docname_ = None, None
        if doc.get("name") and frappe.db.exists(doc.doctype, doc.name):
            doctype_, docname_ = doc.doctype, doc.name

        override = None
        if doc.get("recognition_date_basis") == "User Specified" and doc.get("recognition_date"):
            override = doc.recognition_date

        m = get_recognition_policy_display(
            doctype=doctype_,
            docname=docname_,
            company=company,
            cost_center=doc.get("cost_center") or "",
            profit_center=doc.get("profit_center") or "",
            branch=doc.get("branch") or "",
            job_costing_number=doc.get("job_costing_number") or "",
            recognition_date_override=override,
        )
        doc.wip_recognition_enabled = cint(m.get("wip_recognition_enabled"))
        doc.accrual_recognition_enabled = cint(m.get("accrual_recognition_enabled"))
        doc.recognition_date_basis = m.get("recognition_date_basis") or "Job Booking Date"
        doc.recognition_policy_reference = m.get("recognition_policy_reference") or ""
        if doc.get("recognition_date_basis") != "User Specified":
            rd = m.get("recognition_date")
            if rd:
                doc.recognition_date = getdate(rd)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "sync_job_recognition_fields_from_policy")


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


def _get_nothing_to_recognize_reason(job, engine):
    """Return a user-facing reason when neither WIP nor accrual was recognized."""
    settings = engine.get_settings()
    est_revenue = engine.calculate_estimated_revenue()
    est_costs = engine.calculate_estimated_costs()

    reasons = []
    if job.get("wip_journal_entry"):
        reasons.append(_("WIP already recognized"))
    elif not settings.get("enable_wip_recognition"):
        reasons.append(_("WIP recognition is disabled in Recognition Policy Settings"))
    elif est_revenue <= 0:
        reasons.append(_("Estimated revenue is zero (add charges with selling amount)"))
    elif settings.get("minimum_wip_amount") and est_revenue < settings.get("minimum_wip_amount"):
        reasons.append(_("Estimated revenue {0} is below minimum WIP {1}").format(
            est_revenue, settings.get("minimum_wip_amount")))

    if job.get("accrual_journal_entry"):
        reasons.append(_("Accrual already recognized"))
    elif not settings.get("enable_accrual_recognition"):
        reasons.append(_("Accrual recognition is disabled in Recognition Policy Settings"))
    elif est_costs <= 0:
        reasons.append(_("Estimated costs are zero (add charges with cost)"))
    elif settings.get("minimum_accrual_amount") and est_costs < settings.get("minimum_accrual_amount"):
        reasons.append(_("Estimated costs {0} are below minimum accrual {1}").format(
            est_costs, settings.get("minimum_accrual_amount")))

    if not reasons:
        return _("Nothing to recognize (already recognized or below minimum)")
    return " ".join(reasons)


@frappe.whitelist()
def recognize(doctype, docname, recognition_date=None):
    """
    API to recognize WIP and accruals for a job (manual action).
    Runs both WIP and accrual recognition based on Recognition Policy Settings.
    
    Args:
        doctype: The job document type
        docname: The job document name
        recognition_date: Optional recognition date
    
    Returns:
        dict: Names of created Journal Entries and status
    """
    job = frappe.get_doc(doctype, docname)
    # Allow recognition on both draft (0) and submitted (1) documents
    engine = RecognitionEngine(job)
    result = {"wip_journal_entry": None, "accrual_journal_entry": None}
    
    try:
        wip_je = engine.recognize_wip(recognition_date)
        if wip_je:
            result["wip_journal_entry"] = wip_je
    except Exception as e:
        if "already been recognized" not in str(e).lower():
            raise
        # Already recognized - skip
    try:
        accrual_je = engine.recognize_accruals(recognition_date)
        if accrual_je:
            result["accrual_journal_entry"] = accrual_je
    except Exception as e:
        if "already been recognized" not in str(e).lower():
            raise
        # Already recognized - skip

    # When nothing was recognized, return a clear reason for the user
    if not result["wip_journal_entry"] and not result["accrual_journal_entry"]:
        result["message"] = _get_nothing_to_recognize_reason(job, engine)

    return result


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
        "Warehouse Job", "Declaration", "General Job"
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
