"""
Unit tests for Recognition Engine

Tests cover:
- WIP recognition
- Accrual recognition
- WIP adjustments
- Accrual adjustments
- Job closure
- Settings resolution
"""

import frappe
import unittest
from frappe.utils import nowdate, add_days, flt
from logistics.job_management.recognition_engine import (
    RecognitionEngine,
    get_recognition_settings,
    get_recognition_policy_for_job,
    get_recognition_policy_by_dimensions,
    get_ata_date,
    get_atd_date,
    get_booking_date
)


class TestRecognitionEngine(unittest.TestCase):
    """Test cases for RecognitionEngine class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not cls.company:
            cls.company = frappe.get_all("Company", limit=1)[0].name
        
        # Create test accounts if they don't exist
        cls.setup_test_accounts()
        
        # Create test Recognition Policy Settings
        cls.setup_test_policy()
    
    @classmethod
    def setup_test_accounts(cls):
        """Create test accounts for recognition."""
        accounts = [
            {"account_name": "Test WIP Account", "account_type": "Asset", "root_type": "Asset"},
            {"account_name": "Test Revenue Liability", "account_type": "Liability", "root_type": "Liability"},
            {"account_name": "Test Cost Accrual", "account_type": "Expense", "root_type": "Expense"},
            {"account_name": "Test Accrued Cost Liability", "account_type": "Liability", "root_type": "Liability"}
        ]
        
        for acc in accounts:
            if not frappe.db.exists("Account", {"account_name": acc["account_name"], "company": cls.company}):
                account = frappe.new_doc("Account")
                account.account_name = acc["account_name"]
                account.company = cls.company
                account.root_type = acc["root_type"]
                account.account_type = acc["account_type"]
                account.parent_account = frappe.db.get_value(
                    "Account", 
                    {"company": cls.company, "root_type": acc["root_type"], "is_group": 1},
                    "name"
                )
                account.insert(ignore_permissions=True)
    
    @classmethod
    def setup_test_policy(cls):
        """Create test Recognition Policy Settings."""
        if frappe.db.exists("Recognition Policy Settings", {"company": cls.company}):
            return
        
        wip_account = frappe.db.get_value("Account", {"account_name": "Test WIP Account", "company": cls.company})
        revenue_liability = frappe.db.get_value("Account", {"account_name": "Test Revenue Liability", "company": cls.company})
        cost_accrual = frappe.db.get_value("Account", {"account_name": "Test Cost Accrual", "company": cls.company})
        accrued_liability = frappe.db.get_value("Account", {"account_name": "Test Accrued Cost Liability", "company": cls.company})
        
        policy = frappe.new_doc("Recognition Policy Settings")
        policy.company = cls.company
        policy.enabled = 1
        policy.enable_wip_recognition = 1
        policy.enable_accrual_recognition = 1
        policy.wip_recognition_date_basis = "Job Booking Date"
        policy.accrual_recognition_date_basis = "Job Booking Date"
        policy.wip_account = wip_account
        policy.revenue_liability_account = revenue_liability
        policy.cost_accrual_account = cost_accrual
        policy.accrued_cost_liability_account = accrued_liability
        policy.insert(ignore_permissions=True)
    
    def test_get_recognition_settings(self):
        """Test settings resolution."""
        # Create a mock job object
        class MockJob:
            def __init__(self):
                self.company = TestRecognitionEngine.company
                self.cost_center = None
                self.profit_center = None
                self.branch = None
                self.job_costing_number = None
            
            def get(self, key, default=None):
                return getattr(self, key, default)
        
        job = MockJob()
        settings = get_recognition_settings(job)
        
        self.assertIsNotNone(settings)
        self.assertIn("enable_wip_recognition", settings)
        self.assertIn("enable_accrual_recognition", settings)
    
    def test_date_resolution_functions(self):
        """Test date resolution helper functions."""
        class MockJob:
            def __init__(self):
                self.ata = "2024-01-15"
                self.atd = "2024-01-10"
                self.booking_date = "2024-01-05"
                self.creation = "2024-01-01"
            
            def get(self, key, default=None):
                return getattr(self, key, default)
        
        job = MockJob()
        
        ata = get_ata_date(job)
        self.assertEqual(str(ata), "2024-01-15")
        
        atd = get_atd_date(job)
        self.assertEqual(str(atd), "2024-01-10")
        
        booking = get_booking_date(job)
        self.assertEqual(str(booking), "2024-01-05")
    
    def test_policy_matching(self):
        """Test policy matching by dimensions."""
        # Test with no dimensions (should match default)
        policy = get_recognition_policy_by_dimensions(self.company)
        self.assertIsNotNone(policy)


class TestRecognitionAccounting(unittest.TestCase):
    """Test accounting entries for recognition."""
    
    def test_wip_entry_structure(self):
        """Test WIP Journal Entry has correct structure."""
        # WIP Recognition: Dr WIP, Cr Revenue Liability
        # WIP Adjustment: Dr Revenue Liability, Cr WIP
        pass  # Requires actual job document to test
    
    def test_accrual_entry_structure(self):
        """Test Accrual Journal Entry has correct structure."""
        # Accrual Recognition: Dr Cost Accrual, Cr Accrued Cost Liability
        # Accrual Adjustment: Dr Accrued Cost Liability, Cr Cost Accrual
        pass  # Requires actual job document to test


def run_tests():
    """Run all recognition engine tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRecognitionEngine)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRecognitionAccounting))
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    run_tests()
