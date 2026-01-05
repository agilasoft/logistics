# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password


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
				"heading_deg": vehicle.get("last_heading_deg") if hasattr(vehicle, "last_heading_deg") else None,
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
						"heading_deg": pos.get("heading_deg"),  # Add heading for arrow direction
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
			
			# Update heading if available
			if vehicle_position.get("heading_deg") is not None:
				if hasattr(vehicle, "last_heading_deg"):
					vehicle.last_heading_deg = vehicle_position.get("heading_deg")
			
			# Save the updated vehicle document
			vehicle.save()
			
			return {
				"success": True,
				"vehicle_name": vehicle_name,
				"latitude": vehicle_position.get("latitude"),
				"longitude": vehicle_position.get("longitude"),
				"timestamp": vehicle_position.get("timestamp"),
				"speed_kph": vehicle_position.get("speed_kph"),
				"heading_deg": vehicle_position.get("heading_deg"),
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


@frappe.whitelist()
def get_google_maps_api_key():
	"""
	Get the Google Maps API key for client-side use.
	This properly decrypts the Password field.
	
	Returns:
		dict: {
			"api_key": str or None,
			"has_key": bool
		}
	"""
	try:
		# Get the API key using get_decrypted_password for Password fields
		# For Single doctypes, both doctype and name are the same
		api_key = get_decrypted_password(
			"Transport Settings",
			"Transport Settings",
			"routing_google_api_key",
			raise_exception=False
		)
		
		# Also try alternative field names (for compatibility)
		if not api_key:
			for field_name in ["google_api_key", "google_maps_api_key", "maps_api_key"]:
				api_key = get_decrypted_password(
					"Transport Settings",
					"Transport Settings",
					field_name,
					raise_exception=False
				)
				if api_key:
					break
		
		if api_key and len(api_key) > 10:
			return {
				"api_key": api_key,
				"has_key": True
			}
		else:
			return {
				"api_key": None,
				"has_key": False
			}
	except Exception as e:
		frappe.log_error(f"Error getting Google Maps API key: {str(e)}", "Vehicle Tracking")
		return {
			"api_key": None,
			"has_key": False,
			"error": str(e)
		}


@frappe.whitelist()
def save_selected_route(run_sheet_name=None, transport_leg_name=None, route_index=None, polyline=None, distance_km=None, duration_min=None, route_type="run_sheet"):
	"""
	Save the selected route polyline, distance, and duration to Run Sheet or Transport Leg document.
	
	Args:
		run_sheet_name: Name of the Run Sheet document (for combined route)
		transport_leg_name: Name of the Transport Leg document (for individual leg route)
		route_index: Index of the selected route (0-based)
		polyline: Encoded polyline string of the selected route
		distance_km: Distance in kilometers for the selected route
		duration_min: Duration in minutes for the selected route
		route_type: "run_sheet" or "transport_leg" - indicates which document to save to
	
	Returns:
		dict: {"success": bool}
	"""
	try:
		if route_type == "run_sheet" and run_sheet_name:
			run_sheet = frappe.get_doc("Run Sheet", run_sheet_name)
			
			# Store route in Run Sheet fields
			if hasattr(run_sheet, "selected_route_polyline"):
				run_sheet.selected_route_polyline = polyline
			if hasattr(run_sheet, "selected_route_index"):
				run_sheet.selected_route_index = route_index
			
			# Update total distance and duration for the entire run sheet route
			# Calculate total from all legs if distance/duration provided
			if distance_km is not None and duration_min is not None:
				# For Run Sheet, we could store total route distance/duration
				# But typically Run Sheet doesn't have these fields - they're per leg
				# So we'll update the estimated completion time if that field exists
				if hasattr(run_sheet, "estimated_completion_time") and run_sheet.run_date:
					try:
						from frappe.utils import add_to_date, get_datetime
						start_time = get_datetime(run_sheet.run_date)
						estimated_end = add_to_date(start_time, minutes=int(duration_min))
						run_sheet.estimated_completion_time = estimated_end
					except Exception:
						pass
			
			run_sheet.save(ignore_permissions=True)
			
			# Sync: Clear individual leg routes when Run Sheet route changes
			# This ensures leg routes can be recalculated if needed
			for leg_row in run_sheet.legs:
				if leg_row.transport_leg:
					try:
						leg_doc = frappe.get_doc("Transport Leg", leg_row.transport_leg)
						# Clear leg route so it can be recalculated
						if hasattr(leg_doc, "selected_route_polyline"):
							leg_doc.selected_route_polyline = None
						if hasattr(leg_doc, "selected_route_index"):
							leg_doc.selected_route_index = None
						leg_doc.save(ignore_permissions=True)
					except Exception as e:
						frappe.log_error(f"Error clearing leg route {leg_row.transport_leg}: {str(e)}")
			
			return {"success": True}
		
		elif route_type == "transport_leg" and transport_leg_name:
			transport_leg = frappe.get_doc("Transport Leg", transport_leg_name)
			
			# Store route in Transport Leg fields
			if hasattr(transport_leg, "selected_route_polyline"):
				transport_leg.selected_route_polyline = polyline
			if hasattr(transport_leg, "selected_route_index"):
				transport_leg.selected_route_index = route_index
			
			# Update distance and duration from the selected route
			if distance_km is not None:
				# Try route_distance_km first, then distance_km
				if hasattr(transport_leg, "route_distance_km"):
					transport_leg.route_distance_km = round(float(distance_km), 3)
				elif hasattr(transport_leg, "distance_km"):
					transport_leg.distance_km = round(float(distance_km), 3)
			
			if duration_min is not None:
				# Try route_duration_min first, then duration_min
				if hasattr(transport_leg, "route_duration_min"):
					transport_leg.route_duration_min = round(float(duration_min), 1)
				elif hasattr(transport_leg, "duration_min"):
					transport_leg.duration_min = round(float(duration_min), 1)
			
			transport_leg.save(ignore_permissions=True)
			
			# Sync: Clear Run Sheet route when leg route changes
			# This ensures Run Sheet route gets recalculated with updated leg routes
			if transport_leg.run_sheet:
				try:
					run_sheet = frappe.get_doc("Run Sheet", transport_leg.run_sheet)
					if hasattr(run_sheet, "selected_route_polyline"):
						run_sheet.selected_route_polyline = None
					if hasattr(run_sheet, "selected_route_index"):
						run_sheet.selected_route_index = None
					run_sheet.save(ignore_permissions=True)
				except Exception as e:
					frappe.log_error(f"Error clearing Run Sheet route {transport_leg.run_sheet}: {str(e)}")
			
			return {"success": True}
		else:
			return {
				"success": False,
				"error": "Invalid parameters: provide either run_sheet_name or transport_leg_name"
			}
	except Exception as e:
		frappe.log_error(f"Error saving selected route: {str(e)}", "Vehicle Tracking")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_google_route_polyline(waypoints):
	"""
	Get Google Directions API route polyline for waypoints.
	This returns an encoded polyline that can be used in Static Maps API.
	
	Args:
		waypoints: List of [lat, lon] coordinates or string of "lat,lon|lat,lon|..."
	
	Returns:
		dict: {
			"polyline": str (encoded polyline),
			"success": bool
		}
	"""
	try:
		import requests
		
		# Get API key
		api_key = get_decrypted_password(
			"Transport Settings",
			"Transport Settings",
			"routing_google_api_key",
			raise_exception=False
		)
		
		if not api_key or len(api_key) < 10:
			return {
				"success": False,
				"error": "Google Maps API key not configured"
			}
		
		# Parse waypoints
		if isinstance(waypoints, str):
			# Format: "lat,lon|lat,lon|..."
			points = waypoints.split('|')
		elif isinstance(waypoints, list):
			# Format: [["lat", "lon"], ...] or [{"lat": x, "lon": y}, ...]
			if len(waypoints) == 0:
				return {"success": False, "error": "No waypoints provided"}
			
			# Convert to string format
			points = []
			for wp in waypoints:
				if isinstance(wp, dict):
					points.append(f"{wp.get('lat')},{wp.get('lon')}")
				elif isinstance(wp, list):
					points.append(f"{wp[0]},{wp[1]}")
				else:
					points.append(str(wp))
		else:
			return {"success": False, "error": "Invalid waypoints format"}
		
		if len(points) < 2:
			return {"success": False, "error": "Need at least 2 waypoints"}
		
		# Build Directions API URL
		origin = points[0]
		destination = points[-1]
		waypoint_str = '|'.join(points[1:-1]) if len(points) > 2 else ''
		
		url = "https://maps.googleapis.com/maps/api/directions/json"
		params = {
			"origin": origin,
			"destination": destination,
			"mode": "driving",
			"units": "metric",
			"alternatives": "true",  # Request alternate routes
			"key": api_key
		}
		
		if waypoint_str:
			params["waypoints"] = waypoint_str
		
		# Call Directions API
		response = requests.get(url, params=params, timeout=10)
		data = response.json()
		
		if data.get("status") != "OK":
			error_msg = data.get("error_message", data.get("status", "Unknown error"))
			return {
				"success": False,
				"error": f"Google Directions API error: {error_msg}"
			}
		
		routes = data.get("routes", [])
		if not routes:
			return {"success": False, "error": "No routes returned"}
		
		# Extract all routes with their details
		route_options = []
		for idx, route in enumerate(routes):
			overview_polyline = route.get("overview_polyline", {})
			encoded_polyline = overview_polyline.get("points", "")
			
			if encoded_polyline:
				# Get route summary (distance and duration)
				legs = route.get("legs", [])
				total_distance = sum(leg.get("distance", {}).get("value", 0) for leg in legs) / 1000.0  # Convert to km
				total_duration = sum(leg.get("duration", {}).get("value", 0) for leg in legs) / 60.0  # Convert to minutes
				
				route_options.append({
					"index": idx,
					"polyline": encoded_polyline,
					"distance_km": round(total_distance, 2),
					"duration_min": round(total_duration, 1),
					"summary": route.get("summary", f"Route {idx + 1}")
				})
		
		if not route_options:
			return {"success": False, "error": "No valid polylines in routes"}
		
		return {
			"success": True,
			"routes": route_options,
			"polyline": route_options[0]["polyline"]  # Default to first route for backward compatibility
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting Google route polyline: {str(e)}", "Vehicle Tracking")
		return {
			"success": False,
			"error": str(e)
		}
