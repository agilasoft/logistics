#!/usr/bin/env python3
"""
Debug Remora API responses for a specific vehicle
Shows detailed SOAP request/response information
"""

import frappe
from datetime import datetime, timedelta

def debug_vehicle_remora_api(vehicle_name):
    """Debug Remora API responses for a specific vehicle with full request/response details"""
    print(f"🔍 Debugging Remora API for Vehicle: {vehicle_name}")
    print("=" * 60)
    
    try:
        # Get vehicle document
        vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
        
        if not vehicle.telematics_external_id:
            print("❌ No telematics external ID configured for this vehicle")
            return
        
        print(f"📋 Vehicle: {vehicle.name}")
        print(f"📋 External ID: {vehicle.telematics_external_id}")
        print(f"📋 Provider: {vehicle.telematics_provider}")
        
        # Get provider configuration
        from logistics.transport.telematics.resolve import _provider_conf
        conf = _provider_conf(vehicle.telematics_provider)
        
        if not conf:
            print("❌ Provider not found or not enabled")
            return
        
        print(f"📋 Provider Type: {conf.get('provider_type')}")
        print(f"📋 Username: {conf.get('username')}")
        
        # Enable debug mode in configuration
        conf["debug"] = 1
        conf["request_timeout_sec"] = 30
        
        print(f"\n🔧 Configuration with debug enabled:")
        print(f"   Debug: {conf.get('debug')}")
        print(f"   Timeout: {conf.get('request_timeout_sec')}s")
        
        # Initialize Remora provider with debug mode
        from logistics.transport.telematics.providers.remora import RemoraProvider
        provider = RemoraProvider(conf)
        
        print(f"\n📡 Testing API Connection...")
        print("=" * 40)
        
        # Test 1: Get Version Info
        print("🔍 1. Testing GetVersionInfo...")
        try:
            version_info = provider.GetVersionInfo()
            print(f"✅ Version Info: {version_info}")
        except Exception as e:
            print(f"❌ GetVersionInfo failed: {e}")
        
        # Test 2: Get Devices
        print(f"\n🔍 2. Testing GetDevices...")
        try:
            devices = provider.GetDevices()
            print(f"✅ Found {len(devices)} devices")
            for i, device in enumerate(devices[:3]):  # Show first 3 devices
                device_id = device.get("deviceId") or device.get("DeviceId")
                device_name = device.get("name") or device.get("Name") or "Unknown"
                print(f"   Device {i+1}: {device_id} ({device_name})")
        except Exception as e:
            print(f"❌ GetDevices failed: {e}")
        
        # Test 3: Get Positions
        print(f"\n🔍 3. Testing GetPositions...")
        try:
            positions = list(provider.fetch_latest_positions())
            print(f"✅ Found {len(positions)} positions")
            for i, pos in enumerate(positions[:3]):  # Show first 3 positions
                print(f"   Position {i+1}: {pos.get('device_id')} at {pos.get('latitude')}, {pos.get('longitude')}")
        except Exception as e:
            print(f"❌ GetPositions failed: {e}")
        
        # Test 4: Get Positions for specific vehicle
        if vehicle.telematics_external_id:
            print(f"\n🔍 4. Testing GetPositionsByInterval for vehicle {vehicle.telematics_external_id}...")
            try:
                # Get positions for last 24 hours
                end_time = datetime.now()
                start_time = end_time - timedelta(days=1)
                
                positions = provider.GetPositionsByInterval(
                    vehicle.telematics_external_id, 
                    start_time, 
                    end_time
                )
                print(f"✅ Found {len(positions)} positions for vehicle in last 24h")
                for i, pos in enumerate(positions[:3]):  # Show first 3 positions
                    coord = pos.get("coordinate", {})
                    lat = coord.get("latitude") if "latitude" in coord else coord.get("lat")
                    lon = coord.get("longitude") if "longitude" in coord else coord.get("lon")
                    print(f"   Position {i+1}: {lat}, {lon} at {pos.get('dateTime')}")
            except Exception as e:
                print(f"❌ GetPositionsByInterval failed: {e}")
        
        print(f"\n✅ Debug complete!")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run debug for a specific vehicle"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python debug_vehicle_remora.py <vehicle_name>")
        print("Example: python debug_vehicle_remora.py 'VEH-001'")
        return
    
    vehicle_name = sys.argv[1]
    debug_vehicle_remora_api(vehicle_name)

if __name__ == "__main__":
    main()
