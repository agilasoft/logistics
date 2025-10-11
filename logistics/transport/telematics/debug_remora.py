#!/usr/bin/env python3
"""
Remora Telematics Debug Script
Diagnoses common issues with Remora integration
"""

import frappe
import sys
from datetime import datetime, timedelta

def check_remora_configuration():
    """Check Remora telematics provider configuration"""
    print("🔍 Checking Remora Telematics Configuration...")
    print("=" * 50)
    
    # Check if any telematics providers exist
    providers = frappe.get_all("Telematics Provider", 
                             filters={"provider_type": "REMORA"},
                             fields=["name", "enabled", "username", "soap_endpoint_override", "soap_version"])
    
    if not providers:
        print("❌ No REMORA telematics providers found!")
        print("   Create a Telematics Provider with provider_type = 'REMORA'")
        return False
    
    print(f"✅ Found {len(providers)} REMORA provider(s)")
    
    for provider in providers:
        print(f"\n📋 Provider: {provider.name}")
        print(f"   Enabled: {provider.enabled}")
        print(f"   Username: {'✅ Set' if provider.username else '❌ Missing'}")
        print(f"   SOAP Endpoint: {provider.soap_endpoint_override or 'Using default'}")
        print(f"   SOAP Version: {provider.soap_version or 'SOAP11 (default)'}")
        
        if not provider.enabled:
            print("   ⚠️  Provider is disabled!")
        if not provider.username:
            print("   ⚠️  Username is missing!")
    
    return True

def check_vehicle_mapping():
    """Check vehicle telematics mapping"""
    print("\n🚗 Checking Vehicle Telematics Mapping...")
    print("=" * 50)
    
    vehicles = frappe.get_all("Transport Vehicle",
                             fields=["name", "telematics_provider", "telematics_external_id"])
    
    mapped_vehicles = [v for v in vehicles if v.telematics_external_id]
    
    print(f"📊 Total Vehicles: {len(vehicles)}")
    print(f"📊 Mapped Vehicles: {len(mapped_vehicles)}")
    
    if not mapped_vehicles:
        print("❌ No vehicles have telematics_external_id set!")
        print("   Set telematics_external_id on Transport Vehicle records")
        return False
    
    print("\n🚗 Mapped Vehicles:")
    for vehicle in mapped_vehicles:
        print(f"   • {vehicle.name} -> External ID: {vehicle.telematics_external_id}")
        if not vehicle.telematics_provider:
            print(f"     ⚠️  No telematics provider assigned (will use default)")
    
    return True

def check_transport_settings():
    """Check Transport Settings for telematics configuration"""
    print("\n⚙️ Checking Transport Settings...")
    print("=" * 50)
    
    try:
        settings = frappe.get_single("Transport Settings")
        default_provider = settings.default_telematics_provider
        poll_interval = settings.telematics_poll_interval_min
        
        print(f"📋 Default Telematics Provider: {default_provider or 'Not set'}")
        print(f"📋 Poll Interval: {poll_interval or 5} minutes")
        
        if not default_provider:
            print("⚠️  No default telematics provider set in Transport Settings")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error reading Transport Settings: {e}")
        return False

def test_remora_connection():
    """Test Remora API connection"""
    print("\n🔌 Testing Remora API Connection...")
    print("=" * 50)
    
    try:
        from logistics.transport.telematics.providers.remora import RemoraProvider
        
        # Get first enabled REMORA provider
        providers = frappe.get_all("Telematics Provider", 
                                 filters={"provider_type": "REMORA", "enabled": 1},
                                 fields=["name"])
        
        if not providers:
            print("❌ No enabled REMORA providers found!")
            return False
        
        provider_name = providers[0].name
        provider_doc = frappe.get_doc("Telematics Provider", provider_name)
        
        # Build configuration
        config = {
            "username": provider_doc.username,
            "password": frappe.utils.password.get_decrypted_password("Telematics Provider", provider_name, "password"),
            "soap_endpoint_override": provider_doc.soap_endpoint_override,
            "soap_version": provider_doc.soap_version,
            "debug": 1,  # Enable debug mode
            "request_timeout_sec": 30  # Longer timeout for debugging
        }
        
        print(f"🔧 Testing connection to: {config.get('soap_endpoint_override', 'Default endpoint')}")
        
        # Initialize provider
        provider = RemoraProvider(config)
        
        # Test basic connection with GetVersionInfo
        print("📡 Calling GetVersionInfo...")
        version_info = provider.GetVersionInfo()
        print(f"✅ Connection successful!")
        print(f"📋 Version Info: {version_info}")
        
        # Test fetching devices
        print("📡 Testing GetDevices...")
        devices = provider.GetDevices()
        print(f"📊 Found {len(devices)} devices")
        
        # Test fetching positions if devices available
        if devices:
            print("📡 Testing GetPositions...")
            positions = list(provider.fetch_latest_positions())
            print(f"📊 Found {len(positions)} positions")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running this from the Frappe bench environment")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Check your credentials and endpoint configuration")
        return False

def test_vehicle_data_fetch():
    """Test fetching vehicle data from Remora"""
    print("\n📡 Testing Vehicle Data Fetch...")
    print("=" * 50)
    
    try:
        from logistics.transport.telematics.ingest import _vehicles_with_mapping
        
        vehicles = _vehicles_with_mapping()
        if not vehicles:
            print("❌ No vehicles with telematics mapping found!")
            return False
        
        print(f"📊 Found {len(vehicles)} vehicles with mapping")
        
        # Test with first vehicle
        test_vehicle = vehicles[0]
        print(f"🧪 Testing with vehicle: {test_vehicle['vehicle']}")
        print(f"   External ID: {test_vehicle['external_id']}")
        print(f"   Provider: {test_vehicle['provider_doc']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing vehicle data fetch: {e}")
        return False

def debug_specific_vehicle(vehicle_name):
    """Debug Remora API responses for a specific vehicle with full request/response details"""
    print(f"\n🔍 Debugging Remora API for Vehicle: {vehicle_name}")
    print("=" * 60)
    
    try:
        # Get vehicle document
        vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
        
        if not vehicle.telematics_external_id:
            print("❌ No telematics external ID configured for this vehicle")
            return False
        
        print(f"📋 Vehicle: {vehicle.name}")
        print(f"📋 External ID: {vehicle.telematics_external_id}")
        print(f"📋 Provider: {vehicle.telematics_provider}")
        
        # Get provider configuration
        from logistics.transport.telematics.resolve import _provider_conf
        conf = _provider_conf(vehicle.telematics_provider)
        
        if not conf:
            print("❌ Provider not found or not enabled")
            return False
        
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
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic checks or debug specific vehicle"""
    import sys
    
    # Check if vehicle name provided as argument
    if len(sys.argv) > 1:
        vehicle_name = sys.argv[1]
        print("🚀 Remora Vehicle-Specific Debug Tool")
        print("=" * 60)
        return debug_specific_vehicle(vehicle_name)
    
    print("🚀 Remora Telematics Diagnostic Tool")
    print("=" * 60)
    
    checks = [
        ("Configuration", check_remora_configuration),
        ("Vehicle Mapping", check_vehicle_mapping),
        ("Transport Settings", check_transport_settings),
        ("API Connection", test_remora_connection),
        ("Data Fetch", test_vehicle_data_fetch)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results[name] = False
    
    print("\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! Remora integration should be working.")
    else:
        print("\n⚠️  Some checks failed. Please address the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()
