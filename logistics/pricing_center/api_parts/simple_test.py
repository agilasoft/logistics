# Simple test for Transport Rate Calculation Engine
# Run this in Frappe console: bench --site [site] console

def test_transport_calculations():
    """Simple test function for Transport Rate calculations"""
    
    print("Testing Transport Rate Calculation Engine...")
    
    try:
        # Import the calculation engine
        from logistics.pricing_center.api_parts.transport_rate_calculation_engine import TransportRateCalculationEngine
        
        # Initialize calculator
        calculator = TransportRateCalculationEngine()
        
        # Test 1: Per Unit calculation
        print("\nTest 1: Per Unit - Weight Based")
        rate_data = {
            'calculation_method': 'Per Unit',
            'rate': 10.50,
            'unit_type': 'Weight',
            'currency': 'USD',
            'item_code': 'TRANS-001',
            'item_name': 'Transport Service'
        }
        
        result = calculator.calculate_transport_rate(
            rate_data=rate_data,
            actual_weight=100  # 100 kg
        )
        
        print(f"Result: {result}")
        expected = 1050.00  # 10.50 * 100
        if result.get('success') and abs(result.get('amount', 0) - expected) < 0.01:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
        
        # Test 2: Fixed Amount
        print("\nTest 2: Fixed Amount")
        rate_data = {
            'calculation_method': 'Fixed Amount',
            'fixed_amount': 500.00,
            'currency': 'USD',
            'item_code': 'TRANS-002',
            'item_name': 'Fixed Transport'
        }
        
        result = calculator.calculate_transport_rate(
            rate_data=rate_data,
            actual_weight=100
        )
        
        print(f"Result: {result}")
        expected = 500.00
        if result.get('success') and abs(result.get('amount', 0) - expected) < 0.01:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
        
        # Test 3: Base Plus Additional
        print("\nTest 3: Base Plus Additional")
        rate_data = {
            'calculation_method': 'Base Plus Additional',
            'base_amount': 200.00,
            'rate': 5.00,
            'unit_type': 'Weight',
            'currency': 'USD',
            'item_code': 'TRANS-003',
            'item_name': 'Base Plus Transport'
        }
        
        result = calculator.calculate_transport_rate(
            rate_data=rate_data,
            actual_weight=50  # 50 kg
        )
        
        print(f"Result: {result}")
        expected = 450.00  # 200 + (5 * 50)
        if result.get('success') and abs(result.get('amount', 0) - expected) < 0.01:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
        
        print("\n🎉 Basic tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Run the test
if __name__ == "__main__":
    test_transport_calculations()


