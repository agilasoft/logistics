# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class AirShipment(Document):
	@frappe.whitelist()
	def get_milestone_html(self):
		"""Generate HTML for milestone visualization with map and cards"""
		try:
			if not self.origin_port or not self.destination_port:
				return "<div class='alert alert-info'>Origin and Destination ports are required to display the milestone view.</div>"
			
			# Get milestone data
			milestones = frappe.get_all(
				"Job Milestone",
				filters={
					"job_type": "Air Shipment",
					"job_number": self.name
				},
				fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
				order_by="planned_start"
			)
			
			# Get milestone details
			milestone_details = {}
			if milestones:
				milestone_names = [m.milestone for m in milestones if m.milestone]
				if milestone_names:
					milestone_data = frappe.get_all(
						"Logistics Milestone",
						filters={"name": ["in", milestone_names]},
						fields=["name", "description", "code"]
					)
					milestone_details = {m.name: m for m in milestone_data}
			
			# Build header with job details
			incoterm = getattr(self, 'incoterm', None) or 'Not specified'
			
			# Get shipper details
			shipper_code = ''
			shipper_name = 'Not specified'
			shipper_address = ''
			shipper = getattr(self, 'shipper', None)
			if shipper:
				try:
					# Try to get as Shipper doctype first
					if frappe.db.exists('Shipper', shipper):
						shipper_doc = frappe.get_doc('Shipper', shipper)
						shipper_code = getattr(shipper_doc, 'shipper_code', None) or getattr(shipper_doc, 'code', None) or ''
						shipper_name = getattr(shipper_doc, 'shipper_name', None) or getattr(shipper_doc, 'name', None) or shipper
						shipper_addr = getattr(shipper_doc, 'address', None)
						if shipper_addr:
							shipper_address = shipper_addr
					else:
						# Fallback: just use the value as name
						shipper_name = shipper
						
					# Get address if linked separately
					shipper_addr_field = getattr(self, 'shipper_address', None)
					if shipper_addr_field:
						try:
							addr_doc = frappe.get_doc('Address', shipper_addr_field)
							addr_line1 = getattr(addr_doc, 'address_line1', None) or ''
							city = getattr(addr_doc, 'city', None) or ''
							shipper_address = f"{addr_line1}, {city}".strip(', ')
						except:
							pass
				except:
					shipper_name = shipper
			
			# Get consignee details
			consignee_code = ''
			consignee_name = 'Not specified'
			consignee_address = ''
			consignee = getattr(self, 'consignee', None)
			if consignee:
				try:
					# Try to get as Consignee doctype first
					if frappe.db.exists('Consignee', consignee):
						consignee_doc = frappe.get_doc('Consignee', consignee)
						consignee_code = getattr(consignee_doc, 'consignee_code', None) or getattr(consignee_doc, 'code', None) or ''
						consignee_name = getattr(consignee_doc, 'consignee_name', None) or getattr(consignee_doc, 'name', None) or consignee
						consignee_addr = getattr(consignee_doc, 'address', None)
						if consignee_addr:
							consignee_address = consignee_addr
					else:
						# Fallback: just use the value as name
						consignee_name = consignee
						
					# Get address if linked separately
					consignee_addr_field = getattr(self, 'consignee_address', None)
					if consignee_addr_field:
						try:
							addr_doc = frappe.get_doc('Address', consignee_addr_field)
							addr_line1 = getattr(addr_doc, 'address_line1', None) or ''
							city = getattr(addr_doc, 'city', None) or ''
							consignee_address = f"{addr_line1}, {city}".strip(', ')
						except:
							pass
				except:
					consignee_name = consignee
			
			# Get flight details from Master Airway Bill if linked
			airline = 'Not specified'
			flight_number = 'Not specified'
			mawb = getattr(self, 'master_airway_bill', None)
			if mawb:
				try:
					mawb_doc = frappe.get_doc('Master Airway Bill', mawb)
					airline = getattr(mawb_doc, 'airline', None) or 'Not specified'
					flight_number = getattr(mawb_doc, 'flight_number', None) or 'Not specified'
				except:
					pass
			
			html = f"""
		<div class="job-header">
			<div class="header-main">
				<div class="header-column">
					<div class="header-section">
						<label class="section-label">ORIGIN</label>
						<div class="location-name">{self.origin_port or 'Origin'}</div>
					</div>
					<div class="party-info">
						<div class="party-label">Shipper:</div>
						{'<div class="party-code">' + shipper_code + '</div>' if shipper_code else ''}
						<div class="party-name">{shipper_name}</div>
						{'<div class="party-address">' + shipper_address + '</div>' if shipper_address else ''}
					</div>
				</div>
				
				<div class="header-column">
					<div class="header-section">
						<label class="section-label">DESTINATION</label>
						<div class="location-name">{self.destination_port or 'Destination'}</div>
					</div>
					<div class="party-info">
						<div class="party-label">Consignee:</div>
						{'<div class="party-code">' + consignee_code + '</div>' if consignee_code else ''}
						<div class="party-name">{consignee_name}</div>
						{'<div class="party-address">' + consignee_address + '</div>' if consignee_address else ''}
					</div>
				</div>
			</div>
			
			<div class="header-details">
				<div class="detail-item">
					<label>Airline:</label>
					<span>{airline}</span>
				</div>
				<div class="detail-item">
					<label>Flight:</label>
					<span>{flight_number}</span>
				</div>
				<div class="detail-item">
					<label>Incoterm:</label>
					<span>{incoterm}</span>
				</div>
				{self.get_dg_compliance_badge()}
			</div>
		</div>
		
		<div class="milestone-container">
			<div class="milestone-cards">
				<div class="milestone-list">
		"""
		
			for milestone in milestones:
				milestone_info = milestone_details.get(milestone.milestone, {})
				
				# Get base status
				status = milestone.status or 'Planned'
				status_class = status.lower().replace(' ', '-')
				
				# Check if milestone is delayed - either:
				# 1. No actual end yet and planned end has passed, OR
				# 2. Has actual end but actual end is after planned end (completed late)
				if (milestone.planned_end and 
					((not milestone.actual_end and milestone.planned_end < frappe.utils.now_datetime()) or
					 (milestone.actual_end and milestone.actual_end > milestone.planned_end))):
					
					# If it's not completed yet and delayed, show delayed status
					if not milestone.actual_end or milestone.actual_end <= milestone.planned_end:
						status = 'Delayed'
						status_class = 'delayed'
				
				# Determine status badges to display
				status_badges = []
				original_status = milestone.status or 'Planned'
				
				if (milestone.actual_end and milestone.actual_end > milestone.planned_end and 
					original_status.lower() in ['completed', 'finished', 'done']):
					# Show both completed and delayed badges
					status_badges = [
						'<span class="status-badge completed">Completed</span>',
						'<span class="status-badge delayed">Delayed</span>'
					]
				else:
					# Show single status badge
					status_badges = [f'<span class="status-badge {status_class}">{status}</span>']
				
				# Build action icons - show only if dates are not present
				action_icons = []
				if not milestone.actual_start:
					action_icons.append(f'''<i class="fa fa-play-circle action-icon start-icon" 
					   title="Capture Actual Start" 
					   onclick="captureActualStart('{milestone.name}')"
					   style="color: #28a745; cursor: pointer;"></i>''')
				if not milestone.actual_end:
					action_icons.append(f'''<i class="fa fa-stop-circle action-icon end-icon" 
					   title="Capture Actual End" 
					   onclick="captureActualEnd('{milestone.name}')"
					   style="color: #dc3545; cursor: pointer;"></i>''')
				# Always show view icon
				action_icons.append(f'''<i class="fa fa-eye action-icon view-icon" 
				   title="View Milestone" 
				   onclick="viewMilestone('{milestone.name}')"
				   style="color: #007bff; cursor: pointer;"></i>''')
				
				html += f"""
						<div class="milestone-card {status_class}">
							<div class="milestone-header">
								<h5>{milestone_info.get('description', milestone.milestone or 'Unknown')}</h5>
								<div class="milestone-actions">
									<div class="status-badges">
										{''.join(status_badges)}
									</div>
									<div class="action-icons">
										{''.join(action_icons)}
									</div>
								</div>
							</div>
							<div class="milestone-dates">
								<div class="date-row">
									<label>Planned:</label>
									<span>{self.format_datetime(milestone.planned_end) or 'Not set'}</span>
								</div>
								<div class="date-row">
									<label>Actual:</label>
									<span>{self.format_datetime(milestone.actual_end) or 'Not completed'}</span>
								</div>
							</div>
						</div>
				"""
			
			# Build the final HTML with proper string formatting
			origin_port = self.origin_port or 'Not specified'
			dest_port = self.destination_port or 'Not specified'
			
			html += f"""
				</div>
			</div>
			<div class="map-container">
				<div style="width: 100%; height: 450px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
					<div id="route-map" style="width: 100%; height: 100%;"></div>
					<div id="route-map-fallback" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
						<div style="text-align: center; color: #6c757d;">
							<i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
							<div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Route Map</div>
							<div style="font-size: 14px; margin-bottom: 15px; line-height: 1.4;">
								<strong>Origin:</strong> {origin_port}<br>
								<strong>Destination:</strong> {dest_port}
							</div>
							<div style="font-size: 12px; color: #999;">
								Loading map...
							</div>
						</div>
					</div>
				</div>
				<div class="text-muted small" style="margin-top: 10px; display: flex; gap: 20px; align-items: center; justify-content: center;">
					<a href="#" id="route-google-link" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
						<i class="fa fa-external-link"></i> Google Maps
					</a>
					<a href="#" id="route-osm-link" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
						<i class="fa fa-external-link"></i> OpenStreetMap
					</a>
					<a href="#" id="route-apple-link" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
						<i class="fa fa-external-link"></i> Apple Maps
					</a>
				</div>
			</div>
		</div>
		
		<style>
		.job-header {{
			background: #ffffff;
			border: 1px solid #e0e0e0;
			border-radius: 6px;
			margin-bottom: 20px;
			padding: 12px 16px;
		}}
		
		.header-main {{
			display: flex;
			justify-content: space-between;
			padding-bottom: 10px;
			border-bottom: 1px solid #e0e0e0;
			gap: 40px;
		}}
		
		.header-column {{
			flex: 1;
			display: flex;
			flex-direction: column;
			gap: 5px;
		}}
		
		.header-section {{
			display: flex;
			flex-direction: column;
			gap: 0px;
		}}
		
		.party-info {{
			margin-top: 5px;
			display: flex;
			flex-direction: column;
		}}
		
		.party-label {{
			font-size: 10px;
			color: #6c757d;
			font-weight: 600;
			margin-bottom: -2px;
		}}
		
		.party-code {{
			font-size: 10px;
			color: #2c3e50;
			font-weight: 600;
			margin-top: -1px;
			margin-bottom: -2px;
		}}
		
		.party-name {{
			font-size: 11px;
			color: #2c3e50;
			font-weight: 500;
			margin-top: -1px;
			margin-bottom: -2px;
		}}
		
		.party-address {{
			font-size: 10px;
			color: #6c757d;
			font-weight: 400;
			margin-top: -1px;
		}}
		
		.section-label {{
			font-size: 10px;
			color: #6c757d;
			text-transform: uppercase;
			font-weight: 600;
			letter-spacing: 0.5px;
			margin-bottom: -2px;
		}}
		
		.location-name {{
			font-size: 18px;
			font-weight: 700;
			color: #007bff;
			margin-top: -2px;
		}}
		
		.header-details {{
			padding-top: 10px;
			background: #ffffff;
			display: flex;
			gap: 15px;
			flex-wrap: wrap;
		}}
		
		.detail-item {{
			display: flex;
			align-items: baseline;
			gap: 5px;
		}}
		
		.detail-item label {{
			font-size: 10px;
			color: #6c757d;
			font-weight: 600;
		}}
		
		.detail-item span {{
			font-size: 12px;
			color: #2c3e50;
			font-weight: 400;
		}}
		
		.dg-compliance-badge {{
			margin-left: auto;
		}}
		
		.dg-badge {{
			display: inline-flex;
			align-items: center;
			gap: 4px;
			padding: 4px 8px;
			border-radius: 12px;
			font-size: 10px;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 0.5px;
		}}
		
		.dg-badge-compliant {{
			background: #d4edda;
			color: #155724;
			border: 1px solid #c3e6cb;
		}}
		
		.dg-badge-non-compliant {{
			background: #f8d7da;
			color: #721c24;
			border: 1px solid #f5c6cb;
		}}
		
		.dg-badge-unknown {{
			background: #e2e3e5;
			color: #6c757d;
			border: 1px solid #d6d8db;
		}}
		
		.dg-badge i {{
			font-size: 10px;
		}}
		
		.milestone-container {{
			display: flex;
			gap: 20px;
			margin: 20px 0;
			align-items: flex-start;
		}}
		
		.milestone-cards {{
			flex: 1;
			max-width: 300px;
		}}
		
		.map-container {{
			flex: 2;
			align-self: flex-start;
			position: relative;
			z-index: 1;
		}}
		
		.milestone-list {{
			display: flex;
			flex-direction: column;
			gap: 8px;
		}}
		
		.milestone-card {{
			background: white;
			border: 1px solid #e0e0e0;
			border-radius: 6px;
			padding: 12px;
			box-shadow: 0 1px 3px rgba(0,0,0,0.1);
			transition: all 0.3s ease;
		}}
		
		.milestone-card:hover {{
			box-shadow: 0 4px 8px rgba(0,0,0,0.15);
		}}
		
		.milestone-card.completed {{
			border-left: 4px solid #28a745;
		}}
		
		.milestone-card.delayed {{
			border-left: 4px solid #dc3545;
		}}
		
		.milestone-card.planned {{
			border-left: 4px solid #6c757d;
		}}
		
		.milestone-card.started {{
			border-left: 4px solid #007bff;
		}}
		
		.milestone-header {{
			display: flex;
			justify-content: space-between;
			align-items: flex-start;
			margin-bottom: 8px;
		}}
		
		.milestone-header h5 {{
			margin: 0;
			font-size: 14px;
			font-weight: 600;
			color: #333;
			line-height: 1.2;
		}}
		
		.milestone-actions {{
			display: flex;
			flex-direction: row;
			align-items: center;
			gap: 8px;
		}}
		
		.status-badges {{
			display: flex;
			gap: 5px;
			flex-wrap: wrap;
		}}
		
		.status-badge {{
			padding: 2px 6px;
			border-radius: 10px;
			font-size: 10px;
			font-weight: 500;
			text-transform: uppercase;
		}}
		
		.status-badge.completed {{
			background: #d4edda;
			color: #155724;
		}}
		
		.status-badge.delayed {{
			background: #f8d7da;
			color: #721c24;
		}}
		
		.status-badge.planned {{
			background: #e2e3e5;
			color: #6c757d;
		}}
		
		.status-badge.started {{
			background: #cfe2ff;
			color: #084298;
		}}
		
		.action-icons {{
			display: flex;
			gap: 6px;
		}}
		
		.action-icon {{
			font-size: 14px;
			cursor: pointer;
			transition: opacity 0.2s ease;
		}}
		
		.action-icon:hover {{
			opacity: 0.7;
		}}
		
		.milestone-dates {{
			display: flex;
			flex-direction: row;
			justify-content: space-between;
			gap: 8px;
		}}
		
		.date-row {{
			display: flex;
			flex-direction: column;
			align-items: flex-start;
			gap: 0px;
		}}
		
		.date-row label {{
			font-size: 10px;
			color: #6c757d;
			font-weight: 500;
			margin-bottom: -2px;
		}}
		
		.date-row span {{
			font-size: 10px;
			color: #333;
			margin-top: -2px;
		}}
		
		@media (max-width: 768px) {{
			.milestone-container {{
				flex-direction: column;
			}}
			
			.milestone-cards {{
				max-width: none;
			}}
			
			.map-container {{
				position: relative;
				top: auto;
				max-height: none;
			}}
		}}
		</style>
		
		<script>
		// Initialize embedded map when document is ready
		$(document).ready(function() {{
			// Add a small delay to ensure DOM is fully rendered
			setTimeout(function() {{
				initializeAirFreightMap();
			}}, 100);
		}});
		
		async function initializeAirFreightMap() {{
			console.log('Initializing Air Freight Map...');
			const originPort = '{self.origin_port or ""}';
			const destPort = '{self.destination_port or ""}';
			console.log('Origin Port:', originPort);
			console.log('Destination Port:', destPort);
			
			if (!originPort && !destPort) {{
				console.log('No ports specified, showing fallback');
				showMapFallback('route-map', originPort, destPort);
				return;
			}}
			
			try {{
				// Get map renderer from Logistics Settings
				let mapRenderer = 'MapLibre'; // Default
				try {{
					if (typeof frappe !== 'undefined' && frappe.get_single) {{
						const settings = frappe.get_single('Logistics Settings');
						mapRenderer = settings.map_renderer || 'MapLibre';
						console.log('Map renderer from settings:', mapRenderer);
					}} else {{
						console.log('Frappe not available, using default MapLibre');
					}}
				}} catch (e) {{
					console.log('Could not get map renderer from settings, using default:', e);
				}}
				
				// Get coordinates for ports
				const originCoords = await getPortCoordinates(originPort);
				const destCoords = await getPortCoordinates(destPort);
				
				if (!originCoords || !destCoords) {{
					console.log('Coordinates not available, showing fallback');
					showMapFallback('route-map', originPort, destPort);
					return;
				}}
				
				console.log('Coordinates found:', {{ origin: originCoords, destination: destCoords }});
				
				// Initialize map based on renderer
				if (mapRenderer.toLowerCase() === 'google maps') {{
					initializeGoogleMap('route-map', originCoords, destCoords, originPort, destPort);
				}} else if (mapRenderer.toLowerCase() === 'mapbox') {{
					initializeMapboxMap('route-map', originCoords, destCoords, originPort, destPort);
				}} else if (mapRenderer.toLowerCase() === 'maplibre') {{
					initializeMapLibreMap('route-map', originCoords, destCoords, originPort, destPort);
				}} else {{
					// Default to OpenStreetMap
					initializeOpenStreetMap('route-map', originCoords, destCoords, originPort, destPort);
				}}
				
				// Initialize external links
				initializeExternalLinks(originCoords, destCoords);
				
			}} catch (error) {{
				console.error('Error initializing air freight map:', error);
				showMapFallback('route-map', originPort, destPort);
			}}
		}}
		
		async function getPortCoordinates(portName) {{
			if (!portName) return null;
			
			try {{
				// Check if location exists in database
				if (typeof frappe !== 'undefined' && frappe.db && frappe.db.get_doc) {{
					const location = await frappe.db.get_doc('Location', portName);
					if (location && location.latitude && location.longitude) {{
						return [parseFloat(location.longitude), parseFloat(location.latitude)];
					}}
				}} else {{
					console.log('Frappe DB not available, using default coordinates');
				}}
			}} catch (e) {{
				console.log('Location not found in database:', portName);
			}}
			
			// Fallback to default coordinates
			const defaultCoords = {{
				'PHMNL': [120.9842, 14.5995],  // Manila
				'HKHKG': [114.1694, 22.3193],  // Hong Kong
				'LAX': [-118.4085, 33.9416],   // Los Angeles
				'JFK': [-73.7781, 40.6413],    // JFK
			}};
			
			return defaultCoords[portName] || null;
		}}
		
		function showMapFallback(mapId, originPort, destPort) {{
			console.log('Showing map fallback for:', {{ mapId, originPort, destPort }});
			const mapElement = document.getElementById(mapId);
			const fallbackElement = document.getElementById('route-map-fallback');
			
			if (mapElement && fallbackElement) {{
				mapElement.style.display = 'none';
				fallbackElement.style.display = 'flex';
			}}
		}}
		
		function hideMapFallback(mapId) {{
			const fallbackElement = document.getElementById('route-map-fallback');
			if (fallbackElement) {{
				fallbackElement.style.display = 'none';
			}}
		}}
		
		// MapLibre initialization
		function initializeMapLibreMap(mapId, originCoords, destCoords, originPort, destPort) {{
			console.log('Initializing MapLibre...');
			
			// Load MapLibre GL JS if not already loaded
			if (!window.maplibregl) {{
				// Load CSS
				const css = document.createElement('link');
				css.rel = 'stylesheet';
				css.href = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css';
				document.head.appendChild(css);
				
				// Load JS
				const script = document.createElement('script');
				script.src = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
				script.onload = () => createMapLibreMap(mapId, originCoords, destCoords, originPort, destPort);
				document.head.appendChild(script);
			}} else {{
				createMapLibreMap(mapId, originCoords, destCoords, originPort, destPort);
			}}
		}}
		
		function createMapLibreMap(mapId, originCoords, destCoords, originPort, destPort) {{
			const checkElement = () => {{
				const mapElement = document.getElementById(mapId);
				if (mapElement) {{
					try {{
						console.log('Creating MapLibre map with:', {{ mapId, originCoords, destCoords, originPort, destPort }});
						
						// Create map centered between the two points
						const centerLat = (originCoords[1] + destCoords[1]) / 2;
						const centerLon = (originCoords[0] + destCoords[0]) / 2;
						
						const map = new maplibregl.Map({{
							container: mapId,
							style: {{
								version: 8,
								sources: {{
									'osm': {{
										type: 'raster',
										tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'],
										tileSize: 256,
										attribution: '&copy; OpenStreetMap contributors'
									}}
								}},
								layers: [
									{{
										id: 'osm',
										type: 'raster',
										source: 'osm'
									}}
								]
							}},
							center: [centerLon, centerLat],
							zoom: 13
						}});
						
						// Add origin marker
						const originMarker = new maplibregl.Marker({{ color: 'green' }})
							.setLngLat([originCoords[0], originCoords[1]])
							.setPopup(new maplibregl.Popup().setHTML('<strong>Origin:</strong> ' + originPort))
							.addTo(map);
						
						// Add destination marker
						const destMarker = new maplibregl.Marker({{ color: 'red' }})
							.setLngLat([destCoords[0], destCoords[1]])
							.setPopup(new maplibregl.Popup().setHTML('<strong>Destination:</strong> ' + destPort))
							.addTo(map);
						
						// Add route line
						map.on('load', () => {{
							map.addSource('route', {{
								type: 'geojson',
								data: {{
									type: 'Feature',
									properties: {{}},
									geometry: {{
										type: 'LineString',
										coordinates: [
											[originCoords[0], originCoords[1]],
											[destCoords[0], destCoords[1]]
										]
									}}
								}}
							}});
							
							map.addLayer({{
								id: 'route',
								type: 'line',
								source: 'route',
								layout: {{
									'line-join': 'round',
									'line-cap': 'round'
								}},
								paint: {{
									'line-color': 'blue',
									'line-width': 4,
									'line-dasharray': [2, 2]
								}}
							}});
						}});
						
						// Fit map to show both markers
						const bounds = new maplibregl.LngLatBounds();
						bounds.extend([originCoords[0], originCoords[1]]);
						bounds.extend([destCoords[0], destCoords[1]]);
						map.fitBounds(bounds, {{ padding: 50 }});
						
						// Hide fallback when map loads successfully
						hideMapFallback(mapId);
						
						console.log('MapLibre map created successfully');
						
					}} catch (error) {{
						console.error('Error creating MapLibre map:', error);
						// Keep fallback visible on error
					}}
				}} else {{
					// Retry after a short delay
					setTimeout(checkElement, 100);
				}}
			}};
			
			checkElement();
		}}
		
		// OpenStreetMap initialization
		function initializeOpenStreetMap(mapId, originCoords, destCoords, originPort, destPort) {{
			console.log('Initializing OpenStreetMap...');
			
			if (!window.L) {{
				// Load Leaflet
				const css = document.createElement('link');
				css.rel = 'stylesheet';
				css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
				document.head.appendChild(css);
				
				const script = document.createElement('script');
				script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
				script.onload = () => createOpenStreetMap(mapId, originCoords, destCoords, originPort, destPort);
				document.head.appendChild(script);
			}} else {{
				createOpenStreetMap(mapId, originCoords, destCoords, originPort, destPort);
			}}
		}}
		
		function createOpenStreetMap(mapId, originCoords, destCoords, originPort, destPort) {{
			try {{
				// Create map
				const map = L.map(mapId).setView([5, 5], 4);
				
				// Add tiles
				L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
					attribution: '© OpenStreetMap contributors'
				}}).addTo(map);
				
				// Add markers
				const originMarker = L.marker([originCoords[1], originCoords[0]]).addTo(map);
				originMarker.bindPopup(`<b>Origin:</b> ${{originPort}}`);
				
				const destMarker = L.marker([destCoords[1], destCoords[0]]).addTo(map);
				destMarker.bindPopup(`<b>Destination:</b> ${{destPort}}`);
				
				// Add route line
				const routeLine = L.polyline([
					[originCoords[1], originCoords[0]],
					[destCoords[1], destCoords[0]]
				], {{color: 'blue', weight: 3}}).addTo(map);
				
				// Fit bounds
				const group = new L.featureGroup([originMarker, destMarker]);
				map.fitBounds(group.getBounds().pad(0.1));
				
				console.log('OpenStreetMap created successfully');
				
			}} catch (error) {{
				console.error('Error creating OpenStreetMap:', error);
				showMapFallback(mapId, originPort, destPort);
			}}
		}}
		
		// Google Maps initialization (placeholder)
		function initializeGoogleMap(mapId, originCoords, destCoords, originPort, destPort) {{
			console.log('Google Maps not implemented yet');
			showMapFallback(mapId, originPort, destPort);
		}}
		
		// Mapbox initialization (placeholder)
		function initializeMapboxMap(mapId, originCoords, destCoords, originPort, destPort) {{
			console.log('Mapbox not implemented yet');
			showMapFallback(mapId, originPort, destPort);
		}}
		
		// External links
		function initializeExternalLinks(originCoords, destCoords) {{
			const googleLink = document.getElementById('route-google-link');
			const osmLink = document.getElementById('route-osm-link');
			const appleLink = document.getElementById('route-apple-link');
			
			if (googleLink) {{
				googleLink.href = `https://www.google.com/maps/dir/${{originCoords[1]}},${{originCoords[0]}}/${{destCoords[1]}},${{destCoords[0]}}`;
			}}
			if (osmLink) {{
				osmLink.href = `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${{originCoords[1]}},${{originCoords[0]}};${{destCoords[1]}},${{destCoords[0]}}`;
			}}
			if (appleLink) {{
				appleLink.href = `http://maps.apple.com/?daddr=${{destCoords[1]}},${{destCoords[0]}}&saddr=${{originCoords[1]}},${{originCoords[0]}}`;
			}}
		}}
		
		// Milestone action functions
		function captureActualStart(milestoneId) {{
			console.log('Capture Actual Start for milestone:', milestoneId);
			frappe.call({{
				method: 'frappe.client.set_value',
				args: {{
					doctype: 'Job Milestone',
					name: milestoneId,
					fieldname: 'actual_start',
					value: frappe.datetime.now_datetime()
				}},
				callback: function(r) {{
					if (!r.exc) {{
						frappe.show_alert({{message: __('Actual start time captured'), indicator: 'green'}});
						// Refresh the milestone HTML
						cur_frm.trigger('refresh');
					}}
				}}
			}});
		}}
		
		function captureActualEnd(milestoneId) {{
			console.log('Capture Actual End for milestone:', milestoneId);
			frappe.call({{
				method: 'frappe.client.set_value',
				args: {{
					doctype: 'Job Milestone',
					name: milestoneId,
					fieldname: 'actual_end',
					value: frappe.datetime.now_datetime()
				}},
				callback: function(r) {{
					if (!r.exc) {{
						frappe.show_alert({{message: __('Actual end time captured'), indicator: 'green'}});
						// Refresh the milestone HTML
						cur_frm.trigger('refresh');
					}}
				}}
			}});
		}}
		
		function viewMilestone(milestoneId) {{
			console.log('View Milestone for milestone:', milestoneId);
			frappe.set_route('Form', 'Job Milestone', milestoneId);
		}}
		</script>
		"""
			
			return html
			
		except Exception as e:
			frappe.log_error(f"Error in get_milestone_html: {str(e)}", "Air Shipment - Milestone HTML")
			return "<div class='alert alert-danger'>Error loading milestone view. Please check the error log.</div>"
	
	def format_datetime(self, datetime_value):
		"""Format datetime for display"""
		if not datetime_value:
			return None
		
		try:
			from frappe.utils import format_datetime
			return format_datetime(datetime_value, "dd-MM-yyyy HH:mm")
		except:
			return str(datetime_value)
	
	def get_dg_compliance_badge(self):
		"""Get DG compliance badge HTML"""
		if not self.has_dg_fields():
			return ""
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			return ""
		
		# Get compliance status
		compliance_result = self.check_dg_compliance()
		compliance_status = compliance_result.get('status', 'Unknown')
		
		# Determine badge color and text
		if compliance_status == 'Compliant':
			badge_class = 'dg-badge-compliant'
			badge_text = 'DG Compliant'
			badge_icon = 'fa-check-circle'
		elif compliance_status == 'Non-Compliant':
			badge_class = 'dg-badge-non-compliant'
			badge_text = 'DG Non-Compliant'
			badge_icon = 'fa-exclamation-triangle'
		else:
			badge_class = 'dg-badge-unknown'
			badge_text = 'DG Status Unknown'
			badge_icon = 'fa-question-circle'
		
		return f'''
		<div class="detail-item dg-compliance-badge">
			<div class="dg-badge {badge_class}">
				<i class="fa {badge_icon}"></i>
				<span>{badge_text}</span>
			</div>
		</div>
		'''
	
	@frappe.whitelist(allow_guest=True)
	def get_port_coordinates(self, port_name):
		"""Get coordinates for a port from Location doctype"""
		if not port_name:
			return None
		
		try:
			# Get location document
			location = frappe.get_doc("Location", port_name);
			if location and location.latitude and location.longitude:
				return [float(location.latitude), float(location.longitude)]
		except Exception as e:
			frappe.log_error(f"Error getting coordinates for {port_name}: {str(e)}", "Air Shipment - Get Port Coordinates")
		
		return None
	
	def has_dg_fields(self):
		"""Check if dangerous goods fields are available"""
		try:
			return hasattr(self, 'contains_dangerous_goods')
		except:
			return False
	
	def validate(self):
		"""Validate Air Shipment document"""
		self.validate_dangerous_goods()
		self.validate_dg_compliance()
		# Update DG compliance status automatically
		self.update_dg_compliance_status()
		self.validate_accounts()
	
	def on_update(self):
		"""Called after document is updated"""
		# Update DG compliance status when document is updated
		self.update_dg_compliance_status()
	
	def before_save(self):
		"""Called before document is saved"""
		# Update DG compliance status before saving
		self.update_dg_compliance_status()
		# Job Costing Number will be created in after_insert method
	
	def after_insert(self):
		"""Create Job Costing Number after document is inserted"""
		self.create_job_costing_number_if_needed()
		# Save the document to persist the job_costing_number field
		if self.job_costing_number:
			self.save(ignore_permissions=True)
	
	def validate_dangerous_goods(self):
		"""Validate dangerous goods requirements"""
		if not self.has_dg_fields():
			return
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			return
		
		# Check if any packages contain dangerous goods
		has_dg_packages = False
		for package in self.packages:
			if (package.dg_substance or package.un_number or 
				package.proper_shipping_name or package.dg_class):
				has_dg_packages = True
				break
		
		if not has_dg_packages:
			frappe.throw(_("Dangerous goods flag is set but no dangerous goods packages found. Please add dangerous goods information to packages or uncheck the 'Contains Dangerous Goods' flag."))
		
		# Validate emergency contact information
		dg_emergency_contact = getattr(self, 'dg_emergency_contact', None)
		dg_emergency_phone = getattr(self, 'dg_emergency_phone', None)
		
		if not dg_emergency_contact:
			frappe.throw(_("Emergency contact is required for dangerous goods shipments."))
		
		if not dg_emergency_phone:
			frappe.throw(_("Emergency phone number is required for dangerous goods shipments."))
	
	def validate_dg_compliance(self):
		"""Validate dangerous goods compliance"""
		if not self.has_dg_fields():
			return
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			return
		
		# Validate each dangerous goods package
		for package in self.packages:
			if not (package.dg_substance or package.un_number):
				continue
			
			# Required fields for dangerous goods
			required_fields = [
				('un_number', 'UN Number'),
				('proper_shipping_name', 'Proper Shipping Name'),
				('dg_class', 'DG Class'),
				('packing_group', 'Packing Group')
			]
			
			for field, label in required_fields:
				if not getattr(package, field, None):
					frappe.throw(_("Field {0} is required for dangerous goods package: {1}").format(label, package.commodity or 'Unknown'))
			
			# Validate emergency contact for each package
			if not package.emergency_contact_name:
				frappe.throw(_("Emergency contact name is required for dangerous goods package: {0}").format(package.commodity or 'Unknown'))
			
			if not package.emergency_contact_phone:
				frappe.throw(_("Emergency contact phone is required for dangerous goods package: {0}").format(package.commodity or 'Unknown'))
			
			# Validate radioactive materials
			if package.is_radioactive:
				if not package.transport_index:
					frappe.throw(_("Transport Index is required for radioactive materials in package: {0}").format(package.commodity or 'Unknown'))
				
				if not package.radiation_level:
					frappe.throw(_("Radiation Level is required for radioactive materials in package: {0}").format(package.commodity or 'Unknown'))
			
			# Validate temperature controlled dangerous goods
			if package.temp_controlled:
				if not package.min_temperature and not package.max_temperature:
					frappe.throw(_("Temperature range is required for temperature controlled dangerous goods in package: {0}").format(package.commodity or 'Unknown'))
	
	@frappe.whitelist()
	def check_dg_compliance(self):
		"""Check dangerous goods compliance status"""
		if not self.has_dg_fields():
			return {"status": "Not Available", "message": "Dangerous goods fields not available"}
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			return {"status": "Compliant", "message": "No dangerous goods in this shipment"}
		
		compliance_issues = []
		
		# Check main document compliance
		dg_emergency_contact = getattr(self, 'dg_emergency_contact', None)
		dg_emergency_phone = getattr(self, 'dg_emergency_phone', None)
		dg_declaration_complete = getattr(self, 'dg_declaration_complete', False)
		
		if not dg_emergency_contact:
			compliance_issues.append("Emergency contact not specified")
		
		if not dg_emergency_phone:
			compliance_issues.append("Emergency phone not specified")
		
		if not dg_declaration_complete:
			compliance_issues.append("DG declaration not complete")
		
		# Check package compliance
		for package in self.packages:
			if not (package.dg_substance or package.un_number):
				continue
			
			package_issues = []
			if not package.un_number:
				package_issues.append("UN Number missing")
			if not package.proper_shipping_name:
				package_issues.append("Proper Shipping Name missing")
			if not package.dg_class:
				package_issues.append("DG Class missing")
			if not package.emergency_contact_name:
				package_issues.append("Emergency contact missing")
			
			if package_issues:
				compliance_issues.append(f"Package {package.commodity or 'Unknown'}: {', '.join(package_issues)}")
		
		if compliance_issues:
			return {
				"status": "Non-Compliant",
				"message": "Compliance issues found",
				"issues": compliance_issues
			}
		else:
			return {
				"status": "Compliant",
				"message": "All dangerous goods requirements met"
			}
	
	def update_dg_compliance_status(self):
		"""Update DG compliance status based on current data"""
		if not self.has_dg_fields():
			return
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			# No dangerous goods, clear the status field
			if hasattr(self, 'dg_compliance_status'):
				setattr(self, 'dg_compliance_status', '')
			return
		
		# Check compliance using existing method
		compliance_result = self.check_dg_compliance()
		compliance_status = compliance_result.get('status', 'Unknown')
		
		# Update the compliance status field
		if hasattr(self, 'dg_compliance_status'):
			setattr(self, 'dg_compliance_status', compliance_status)
	
	@frappe.whitelist()
	def refresh_dg_compliance_status(self):
		"""Refresh DG compliance status and return updated status"""
		self.update_dg_compliance_status()
		compliance_result = self.check_dg_compliance()
		return {
			"status": compliance_result.get('status', 'Unknown'),
			"message": compliance_result.get('message', ''),
			"issues": compliance_result.get('issues', [])
		}
	
	@frappe.whitelist()
	def generate_dg_declaration(self):
		"""Generate dangerous goods declaration"""
		if not self.has_dg_fields():
			frappe.throw(_("Dangerous goods fields not available"))
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			frappe.throw(_("No dangerous goods in this shipment"))
		
		# Check if Dangerous Goods Declaration DocType exists
		if not frappe.db.exists("DocType", "Dangerous Goods Declaration"):
			# Create a simple text-based declaration instead
			declaration_content = self._generate_text_dg_declaration()
			
			# Update the job with declaration status
			if hasattr(self, 'dg_declaration_complete'):
				setattr(self, 'dg_declaration_complete', 1)
			if hasattr(self, 'dg_declaration_number'):
				setattr(self, 'dg_declaration_number', f"DG-DEC-{self.name}")
			self.save()
			
			return {
				"status": "success",
				"message": "DG Declaration generated as text document (Dangerous Goods Declaration DocType not available)",
				"declaration": f"DG-DEC-{self.name}",
				"content": declaration_content
			}
		
		try:
			# Create DG declaration document
			dg_declaration = frappe.new_doc("Dangerous Goods Declaration")
			dg_declaration.air_freight_job = self.name
			dg_declaration.shipper = self.shipper
			dg_declaration.consignee = self.consignee
			dg_declaration.origin_port = self.origin_port
			dg_declaration.destination_port = self.destination_port
			dg_emergency_contact = getattr(self, 'dg_emergency_contact', None)
			dg_emergency_phone = getattr(self, 'dg_emergency_phone', None)
			dg_emergency_email = getattr(self, 'dg_emergency_email', None)
			
			dg_declaration.emergency_contact = dg_emergency_contact
			dg_declaration.emergency_phone = dg_emergency_phone
			dg_declaration.emergency_email = dg_emergency_email
			
			# Add package details
			for package in self.packages:
				if package.dg_substance or package.un_number:
					dg_package = dg_declaration.append("packages")
					dg_package.commodity = package.commodity
					dg_package.un_number = package.un_number
					dg_package.proper_shipping_name = package.proper_shipping_name
					dg_package.dg_class = package.dg_class
					dg_package.packing_group = package.packing_group
					dg_package.net_quantity = package.net_quantity_per_package
					dg_package.packing_instruction = package.packing_instruction
					dg_package.emergency_contact = package.emergency_contact_name
					dg_package.emergency_phone = package.emergency_contact_phone
			
			dg_declaration.insert()
			
			# Update the job with declaration number
			if hasattr(self, 'dg_declaration_number'):
				setattr(self, 'dg_declaration_number', dg_declaration.name)
			if hasattr(self, 'dg_declaration_complete'):
				setattr(self, 'dg_declaration_complete', 1)
			self.save()
			
			return {
				"status": "success",
				"message": f"DG Declaration {dg_declaration.name} created successfully",
				"declaration": dg_declaration.name
			}
			
		except Exception as e:
			# Fallback to text-based declaration
			declaration_content = self._generate_text_dg_declaration()
			
			# Update the job with declaration status
			if hasattr(self, 'dg_declaration_complete'):
				setattr(self, 'dg_declaration_complete', 1)
			if hasattr(self, 'dg_declaration_number'):
				setattr(self, 'dg_declaration_number', f"DG-DEC-{self.name}")
			self.save()
			
			return {
				"status": "success",
				"message": f"DG Declaration generated as text document (Error: {str(e)})",
				"declaration": f"DG-DEC-{self.name}",
				"content": declaration_content
			}
	
	def _generate_text_dg_declaration(self):
		"""Generate text-based dangerous goods declaration"""
		declaration_lines = []
		declaration_lines.append("DANGEROUS GOODS DECLARATION")
		declaration_lines.append("=" * 50)
		declaration_lines.append(f"Air Freight Job: {self.name}")
		declaration_lines.append(f"Shipper: {self.shipper}")
		declaration_lines.append(f"Consignee: {self.consignee}")
		declaration_lines.append(f"Origin: {self.origin_port}")
		declaration_lines.append(f"Destination: {self.destination_port}")
		declaration_lines.append("")
		
		# Emergency contact information
		dg_emergency_contact = getattr(self, 'dg_emergency_contact', None)
		dg_emergency_phone = getattr(self, 'dg_emergency_phone', None)
		dg_emergency_email = getattr(self, 'dg_emergency_email', None)
		
		declaration_lines.append("EMERGENCY CONTACT INFORMATION:")
		declaration_lines.append(f"Contact: {dg_emergency_contact or 'Not specified'}")
		declaration_lines.append(f"Phone: {dg_emergency_phone or 'Not specified'}")
		declaration_lines.append(f"Email: {dg_emergency_email or 'Not specified'}")
		declaration_lines.append("")
		
		# Package details
		declaration_lines.append("DANGEROUS GOODS PACKAGES:")
		declaration_lines.append("-" * 30)
		
		for i, package in enumerate(self.packages, 1):
			if package.dg_substance or package.un_number:
				declaration_lines.append(f"Package {i}:")
				declaration_lines.append(f"  Commodity: {package.commodity or 'Not specified'}")
				declaration_lines.append(f"  UN Number: {package.un_number or 'Not specified'}")
				declaration_lines.append(f"  Proper Shipping Name: {package.proper_shipping_name or 'Not specified'}")
				declaration_lines.append(f"  DG Class: {package.dg_class or 'Not specified'}")
				declaration_lines.append(f"  Packing Group: {package.packing_group or 'Not specified'}")
				declaration_lines.append(f"  Net Quantity: {package.net_quantity_per_package or 0}")
				declaration_lines.append(f"  Emergency Contact: {package.emergency_contact_name or 'Not specified'}")
				declaration_lines.append(f"  Emergency Phone: {package.emergency_contact_phone or 'Not specified'}")
				declaration_lines.append("")
		
		declaration_lines.append("DECLARATION:")
		declaration_lines.append("I hereby declare that the above information is correct and complete.")
		declaration_lines.append("The dangerous goods are properly classified, packaged, marked, and labeled")
		declaration_lines.append("in accordance with the applicable international regulations.")
		declaration_lines.append("")
		declaration_lines.append(f"Generated on: {frappe.utils.now_datetime()}")
		
		return "\n".join(declaration_lines)
	
	@frappe.whitelist()
	def send_dg_alert(self, alert_type="compliance"):
		"""Send dangerous goods alerts"""
		if not self.has_dg_fields():
			return {"status": "Not Available", "message": "Dangerous goods fields not available"}
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			return {"status": "No action needed", "message": "No dangerous goods in shipment"}
		
		# Get relevant contacts
		contacts = []
		if self.shipper_contact:
			contacts.append(self.shipper_contact)
		if self.consignee_contact:
			contacts.append(self.consignee_contact)
		
		# Add emergency contacts
		dg_emergency_contact = getattr(self, 'dg_emergency_contact', None)
		if dg_emergency_contact:
			contacts.append(dg_emergency_contact)
		
		# Send alerts based on type
		dg_compliance_status = getattr(self, 'dg_compliance_status', 'Unknown')
		dg_emergency_phone = getattr(self, 'dg_emergency_phone', 'Not specified')
		
		if alert_type == "compliance":
			message = f"Dangerous Goods Compliance Alert for Job {self.name}"
			details = f"DG compliance status: {dg_compliance_status}"
		elif alert_type == "emergency":
			message = f"Dangerous Goods Emergency Alert for Job {self.name}"
			details = f"Emergency contact: {dg_emergency_contact} - {dg_emergency_phone}"
		else:
			message = f"Dangerous Goods Alert for Job {self.name}"
			details = f"Alert type: {alert_type}"
		
		# Create notification
		frappe.publish_realtime('dg_alert', {
			'job': self.name,
			'message': message,
			'details': details,
			'contacts': contacts
		})
		
		return {
			"status": "success",
			"message": f"DG alert sent to {len(contacts)} contacts"
		}
	
	@frappe.whitelist()
	def get_dg_dashboard_info(self):
		"""Get dangerous goods information for dashboard display"""
		# Check if dangerous goods fields are available
		if not self.has_dg_fields():
			return {
				"has_dg": False,
				"alert_level": "none",
				"message": "Dangerous goods fields not available"
			}
		
		# Check if dangerous goods field exists (for backward compatibility)
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		
		if not contains_dg:
			return {
				"has_dg": False,
				"alert_level": "none",
				"message": "No dangerous goods in this shipment"
			}
		
		# Count dangerous goods packages
		dg_packages = 0
		radioactive_packages = 0
		temp_controlled_dg = 0
		compliance_issues = 0
		
		for package in self.packages:
			if package.dg_substance or package.un_number:
				dg_packages += 1
				if package.is_radioactive:
					radioactive_packages += 1
				if package.temp_controlled:
					temp_controlled_dg += 1
				
				# Check for compliance issues
				if not package.un_number or not package.proper_shipping_name or not package.emergency_contact_name:
					compliance_issues += 1
		
		# Determine alert level
		alert_level = "warning"  # Default for DG presence
		if radioactive_packages > 0:
			alert_level = "danger"  # Highest priority for radioactive
		elif temp_controlled_dg > 0:
			alert_level = "warning"  # High priority for temp controlled
		elif compliance_issues > 0:
			alert_level = "danger"  # High priority for compliance issues
		
		# Build message
		message_parts = [f"{dg_packages} dangerous goods package(s)"]
		if radioactive_packages > 0:
			message_parts.append(f"{radioactive_packages} radioactive")
		if temp_controlled_dg > 0:
			message_parts.append(f"{temp_controlled_dg} temperature controlled")
		if compliance_issues > 0:
			message_parts.append(f"{compliance_issues} compliance issues")
		
		message = ", ".join(message_parts)
		
		dg_compliance_status = getattr(self, 'dg_compliance_status', 'Unknown')
		dg_emergency_contact = getattr(self, 'dg_emergency_contact', None)
		dg_emergency_phone = getattr(self, 'dg_emergency_phone', None)
		
		# Get compliance status
		compliance_result = self.check_dg_compliance()
		compliance_status = compliance_result.get('status', 'Unknown')
		
		return {
			"has_dg": True,
			"alert_level": alert_level,
			"message": message,
			"dg_packages": dg_packages,
			"radioactive_packages": radioactive_packages,
			"temp_controlled_dg": temp_controlled_dg,
			"compliance_issues": compliance_issues,
			"compliance_status": compliance_status,
			"emergency_contact": dg_emergency_contact,
			"emergency_phone": dg_emergency_phone
		}
	
	def validate_accounts(self):
		"""Validate accounting fields"""
		if not self.company:
			frappe.throw(_("Company is required"))
		
		# Validate cost center belongs to company
		if self.cost_center:
			cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cost_center_company and cost_center_company != self.company:
				frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
					self.cost_center, self.company))
		
		# Validate profit center belongs to company
		if self.profit_center:
			profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
			if profit_center_company and profit_center_company != self.company:
				frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
					self.profit_center, self.company))
		
		# Validate branch belongs to company
		if self.branch:
			branch_company = frappe.db.get_value("Branch", self.branch, "company")
			if branch_company and branch_company != self.company:
				frappe.throw(_("Branch {0} does not belong to Company {1}").format(
					self.branch, self.company))
	
	def create_job_costing_number_if_needed(self):
		"""Create Job Costing Number when document is first saved"""
		# Only create if job_costing_number is not set
		if not self.job_costing_number:
			# Check if this is the first save (no existing Job Costing Number)
			existing_job_ref = frappe.db.get_value("Job Costing Number", {
				"job_type": "Air Shipment",
				"job_no": self.name
			})
			
			if not existing_job_ref:
			# Create Job Costing Number
			job_ref = frappe.new_doc("Job Costing Number")
			job_ref.job_type = "Air Shipment"
			job_ref.job_no = self.name
			job_ref.company = self.company
			job_ref.branch = self.branch
			job_ref.cost_center = self.cost_center
			job_ref.profit_center = self.profit_center
			# Leave recognition_date blank - will be filled in separate function
			# Use air shipment's booking_date instead
			job_ref.job_open_date = self.booking_date
			job_ref.insert(ignore_permissions=True)
				
				# Set the job_costing_number field
				self.job_costing_number = job_ref.name
				
				frappe.msgprint(_("Job Costing Number {0} created successfully").format(job_ref.name))