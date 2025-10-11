# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_vehicle_position(vehicle_name):
	"""Get the latest position of a vehicle from telematics"""
	try:
		vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
		
		if not vehicle.telematics_external_id or not vehicle.telematics_provider:
			return {
				"success": False,
				"error": "Vehicle does not have telematics configured"
			}
		
		# Try to get latest position from saved data first
		if vehicle.last_telematics_lat and vehicle.last_telematics_lon:
			return {
				"success": True,
				"vehicle_name": vehicle_name,
				"latitude": vehicle.last_telematics_lat,
				"longitude": vehicle.last_telematics_lon,
				"timestamp": vehicle.last_telematics_ts,
				"speed_kph": vehicle.last_speed_kph,
				"ignition": vehicle.last_ignition_on,
				"fuel_level": vehicle.get("last_fuel_level") if hasattr(vehicle, "last_fuel_level") else None,
				"odometer_km": vehicle.last_odometer_km,
				"provider": vehicle.last_provider
			}
		
		# If no saved position, try to fetch from provider
		try:
			from logistics.transport.telematics.resolve import _provider_conf
			from logistics.transport.telematics.providers import make_provider
			
			conf = _provider_conf(vehicle.telematics_provider)
			if not conf:
				return {
					"success": False,
					"error": "Telematics provider not configured or disabled"
				}
			
			provider = make_provider(conf["provider_type"], conf)
			positions = list(provider.fetch_latest_positions())
			
			# Find position for this vehicle
			for pos in positions:
				pos_external_id = pos.get("external_id") or pos.get("device_id")
				if str(pos_external_id) == str(vehicle.telematics_external_id):
					return {
						"success": True,
						"vehicle_name": vehicle_name,
						"latitude": pos.get("latitude"),
						"longitude": pos.get("longitude"),
						"timestamp": pos.get("timestamp"),
						"speed_kph": pos.get("speed_kph"),
						"ignition": pos.get("ignition"),
						"fuel_level": pos.get("fuel_l"),  # Add fuel level from position data
						"odometer_km": pos.get("odometer_km"),  # Add mileage/odometer data
						"provider": vehicle.telematics_provider
					}
			
			return {
				"success": False,
				"error": f"No position data found for vehicle {vehicle_name}"
			}
			
		except Exception as e:
			frappe.log_error(f"Error fetching vehicle position: {str(e)}", "Vehicle Tracking")
			return {
				"success": False,
				"error": str(e)
			}
		
	except Exception as e:
		frappe.log_error(f"Error in get_vehicle_position: {str(e)}", "Vehicle Tracking")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_run_sheet_vehicle_positions(run_sheet_name):
	"""Get positions for all vehicles in a run sheet"""
	try:
		run_sheet = frappe.get_doc("Run Sheet", run_sheet_name)
		
		vehicle_positions = []
		
		# Get main vehicle position
		if run_sheet.vehicle:
			pos = get_vehicle_position(run_sheet.vehicle)
			if pos.get("success"):
				vehicle_positions.append(pos)
		
		# You could also get positions for vehicles assigned to individual legs if needed
		# For now, we'll just track the main run sheet vehicle
		
		return {
			"success": True,
			"run_sheet": run_sheet_name,
			"vehicle_positions": vehicle_positions
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_run_sheet_vehicle_positions: {str(e)}", "Vehicle Tracking")
		return {
			"success": False,
			"error": str(e),
			"vehicle_positions": []
		}


@frappe.whitelist()
def refresh_vehicle_data(vehicle_name):
	"""Refresh vehicle telematics data and return updated position and status"""
	try:
		vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
		
		if not vehicle.telematics_external_id or not vehicle.telematics_provider:
			return {
				"success": False,
				"error": "Vehicle does not have telematics configured"
			}
		
		# Force refresh from telematics provider
		try:
			from logistics.transport.telematics.resolve import _provider_conf
			from logistics.transport.telematics.providers import make_provider
			
			conf = _provider_conf(vehicle.telematics_provider)
			if not conf:
				return {
					"success": False,
					"error": "Telematics provider not configured or disabled"
				}
			
			provider = make_provider(conf["provider_type"], conf)
			
			# Fetch latest positions and CAN data
			positions = list(provider.fetch_latest_positions())
			can_data = list(provider.fetch_latest_can_data()) if hasattr(provider, 'fetch_latest_can_data') else []
			
			# Find position for this vehicle
			vehicle_position = None
			vehicle_can_data = None
			
			for pos in positions:
				pos_external_id = pos.get("external_id") or pos.get("device_id")
				if str(pos_external_id) == str(vehicle.telematics_external_id):
					vehicle_position = pos
					break
			
			# Find CAN data for this vehicle
			for can in can_data:
				can_external_id = can.get("device_id")
				if str(can_external_id) == str(vehicle.telematics_external_id):
					vehicle_can_data = can
					break
			
			if not vehicle_position:
				return {
					"success": False,
					"error": f"No fresh position data found for vehicle {vehicle_name}"
				}
			
			# Update vehicle document with fresh data
			vehicle.last_telematics_lat = vehicle_position.get("latitude")
			vehicle.last_telematics_lon = vehicle_position.get("longitude")
			
			# Handle timestamp conversion - convert ISO format to MySQL datetime
			timestamp = vehicle_position.get("timestamp")
			if timestamp:
				try:
					# Use Frappe's datetime utilities for proper timezone handling
					from dateutil import parser
					
					# Parse the ISO timestamp
					dt = parser.parse(timestamp)
					
					# Convert to system timezone using Frappe's utilities
					if dt.tzinfo is not None:
						# Convert to system timezone
						dt = dt.astimezone()
					
					# Convert to MySQL datetime format (YYYY-MM-DD HH:MM:SS)
					vehicle.last_telematics_ts = dt.strftime('%Y-%m-%d %H:%M:%S')
					
					frappe.logger().info(f"Converted timestamp '{timestamp}' to '{vehicle.last_telematics_ts}'")
				except Exception as e:
					frappe.logger().warning(f"Could not parse timestamp '{timestamp}': {str(e)}")
					# Fallback to current time in system timezone
					vehicle.last_telematics_ts = frappe.utils.now()
			else:
				vehicle.last_telematics_ts = frappe.utils.now()
			
			vehicle.last_speed_kph = vehicle_position.get("speed_kph")
			
			# Handle ignition - convert string to boolean
			ignition = vehicle_position.get("ignition")
			if ignition:
				ignition_str = str(ignition).upper()
				vehicle.last_ignition_on = ignition_str not in ['OFF', 'FALSE', '0', 'NONE', '']
			else:
				vehicle.last_ignition_on = False
			
			vehicle.last_odometer_km = vehicle_position.get("odometer_km")
			
			# Handle fuel level - try CAN data first, then position data
			fuel_l = None
			if vehicle_can_data:
				fuel_l = vehicle_can_data.get("fuel_l")
				frappe.logger().info(f"Fuel level from CAN data: {fuel_l}")
			
			# Fallback to position data if CAN data not available
			if fuel_l is None:
				fuel_l = vehicle_position.get("fuel_l")
				frappe.logger().info(f"Fuel level from position data: {fuel_l}")
			
			if fuel_l is not None:
				vehicle.last_fuel_level = float(fuel_l)
			else:
				vehicle.last_fuel_level = None
			
			vehicle.last_provider = vehicle.telematics_provider
			
			# Save the updated vehicle document
			vehicle.save()
			
			return {
				"success": True,
				"vehicle_name": vehicle_name,
				"latitude": vehicle_position.get("latitude"),
				"longitude": vehicle_position.get("longitude"),
				"timestamp": vehicle_position.get("timestamp"),
				"speed_kph": vehicle_position.get("speed_kph"),
				"ignition": vehicle.last_ignition_on,
				"fuel_level": vehicle.last_fuel_level,
				"odometer_km": vehicle.last_odometer_km,
				"provider": vehicle.telematics_provider,
				"message": "Vehicle data refreshed successfully"
			}
			
		except Exception as e:
			frappe.log_error(f"Error refreshing vehicle data: {str(e)}", "Vehicle Tracking")
			return {
				"success": False,
				"error": f"Failed to refresh from telematics provider: {str(e)}"
			}
		
	except Exception as e:
		frappe.log_error(f"Error in refresh_vehicle_data: {str(e)}", "Vehicle Tracking")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_all_vehicles_with_status():
	"""Get all vehicles with their locations and run sheet status for dashboard map"""
	try:
		# Get all vehicles with their basic info
		vehicles = frappe.get_all(
			"Transport Vehicle",
			fields=[
				"name", "code", "vehicle_name", "vehicle_type", "transport_company",
				"last_telematics_lat", "last_telematics_lon", "last_telematics_ts",
				"last_speed_kph", "last_ignition_on", "last_fuel_level", "last_provider"
			],
			limit=500
		)
		
		# Get active run sheets to determine vehicle status
		active_run_sheets = frappe.get_all(
			"Run Sheet",
			filters={"status": ["in", ["Active", "In Progress", "Scheduled", "Draft"]]},
			fields=["name", "vehicle", "status", "run_date", "driver_name"],
			limit=1000
		)
		
		# Create a mapping of vehicle to run sheet
		vehicle_run_sheet_map = {}
		for rs in active_run_sheets:
			if rs.vehicle:
				vehicle_run_sheet_map[rs.vehicle] = {
					"run_sheet": rs.name,
					"status": rs.status,
					"run_date": rs.run_date,
					"driver_name": rs.driver_name
				}
		
		# Process each vehicle
		vehicle_data = []
		for vehicle in vehicles:
			# Determine status
			if vehicle.name in vehicle_run_sheet_map:
				rs_info = vehicle_run_sheet_map[vehicle.name]
				status = "assigned"
				run_sheet_info = rs_info
			else:
				status = "available"
				run_sheet_info = None
			
			# Only include vehicles with location data
			if vehicle.last_telematics_lat and vehicle.last_telematics_lon:
				vehicle_info = {
					"vehicle_name": vehicle.name,
					"code": vehicle.code,
					"display_name": vehicle.vehicle_name or vehicle.code or vehicle.name,
					"vehicle_type": vehicle.vehicle_type,
					"transport_company": vehicle.transport_company,
					"latitude": vehicle.last_telematics_lat,
					"longitude": vehicle.last_telematics_lon,
					"timestamp": vehicle.last_telematics_ts,
					"speed_kph": vehicle.last_speed_kph,
					"ignition": vehicle.last_ignition_on,
					"fuel_level": vehicle.last_fuel_level,
					"provider": vehicle.last_provider,
					"status": status,
					"run_sheet_info": run_sheet_info
				}
				vehicle_data.append(vehicle_info)
		
		return {
			"success": True,
			"vehicles": vehicle_data,
			"total_vehicles": len(vehicles),
			"tracked_vehicles": len(vehicle_data)
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_all_vehicles_with_status: {str(e)}", "Vehicle Tracking")
		return {
			"success": False,
			"error": str(e),
			"vehicles": []
		}
