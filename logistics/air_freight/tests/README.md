# Air Freight Module - Automated Testing

This directory contains automated unit tests for the Air Freight module, following Frappe Framework testing guidelines.

## Test Files

The test suite includes the following test files:

1. **test_air_freight_settings.py** - Tests for Air Freight Settings doctype
   - Settings creation and validation
   - Field validations (volume to weight factor, consolidation limits, etc.)
   - Static methods (get_settings, get_default_value)
   - Cache clearing on update

2. **test_air_freight_rate.py** - Tests for Air Freight Rate doctype
   - Rate creation and validation
   - Date validation (valid_from, valid_to)
   - Calculation method validation
   - Rate calculation functionality
   - Route-based rates

3. **test_air_shipment.py** - Tests for Air Shipment doctype
   - Shipment creation
   - Date validations
   - Weight and volume validations
   - Dangerous goods validation
   - Sustainability metrics calculation
   - Milestone HTML generation
   - Package validations

4. **test_airline.py** - Tests for Airline doctype
   - Airline creation
   - Basic field validations
   - Contact information handling
   - Update operations

5. **test_air_booking.py** - Tests for Air Booking doctype
   - Booking creation
   - Required field validations
   - Date validations (ETD/ETA)
   - Accounts validation
   - Package handling

6. **test_air_consolidation.py** - Tests for Air Consolidation doctype
   - Consolidation creation
   - Validation methods
   - Before save and after insert hooks

7. **test_master_air_waybill.py** - Tests for Master Air Waybill doctype
   - MAWB creation
   - Auto-linking to flight schedules
   - Validation and update hooks

## Running Tests

### Prerequisites

1. Ensure you have a Frappe site set up
2. Make sure the Logistics app is installed on your site
3. Ensure all required master data exists (Company, Customer, etc.)

### Running All Tests

To run all Air Freight module tests:

```bash
cd /home/frappe/frappe-bench
bench --site [your-site-name] run-tests --app logistics --module logistics.air_freight.tests
```

### Running Specific Test Files

To run a specific test file:

```bash
bench --site [your-site-name] run-tests --app logistics --module logistics.air_freight.tests.test_air_freight_settings
```

### Running Specific Test Cases

To run a specific test case within a file:

```bash
bench --site [your-site-name] run-tests --app logistics --module logistics.air_freight.tests.test_air_freight_settings.TestAirFreightSettings.test_air_freight_settings_creation
```

### Running Tests with Verbose Output

For more detailed output:

```bash
bench --site [your-site-name] run-tests --app logistics --module logistics.air_freight.tests --verbose
```

## Test Structure

Each test file follows the standard Frappe testing pattern:

```python
import frappe
import unittest
from frappe.tests.utils import FrappeTestCase

class TestDocTypeName(FrappeTestCase):
    def setUp(self):
        # Set up test data
        
    def tearDown(self):
        # Clean up test data
        
    def test_something(self):
        # Test case
```

## Writing New Tests

When adding new tests:

1. Follow the naming convention: `test_<doctype_name>.py`
2. Inherit from `FrappeTestCase`
3. Use `setUp()` to create necessary test data
4. Use `tearDown()` to clean up (though `frappe.db.rollback()` is usually sufficient)
5. Name test methods with `test_` prefix
6. Use descriptive test method names

## Test Coverage

The current test suite covers:

- ✅ Document creation and basic CRUD operations
- ✅ Field validations
- ✅ Date validations
- ✅ Business logic validations
- ✅ Static methods and helper functions
- ✅ Document hooks (before_save, after_insert, on_update)

## Continuous Integration

These tests can be integrated into CI/CD pipelines. Example for GitHub Actions:

```yaml
- name: Run Air Freight Tests
  run: |
    bench --site test_site run-tests --app logistics --module logistics.air_freight.tests
```

## Troubleshooting

### Common Issues

1. **Missing Master Data**: Some tests require Company, Customer, or other master data. Ensure these exist or are created in `setUp()`.

2. **Database Rollback**: Tests use `frappe.db.rollback()` in `tearDown()` to clean up. If tests fail, data may persist.

3. **Validation Errors**: Some validations may depend on settings or other documents. Adjust test data accordingly.

4. **Import Errors**: Ensure all required modules are imported and available.

## References

- [Frappe Testing Documentation](https://docs.frappe.io/framework/user/en/guides/automated-testing)
- [Frappe Unit Testing Guide](https://docs.frappe.io/framework/user/en/guides/automated-testing/unit-testing)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)

## Contributing

When adding new features to the Air Freight module:

1. Write tests first (TDD approach) or alongside the feature
2. Ensure all tests pass before submitting
3. Add tests for edge cases and error conditions
4. Update this README if adding new test files or patterns

