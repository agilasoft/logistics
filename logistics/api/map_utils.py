# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json

@frappe.whitelist(allow_guest=True)
def test_api():
	"""Test API endpoint"""
	return {
		"status": "working",
		"message": "Logistics Map Utils API is accessible"
	}

@frappe.whitelist(allow_guest=True)
def get_map_settings():
	"""Get map renderer settings from Logistics Settings"""
	try:
		# First check if Logistics Settings exists
		if not frappe.db.exists("DocType", "Logistics Settings"):
			frappe.log_error("Logistics Settings doctype does not exist", "Map Utils - Debug")
			return {
				"map_renderer": "MapLibre",
				"google_maps_api_key": "",
				"mapbox_access_token": "",
				"maplibre_style_url": "https://demotiles.maplibre.org/style.json"
			}
		
		settings = frappe.get_single("Logistics Settings")
		result = {
			"map_renderer": settings.map_renderer or "MapLibre",
			"google_maps_api_key": settings.google_maps_api_key or "",
			"mapbox_access_token": settings.mapbox_access_token or "",
			"maplibre_style_url": settings.maplibre_style_url or "https://demotiles.maplibre.org/style.json"
		}
		frappe.log_error(f"Settings retrieved: renderer={result['map_renderer']}", "Map Utils - Debug")
		return result
	except Exception as e:
		frappe.log_error(f"Error getting map settings: {str(e)}", "Map Utils - Get Settings")
		return {
			"map_renderer": "MapLibre",
			"google_maps_api_key": "",
			"mapbox_access_token": "",
			"maplibre_style_url": "https://demotiles.maplibre.org/style.json"
		}

@frappe.whitelist(allow_guest=True)
def get_location_coordinates(location_name):
	"""Get coordinates for a location"""
	if not location_name:
		return None
	
	try:
		# Check if location exists
		if not frappe.db.exists("Location", location_name):
			frappe.log_error(f"Location {location_name} does not exist", "Map Utils - Get Coordinates")
			
			# Create default coordinates for common ports
			default_coords = {
				"PHMNL": {"latitude": 14.5995, "longitude": 120.9842},  # Manila
				"HKHKG": {"latitude": 22.3193, "longitude": 114.1694},  # Hong Kong
				"USLAX": {"latitude": 33.9425, "longitude": -118.4081}, # Los Angeles
				"USNYC": {"latitude": 40.7128, "longitude": -74.0060},  # New York
				"GBLHR": {"latitude": 51.4700, "longitude": -0.4543},   # London Heathrow
			}
			
			if location_name in default_coords:
				coords = default_coords[location_name]
				return {
					"latitude": coords["latitude"],
					"longitude": coords["longitude"],
					"name": location_name,
					"address": f"Default coordinates for {location_name}"
				}
			else:
				return None
		
		location = frappe.get_doc("Location", location_name)
		frappe.log_error(f"Location {location_name} found: lat={location.latitude}, lng={location.longitude}", "Map Utils - Debug")
		
		if location and location.latitude and location.longitude:
			return {
				"latitude": float(location.latitude),
				"longitude": float(location.longitude),
				"name": location.name,
				"address": getattr(location, 'address_line_1', None) or location.name
			}
		else:
			frappe.log_error(f"Location {location_name} has no coordinates", "Map Utils - Get Coordinates")
			return None
			
	except Exception as e:
		frappe.log_error(f"Error getting coordinates for {location_name}: {str(e)}", "Map Utils - Get Coordinates")
	
	return None

@frappe.whitelist(allow_guest=True)
def get_route_coordinates(origin_location, destination_location):
	"""Get coordinates for origin and destination locations"""
	frappe.log_error(f"Getting coordinates for {origin_location} -> {destination_location}", "Map Utils - Debug")
	
	origin_coords = get_location_coordinates(origin_location)
	dest_coords = get_location_coordinates(destination_location)
	
	result = {
		"origin": origin_coords,
		"destination": dest_coords,
		"has_coordinates": bool(origin_coords and dest_coords)
	}
	
	frappe.log_error(f"Route coordinates: {origin_location}->{destination_location}, has_coords: {result['has_coordinates']}", "Map Utils - Debug")
	return result

@frappe.whitelist(allow_guest=True)
def test_coordinates(origin_location, destination_location):
	"""Test function to check coordinates"""
	origin_coords = get_location_coordinates(origin_location)
	dest_coords = get_location_coordinates(destination_location)
	return {
		"origin": origin_coords,
		"destination": dest_coords,
		"origin_valid": origin_coords and 'latitude' in origin_coords and 'longitude' in origin_coords,
		"dest_valid": dest_coords and 'latitude' in dest_coords and 'longitude' in dest_coords
	}

@frappe.whitelist(allow_guest=True)
def generate_external_map_links(origin_lat, origin_lng, dest_lat, dest_lng):
	"""Generate external map links using coordinates directly"""
	if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
		return {}
	
	try:
		# Use coordinates in URLs for better accuracy
		google_url = f"https://www.google.com/maps/dir/{origin_lat},{origin_lng}/{dest_lat},{dest_lng}"
		osm_url = f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={origin_lat},{origin_lng};{dest_lat},{dest_lng}"
		apple_url = f"http://maps.apple.com/?daddr={dest_lat},{dest_lng}&saddr={origin_lat},{origin_lng}"
		
		return {
			"google_maps": google_url,
			"openstreetmap": osm_url,
			"apple_maps": apple_url
		}
	except Exception as e:
		frappe.log_error(f"Error generating external map links: {str(e)}", "Map Utils - External Links")
		return {}

@frappe.whitelist(allow_guest=True)
def render_map_html(origin_lat, origin_lng, dest_lat, dest_lng, origin_name="", dest_name=""):
	"""Render map HTML using coordinates directly - for use by other modules"""
	if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
		return get_fallback_map_html(origin_name, dest_name)
	
	try:
		# Get map settings
		map_settings = get_map_settings()
		
		# Generate external links
		external_links = generate_external_map_links(origin_lat, origin_lng, dest_lat, dest_lng)
		
		# Create coordinates arrays for JavaScript
		origin_coords = [float(origin_lng), float(origin_lat)]
		dest_coords = [float(dest_lng), float(dest_lat)]
		
		# Generate HTML with embedded JavaScript
		html = f"""
		<div class="map-container">
			<div style="width: 100%; height: 450px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
				<div id="route-map" style="width: 100%; height: 100%;"></div>
				<div id="route-map-fallback" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
					<div style="text-align: center; color: #6c757d;">
						<i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
						<div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Route Map</div>
						<div style="font-size: 14px; margin-bottom: 15px; line-height: 1.4;">
							<strong>Origin:</strong> {origin_name or 'Unknown'}<br>
							<strong>Destination:</strong> {dest_name or 'Unknown'}
						</div>
						<div style="font-size: 12px; color: #999;">
							Loading map...
						</div>
					</div>
				</div>
			</div>
			
			<!-- External Map Links -->
			<div class="external-map-links" style="margin-top: 15px; text-align: center;">
				<div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
					<a href="{external_links.get('google_maps', '#')}" target="_blank" id="route-google-link" 
					   style="display: inline-flex; align-items: center; padding: 8px 12px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">
						<i class="fa fa-google" style="margin-right: 5px;"></i> Google Maps
					</a>
					<a href="{external_links.get('openstreetmap', '#')}" target="_blank" id="route-osm-link"
					   style="display: inline-flex; align-items: center; padding: 8px 12px; background: #7cb342; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">
						<i class="fa fa-map" style="margin-right: 5px;"></i> OpenStreetMap
					</a>
					<a href="{external_links.get('apple_maps', '#')}" target="_blank" id="route-apple-link"
					   style="display: inline-flex; align-items: center; padding: 8px 12px; background: #000; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">
						<i class="fa fa-apple" style="margin-right: 5px;"></i> Apple Maps
					</a>
				</div>
			</div>
		</div>
		
		<script>
		// Initialize map when DOM is ready
		document.addEventListener('DOMContentLoaded', function() {{
			initializeMapWithCoordinates(
				{json.dumps(origin_coords)},
				{json.dumps(dest_coords)},
				'{origin_name}',
				'{dest_name}',
				{json.dumps(map_settings)}
			);
		}});
		
		// Map initialization function
		function initializeMapWithCoordinates(originCoords, destCoords, originName, destName, mapSettings) {{
			console.log('Initializing map with coordinates:', {{ origin: originCoords, destination: destCoords }});
			
			// Initialize map based on renderer
			if (mapSettings.map_renderer && mapSettings.map_renderer.toLowerCase() === 'google maps') {{
				initializeGoogleMap('route-map', originCoords, destCoords, originName, destName);
			}} else if (mapSettings.map_renderer && mapSettings.map_renderer.toLowerCase() === 'mapbox') {{
				initializeMapboxMap('route-map', originCoords, destCoords, originName, destName);
			}} else if (mapSettings.map_renderer && mapSettings.map_renderer.toLowerCase() === 'maplibre') {{
				initializeMapLibreMap('route-map', originCoords, destCoords, originName, destName, mapSettings.maplibre_style_url);
			}} else {{
				// Default to OpenStreetMap
				initializeOpenStreetMap('route-map', originCoords, destCoords, originName, destName);
			}}
		}}
		</script>
		"""
		
		return html
		
	except Exception as e:
		frappe.log_error(f"Error rendering map HTML: {str(e)}", "Map Utils - Render HTML")
		return get_fallback_map_html(origin_name, dest_name)

def get_fallback_map_html(origin_name="", dest_name=""):
	"""Generate fallback map HTML when coordinates are not available"""
	return f"""
	<div class="map-container">
		<div style="width: 100%; height: 450px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
			<div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
				<div style="text-align: center; color: #6c757d;">
					<i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
					<div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Route Map</div>
					<div style="font-size: 14px; margin-bottom: 15px; line-height: 1.4;">
						<strong>Origin:</strong> {origin_name or 'Unknown'}<br>
						<strong>Destination:</strong> {dest_name or 'Unknown'}
					</div>
					<div style="font-size: 12px; color: #999;">
						Map coordinates not available
					</div>
				</div>
			</div>
		</div>
	</div>
	"""
