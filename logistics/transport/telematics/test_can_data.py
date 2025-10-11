#!/usr/bin/env python3
"""
Test script to trigger CAN data fetching for a specific vehicle
Usage: python test_can_data.py <vehicle_name>
"""

import sys
import frappe

def test_can_data(vehicle_name):
    """Test CAN data fetching for a specific vehicle"""
    try:
        # Get the vehicle document
        vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
        
        print(f"Testing CAN data for vehicle: {vehicle.name}")
        print(f"Telematics Provider: {vehicle.telematics_provider}")
        print(f"External ID: {vehicle.telematics_external_id}")
        
        # Call the get_can_data method
        result = vehicle.get_can_data()
        
        print("\n=== CAN Data Results ===")
        print(f"Timestamp: {result.get('timestamp')}")
        print(f"Fuel Level: {result.get('fuel_level')}%")
        print(f"RPM: {result.get('rpm')}")
        print(f"Engine Hours: {result.get('engine_hours')}")
        print(f"Coolant Temp: {result.get('coolant_temp')}°C")
        print(f"Ambient Temp: {result.get('ambient_temp')}°C")
        
        return result
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_can_data.py <vehicle_name>")
        sys.exit(1)
    
    vehicle_name = sys.argv[1]
    test_can_data(vehicle_name)
