# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class AirShipment(Document):
	def before_save(self):
		"""Calculate sustainability metrics before saving"""
		self.calculate_sustainability_metrics()
	
	def after_submit(self):
		"""Record sustainability metrics after shipment submission"""
		self.record_sustainability_metrics()
	
	def calculate_sustainability_metrics(self):
		"""Calculate sustainability metrics for this air shipment"""
		try:
			# Calculate carbon footprint based on weight and distance
			if hasattr(self, 'weight') and hasattr(self, 'origin_port') and hasattr(self, 'destination_port'):
				# Get distance between ports (simplified calculation)
				distance = self._calculate_port_distance(self.origin_port, self.destination_port)
				if distance and self.weight:
					# Use air freight emission factor
					emission_factor = 0.5  # kg CO2e per ton-km for air freight
					carbon_footprint = (flt(self.weight) / 1000) * distance * emission_factor
					self.estimated_carbon_footprint = carbon_footprint
					
					# Calculate fuel consumption estimate
					fuel_consumption = self._calculate_fuel_consumption(distance, flt(self.weight))
					self.estimated_fuel_consumption = fuel_consumption
				
		except Exception as e:
			frappe.log_error(f"Error calculating sustainability metrics for Air Shipment {self.name}: {e}", "Air Shipment Sustainability Error")
	
	def record_sustainability_metrics(self):
		"""Record sustainability metrics in the centralized system"""
		try:
			from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
			
			result = integrate_sustainability(
				doctype=self.doctype,
				docname=self.name,
				module="Air Freight",
				doc=self
			)
			
			if result.get("status") == "success":
				frappe.msgprint(_("Sustainability metrics recorded successfully"))
			elif result.get("status") == "skipped":
				# Don't show message if sustainability is not enabled
				pass
			else:
				frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Air Shipment Sustainability Error")
				
		except Exception as e:
			frappe.log_error(f"Error recording sustainability metrics for Air Shipment {self.name}: {e}", "Air Shipment Sustainability Error")
	
	def _calculate_port_distance(self, origin: str, destination: str) -> float:
		"""Calculate distance between ports (simplified)"""
		# This would typically use a geocoding service or database
		# For now, return a default distance based on common air routes
		route_distances = {
			("LAX", "JFK"): 3944,  # Los Angeles to New York
			("LHR", "JFK"): 3459,  # London to New York
			("NRT", "LAX"): 5472,  # Tokyo to Los Angeles
			("DXB", "LHR"): 3420,  # Dubai to London
		}
		
		# Try to find exact match
		key = (origin, destination)
		if key in route_distances:
			return route_distances[key]
		
		# Try reverse match
		key = (destination, origin)
		if key in route_distances:
			return route_distances[key]
		
		# Default distance
		return 2000.0  # Default 2000 km
	
	def _calculate_fuel_consumption(self, distance: float, weight: float) -> float:
		"""Calculate estimated fuel consumption for air freight"""
		# Air freight fuel consumption is typically 3-4 L per 100 km per ton
		fuel_rate = 3.5  # L per 100 km per ton
		return (fuel_rate * distance * (weight / 1000)) / 100.0

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
			
			# Get map renderer and API keys from Logistics Settings
			map_renderer = 'OpenStreetMap'  # Default
			google_api_key = ''
			mapbox_api_key = ''
			try:
				logistics_settings = frappe.get_single('Logistics Settings')
				if logistics_settings:
					if hasattr(logistics_settings, 'map_renderer') and logistics_settings.map_renderer:
						map_renderer = logistics_settings.map_renderer
					
					# Decrypt password fields using get_decrypted_password
					from frappe.utils.password import get_decrypted_password
					
					# Get Google API key (Password field needs decryption)
					google_api_key = get_decrypted_password(
						"Logistics Settings",
						"Logistics Settings",
						"routing_google_api_key",
						raise_exception=False
					) or ''
					
					# Get Mapbox API key (Password field needs decryption)
					mapbox_api_key = get_decrypted_password(
						"Logistics Settings",
						"Logistics Settings",
						"routing_mapbox_api_key",
						raise_exception=False
					) or ''
			except Exception as e:
				frappe.log_error(f"Error getting map settings from Logistics Settings: {str(e)}", "Air Shipment - Get Map Settings")
			
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
			const mapRenderer = '{map_renderer}'; // From Logistics Settings
			console.log('Origin Port:', originPort);
			console.log('Destination Port:', destPort);
			console.log('Map Renderer from Logistics Settings:', mapRenderer);
			
			if (!originPort && !destPort) {{
				console.log('No ports specified, showing fallback');
				showMapFallback('route-map', originPort, destPort);
				return;
			}}
			
			try {{
				
				// Get coordinates for ports
				const originCoords = await getPortCoordinates(originPort);
				const destCoords = await getPortCoordinates(destPort);
				
				if (!originCoords || !destCoords) {{
					console.log('Coordinates not available, showing fallback');
					showMapFallback('route-map', originPort, destPort);
					return;
				}}
				
				console.log('Coordinates found:', {{ origin: originCoords, destination: destCoords }});
				
				// Initialize map based on renderer (case-insensitive comparison)
				const rendererLower = (mapRenderer || '').toLowerCase();
				console.log('Initializing map with renderer:', rendererLower);
				
				if (rendererLower === 'google maps') {{
					initializeGoogleMap('route-map', originCoords, destCoords, originPort, destPort);
				}} else if (rendererLower === 'mapbox') {{
					initializeMapboxMap('route-map', originCoords, destCoords, originPort, destPort);
				}} else if (rendererLower === 'maplibre') {{
					initializeMapLibreMap('route-map', originCoords, destCoords, originPort, destPort);
				}} else {{
					// Default to OpenStreetMap (including when renderer is 'openstreetmap' or empty)
					console.log('Using OpenStreetMap as default or selected renderer');
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
				// Check if UNLOCO exists in database
				if (typeof frappe !== 'undefined' && frappe.db && frappe.db.get_doc) {{
					const unloco = await frappe.db.get_doc('UNLOCO', portName);
					if (unloco && unloco.latitude && unloco.longitude) {{
						return [parseFloat(unloco.longitude), parseFloat(unloco.latitude)];
					}}
				}} else {{
					console.log('Frappe DB not available, using default coordinates');
				}}
			}} catch (e) {{
				console.log('UNLOCO not found in database:', portName);
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
		
		// Google Maps initialization using Interactive Google Maps JavaScript API (same as run sheet)
		async function initializeGoogleMap(mapId, originCoords, destCoords, originPort, destPort) {{
			console.log('Initializing Google Maps (Interactive)...');
			
			// Note: originCoords and destCoords are [longitude, latitude] format
			// Google Maps expects [latitude, longitude] format
			const originLat = originCoords[1];
			const originLon = originCoords[0];
			const destLat = destCoords[1];
			const destLon = destCoords[0];
			
			// Build waypoints string for Directions API (same format as run sheet)
			const waypoints = `${{originLat}},${{originLon}}|${{destLat}},${{destLon}}`;
			
			// Get API key from server (same method as run sheet)
			try {{
				const apiKeyResponse = await frappe.call({{
					method: 'logistics.air_freight.doctype.air_shipment.air_shipment.get_google_maps_api_key',
					args: {{}}
				}});
				
				const apiKey = apiKeyResponse.message?.api_key;
				
				if (!apiKey || apiKey.length < 10) {{
					console.warn('Google Maps API key not configured, showing fallback');
					showMapFallback(mapId, originPort, destPort);
					return;
				}}
				
				// Get route polyline from Google Directions API (same as run sheet)
				const polylineResponse = await frappe.call({{
					method: 'logistics.air_freight.doctype.air_shipment.air_shipment.get_google_route_polyline',
					args: {{
						waypoints: waypoints
					}}
				}});
				
				if (!polylineResponse.message || !polylineResponse.message.success) {{
					console.warn('Google Directions API failed:', polylineResponse.message?.error);
					showMapFallback(mapId, originPort, destPort);
					return;
				}}
				
				const routes = polylineResponse.message.routes || [];
				if (routes.length === 0) {{
					console.warn('No routes available');
					showMapFallback(mapId, originPort, destPort);
					return;
				}}
				
				// Use first route (same as run sheet)
				const selectedRoute = routes[0];
				const routeIndex = selectedRoute.index;
				
				// Store routes globally for potential route selection (same as run sheet)
				if (!window.airShipmentRoutes) window.airShipmentRoutes = {{}};
				window.airShipmentRoutes[mapId] = routes;
				
				// Load Google Maps JavaScript API if not already loaded (same as run sheet)
				if (window.google && window.google.maps) {{
					createInteractiveGoogleMap(mapId, routes, routeIndex, originLat, originLon, destLat, destLon, originPort, destPort);
				}} else {{
					// Load Google Maps JavaScript API
					const script = document.createElement('script');
					script.src = `https://maps.googleapis.com/maps/api/js?key=${{apiKey}}&libraries=geometry`;
					script.async = true;
					script.defer = true;
					script.onload = () => {{
						createInteractiveGoogleMap(mapId, routes, routeIndex, originLat, originLon, destLat, destLon, originPort, destPort);
					}};
					script.onerror = () => {{
						console.warn('Failed to load Google Maps JavaScript API, showing fallback');
						showMapFallback(mapId, originPort, destPort);
					}};
					document.head.appendChild(script);
				}}
				
			}} catch (error) {{
				console.error('Error initializing Google Maps:', error);
				showMapFallback(mapId, originPort, destPort);
			}}
		}}
		
		// Create interactive Google Maps with route (same as run sheet)
		function createInteractiveGoogleMap(mapId, routes, selectedRouteIndex, originLat, originLon, destLat, destLon, originPort, destPort) {{
			const mapElement = document.getElementById(mapId);
			if (!mapElement) {{
				console.error('Map element not found:', mapId);
				return;
			}}
			
			// Clear any existing content
			mapElement.innerHTML = '';
			
			// Calculate center point
			const centerLat = (originLat + destLat) / 2;
			const centerLon = (originLon + destLon) / 2;
			
			// Initialize the map (same as run sheet)
			const bounds = new google.maps.LatLngBounds();
			const map = new google.maps.Map(mapElement, {{
				zoom: 10,
				center: {{ lat: centerLat, lng: centerLon }},
				mapTypeControl: true,
				streetViewControl: true,
				fullscreenControl: true,
				zoomControl: true,
				scaleControl: true,
				rotateControl: true
			}});
			
			// Store map instance globally (same as run sheet)
			if (!window.airShipmentMaps) window.airShipmentMaps = {{}};
			window.airShipmentMaps[mapId] = map;
			
			// Store polylines for route updates (same as run sheet)
			if (!window.airShipmentPolylines) window.airShipmentPolylines = {{}};
			window.airShipmentPolylines[mapId] = [];
			
			// Add origin marker (green, labeled 'O')
			const originMarker = new google.maps.Marker({{
				position: {{ lat: originLat, lng: originLon }},
				map: map,
				label: 'O',
				icon: {{
					path: google.maps.SymbolPath.CIRCLE,
					scale: 8,
					fillColor: '#28a745',
					fillOpacity: 1,
					strokeColor: '#ffffff',
					strokeWeight: 2
				}},
				title: `Origin: ${{originPort}}`
			}});
			bounds.extend({{ lat: originLat, lng: originLon }});
			
			// Add destination marker (red, labeled 'D')
			const destMarker = new google.maps.Marker({{
				position: {{ lat: destLat, lng: destLon }},
				map: map,
				label: 'D',
				icon: {{
					path: google.maps.SymbolPath.CIRCLE,
					scale: 8,
					fillColor: '#dc3545',
					fillOpacity: 1,
					strokeColor: '#ffffff',
					strokeWeight: 2
				}},
				title: `Destination: ${{destPort}}`
			}});
			bounds.extend({{ lat: destLat, lng: destLon }});
			
			// Add all route polylines (same as run sheet)
			const selectedRoute = routes[selectedRouteIndex];
			const routeIdx = selectedRoute.index;
			
			routes.forEach((route) => {{
				const isSelected = route.index === routeIdx;
				try {{
					let path = [];
					
					// Handle air routes (ZERO_RESULTS) - create geodesic path from coordinates
					if (route.is_air_route && route.origin && route.destination) {{
						// For air routes, create a simple path with just origin and destination
						// Google Maps will automatically render it as a great circle when geodesic: true
						path = [
							{{ lat: route.origin.lat, lng: route.origin.lon }},
							{{ lat: route.destination.lat, lng: route.destination.lon }}
						];
					}} else if (route.polyline) {{
						// Decode polyline for regular routes
						path = google.maps.geometry.encoding.decodePath(route.polyline);
					}} else {{
						console.warn(`Route ${{route.index}} has no polyline or coordinates`);
						return;
					}}
					
					if (!path || path.length === 0) {{
						console.warn(`Route ${{route.index}} has invalid path`);
						return;
					}}
					
					// Extend bounds with route path
					path.forEach(point => bounds.extend(point));
					
					const polyline = new google.maps.Polyline({{
						path: path,
						geodesic: true,  // Always use geodesic (great circle for air routes)
						strokeColor: isSelected ? '#007bff' : '#dc3545',
						strokeOpacity: isSelected ? 1.0 : 0.8,
						strokeWeight: isSelected ? 6 : 4,
						map: map,
						zIndex: isSelected ? 2 : 1,
						clickable: true
					}});
					
					window.airShipmentPolylines[mapId].push({{
						polyline: polyline,
						routeIndex: route.index
					}});
					
					console.log(`Added route ${{route.index}} (selected: ${{isSelected}})`);
				}} catch (error) {{
					console.error(`Error adding route ${{route.index}}:`, error);
				}}
			}});
			
			// Fit map to show all routes (same as run sheet)
			map.fitBounds(bounds);
			
			// Hide fallback
			const fallbackElement = document.getElementById('route-map-fallback');
			if (fallbackElement) {{
				fallbackElement.style.display = 'none';
			}}
			
			console.log('Interactive Google Maps created successfully');
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
		"""Get coordinates for a port from UNLOCO doctype"""
		if not port_name:
			return None
		
		try:
			# Get UNLOCO document
			unloco = frappe.get_doc("UNLOCO", port_name)
			if unloco and unloco.latitude and unloco.longitude:
				return [float(unloco.latitude), float(unloco.longitude)]
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
		self.validate_dates()
		self.validate_weight_volume()
		self.validate_packages()
		self.validate_awb()
		self.validate_uld()
		self.validate_customs()
		self.validate_insurance()
		self.validate_temperature()
		self.validate_documents()
		self.validate_casslink()
		self.validate_tact()
		self.validate_eawb()
		self.validate_revenue()
		self.validate_billing()
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
		# Apply settings defaults if this is a new document
		if self.is_new():
			self.apply_settings_defaults()
		
		# Update DG compliance status before saving
		self.update_dg_compliance_status()
		# Job Costing Number will be created in after_insert method
	
	def after_insert(self):
		"""Create Job Costing Number after document is inserted"""
		# Apply settings defaults if not already applied
		if not hasattr(self, '_settings_applied'):
			self.apply_settings_defaults()
		
		# Create job costing (method will check settings internally)
		self.create_job_costing_number_if_needed()
		
		# Auto-generate AWB numbers if enabled in settings
		settings = self.get_air_freight_settings()
		if settings:
			if settings.auto_generate_house_awb and not self.house_awb_no:
				self.generate_house_awb_number()
			if settings.auto_generate_master_awb and not self.master_awb:
				self.generate_master_awb_reference()
		
		# Validate and clear invalid link fields before saving
		# This prevents LinkValidationError during save
		if hasattr(self, 'service_level') and self.service_level:
			if not frappe.db.exists("Service Level Agreement", self.service_level):
				self.service_level = None
		if hasattr(self, 'release_type') and self.release_type:
			if not frappe.db.exists("Release Type", self.release_type):
				self.release_type = None
		
		# Save the document to persist changes
		if self.job_costing_number or self.house_awb_no or self.master_awb:
			try:
				self.save(ignore_permissions=True)
			except Exception as e:
				# If save fails due to invalid links, clear them and try again
				if "Could not find" in str(e):
					if hasattr(self, 'service_level') and self.service_level:
						if not frappe.db.exists("Service Level Agreement", self.service_level):
							self.service_level = None
					if hasattr(self, 'release_type') and self.release_type:
						if not frappe.db.exists("Release Type", self.release_type):
							self.release_type = None
					# Try save again
					self.save(ignore_permissions=True)
				else:
					raise
	
	def validate_dangerous_goods(self):
		"""Validate dangerous goods requirements"""
		if not self.has_dg_fields():
			return
		
		contains_dg = getattr(self, 'contains_dangerous_goods', False)
		if not contains_dg:
			return
		
		# Check settings for require DG declaration
		settings = self.get_air_freight_settings()
		if settings and settings.require_dg_declaration:
			dg_declaration_complete = getattr(self, 'dg_declaration_complete', False)
			if not dg_declaration_complete:
				frappe.throw(_("Dangerous Goods Declaration is required for dangerous goods shipments as per company settings."), 
					title=_("DG Declaration Required"))
		
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
	
	def validate_dates(self):
		"""Validate date fields"""
		from frappe.utils import getdate, today
		
		# Validate ETD is before ETA
		if self.etd and self.eta:
			if getdate(self.etd) >= getdate(self.eta):
				frappe.throw(_("ETD (Estimated Time of Departure) must be before ETA (Estimated Time of Arrival)"), 
					title=_("Date Validation Error"))
		
		# Warn if booking date is in the future
		if self.booking_date:
			if getdate(self.booking_date) > getdate(today()):
				frappe.msgprint(_("Booking date is in the future. Please verify this is correct."), 
					indicator="orange", title=_("Date Warning"))
	
	def validate_weight_volume(self):
		"""Validate weight and volume fields"""
		# Validate weight is positive
		if self.weight is not None and self.weight <= 0:
			frappe.throw(_("Weight must be greater than zero"), title=_("Validation Error"))
		
		# Validate volume is positive
		if self.volume is not None and self.volume <= 0:
			frappe.throw(_("Volume must be greater than zero"), title=_("Validation Error"))
		
		# Get settings for volume to weight factor
		settings = self.get_air_freight_settings()
		volume_to_weight_factor = 167  # Default IATA standard
		chargeable_weight_calculation = "Higher of Both"  # Default
		
		if settings:
			volume_to_weight_factor = settings.volume_to_weight_factor or 167
			chargeable_weight_calculation = settings.chargeable_weight_calculation or "Higher of Both"
		
		# Calculate chargeable weight based on settings
		if self.weight and self.volume:
			volume_weight = flt(self.volume) * volume_to_weight_factor
			
			if chargeable_weight_calculation == "Actual Weight":
				chargeable_weight = flt(self.weight)
			elif chargeable_weight_calculation == "Volume Weight":
				chargeable_weight = volume_weight
			else:  # Higher of Both (default)
				chargeable_weight = max(flt(self.weight), volume_weight)
			
			# Update chargeable weight if not set or different
			if not self.chargeable or abs(flt(self.chargeable) - chargeable_weight) > 0.01:
				self.chargeable = chargeable_weight
		elif self.weight:
			# If only weight is provided, use it as chargeable
			if not self.chargeable:
				self.chargeable = self.weight
	
	def validate_packages(self):
		"""Validate package data"""
		# Check if packages table exists and has entries
		if hasattr(self, 'packages') and self.packages:
			total_package_weight = sum(flt(p.weight or 0) for p in self.packages)
			total_package_volume = sum(flt(p.volume or 0) for p in self.packages)
			
			# Warn if package weights don't match total weight (allow small tolerance)
			if self.weight and abs(total_package_weight - flt(self.weight)) > 0.01:
				frappe.msgprint(
					_("Package weights ({0} kg) do not match total weight ({1} kg). Please verify.").format(
						total_package_weight, self.weight
					),
					indicator="orange",
					title=_("Weight Mismatch Warning")
				)
			
			# Warn if package volumes don't match total volume (allow small tolerance)
			if self.volume and abs(total_package_volume - flt(self.volume)) > 0.01:
				frappe.msgprint(
					_("Package volumes ({0} m³) do not match total volume ({1} m³). Please verify.").format(
						total_package_volume, self.volume
					),
					indicator="orange",
					title=_("Volume Mismatch Warning")
				)
			
			# Validate each package has required fields
			for idx, package in enumerate(self.packages, 1):
				if not package.commodity and not package.goods_description:
					frappe.msgprint(
						_("Package {0}: Commodity or description is recommended.").format(idx),
						indicator="blue",
						title=_("Package Information")
					)
	
	def validate_awb(self):
		"""Validate Air Waybill fields"""
		import re
		
		# Validate Master AWB if set
		if self.master_awb:
			if not frappe.db.exists("Master Air Waybill", self.master_awb):
				frappe.throw(
					_("Master AWB {0} does not exist").format(self.master_awb),
					title=_("Validation Error")
				)
			
			# Check Master AWB status
			mawb = frappe.get_doc("Master Air Waybill", self.master_awb)
			if hasattr(mawb, 'flight_status'):
				# Check if flight is cancelled
				if mawb.flight_status == "Cancelled":
					frappe.throw(
						_("Master AWB {0} is associated with a cancelled flight. Please select a different Master AWB.").format(
							self.master_awb
						),
						title=_("Validation Error")
					)
				
				# Warn if flight is delayed
				if mawb.flight_status == "Delayed":
					frappe.msgprint(
						_("Master AWB {0} is associated with a delayed flight.").format(self.master_awb),
						indicator="orange",
						title=_("Flight Status Warning")
					)
		
		# Validate House AWB number format (IATA standard: 11 digits)
		if self.house_awb_no:
			# Remove hyphens and spaces for validation
			awb_clean = self.house_awb_no.replace('-', '').replace(' ', '')
			
			# IATA standard: 11 digits
			if not re.match(r'^\d{11}$', awb_clean):
				frappe.throw(
					_("House AWB number must be 11 digits (IATA format). Current format: {0}").format(
						self.house_awb_no
					),
					title=_("AWB Format Error")
				)
	
	def validate_uld(self):
		"""Validate ULD (Unit Load Device) fields"""
		if self.uld_type:
			# Fetch ULD capacity if ULD type is set
			if not self.uld_capacity_kg:
				uld_capacity = frappe.get_cached_value("Unit Load Device", self.uld_type, "capacity_kg")
				if uld_capacity:
					self.uld_capacity_kg = uld_capacity
			
			# Validate weight doesn't exceed ULD capacity
			if self.uld_capacity_kg and self.weight:
				if flt(self.weight) > flt(self.uld_capacity_kg):
					frappe.msgprint(
						_("Cargo weight ({0} kg) exceeds ULD capacity ({1} kg). Please verify.").format(
							self.weight, self.uld_capacity_kg
						),
						indicator="orange",
						title=_("ULD Capacity Warning")
					)
	
	def validate_customs(self):
		"""Validate customs fields"""
		# Validate customs status progression
		if self.customs_status:
			status_order = ["Not Submitted", "Submitted", "Under Review", "Cleared", "Held", "Rejected"]
			current_index = status_order.index(self.customs_status) if self.customs_status in status_order else -1
			
			# If cleared, validate clearance date
			if self.customs_status == "Cleared":
				if not self.customs_clearance_date:
					frappe.msgprint(
						_("Customs clearance date should be set when status is 'Cleared'."),
						indicator="blue",
						title=_("Customs Information")
					)
		
		# Validate duty and tax amounts are positive
		if self.duty_amount and flt(self.duty_amount) < 0:
			frappe.throw(_("Duty amount cannot be negative"), title=_("Validation Error"))
		
		if self.tax_amount and flt(self.tax_amount) < 0:
			frappe.throw(_("Tax amount cannot be negative"), title=_("Validation Error"))
	
	def validate_insurance(self):
		"""Validate insurance fields"""
		# Validate insurance value is positive
		if self.insurance_value and flt(self.insurance_value) <= 0:
			frappe.throw(_("Insurance value must be greater than zero"), title=_("Validation Error"))
		
		# If claim is filed, validate claim number
		if self.insurance_claim_status and self.insurance_claim_status != "No Claim":
			if not self.insurance_claim_number:
				frappe.msgprint(
					_("Insurance claim number should be set when a claim is filed."),
					indicator="blue",
					title=_("Insurance Information")
				)
			
			if not self.insurance_claim_date:
				frappe.msgprint(
					_("Insurance claim date should be set when a claim is filed."),
					indicator="blue",
					title=_("Insurance Information")
				)
	
	def validate_temperature(self):
		"""Validate temperature control fields"""
		if self.requires_temperature_control:
			# Validate temperature range
			if self.min_temperature is None and self.max_temperature is None:
				frappe.throw(
					_("Temperature range (min/max) is required when temperature control is enabled."),
					title=_("Validation Error")
				)
			
			# Validate min temperature is less than max temperature
			if self.min_temperature is not None and self.max_temperature is not None:
				if flt(self.min_temperature) >= flt(self.max_temperature):
					frappe.throw(
						_("Minimum temperature must be less than maximum temperature."),
						title=_("Validation Error")
					)
			
			# Warn if temperature monitoring is not enabled
			if not self.temperature_monitoring:
				frappe.msgprint(
					_("Temperature monitoring is recommended for temperature-controlled cargo."),
					indicator="orange",
					title=_("Temperature Control Warning")
				)
	
	def validate_documents(self):
		"""Validate document requirements based on direction"""
		if not self.direction:
			return
		
		# Check settings for require customs declaration
		settings = self.get_air_freight_settings()
		require_customs = settings and settings.require_customs_declaration if settings else False
		
		# Export direction requires export license
		if self.direction == "Export":
			if not self.export_license:
				if require_customs:
					frappe.throw(_("Export license is required for export shipments as per company settings."), 
						title=_("Document Required"))
				else:
					frappe.msgprint(
						_("Export license is typically required for export shipments."),
						indicator="blue",
						title=_("Document Information")
					)
		
		# Import direction requires import permit
		if self.direction == "Import":
			if not self.import_permit:
				if require_customs:
					frappe.throw(_("Import permit is required for import shipments as per company settings."), 
						title=_("Document Required"))
				else:
					frappe.msgprint(
						_("Import permit is typically required for import shipments."),
						indicator="blue",
						title=_("Document Information")
					)
		
		# Both directions typically require commercial invoice
		if not self.commercial_invoice_number:
			if require_customs:
				frappe.msgprint(
					_("Commercial invoice is required for international shipments as per company settings."),
					indicator="orange",
					title=_("Document Required")
				)
			else:
				frappe.msgprint(
					_("Commercial invoice is typically required for international shipments."),
					indicator="blue",
					title=_("Document Information")
				)
	
	def validate_casslink(self):
		"""Validate CASSLink integration fields"""
		# If CASS settlement status is set, validate participant code
		if self.cass_settlement_status and self.cass_settlement_status != "Pending":
			if not self.cass_participant_code:
				frappe.msgprint(
					_("CASS participant code should be set when settlement status is not 'Pending'."),
					indicator="blue",
					title=_("CASSLink Information")
				)
			
			# If settled, validate settlement date
			if self.cass_settlement_status == "Settled":
				if not self.cass_settlement_date:
					frappe.msgprint(
						_("CASS settlement date should be set when status is 'Settled'."),
						indicator="blue",
						title=_("CASSLink Information")
					)
		
		# Validate settlement amount is positive
		if self.cass_settlement_amount and flt(self.cass_settlement_amount) < 0:
			frappe.throw(_("CASS settlement amount cannot be negative"), title=_("Validation Error"))
	
	def validate_tact(self):
		"""Validate TACT integration fields"""
		# If TACT rate lookup is enabled, validate rate reference
		if self.tact_rate_lookup:
			if not self.tact_rate_reference:
				frappe.msgprint(
					_("TACT rate reference should be set when TACT rate lookup is enabled."),
					indicator="blue",
					title=_("TACT Information")
				)
			
			# Validate rate validity date
			if self.tact_rate_validity:
				from frappe.utils import getdate, today
				if getdate(self.tact_rate_validity) < today():
					frappe.msgprint(
						_("TACT rate validity date is in the past. Rate may no longer be valid."),
						indicator="orange",
						title=_("TACT Rate Warning")
					)
		
		# Validate TACT rate amount is positive
		if self.tact_rate_amount and flt(self.tact_rate_amount) <= 0:
			frappe.throw(_("TACT rate amount must be greater than zero"), title=_("Validation Error"))
	
	def validate_eawb(self):
		"""Validate e-AWB fields"""
		if self.eawb_enabled:
			# If e-AWB is enabled, validate status progression
			if self.eawb_status:
				status_order = ["Not Created", "Created", "Signed", "Submitted", "Accepted", "Rejected"]
				current_index = status_order.index(self.eawb_status) if self.eawb_status in status_order else -1
				
				# If signed, validate signature fields
				if self.eawb_status in ["Signed", "Submitted", "Accepted"]:
					if not self.eawb_digital_signature:
						frappe.msgprint(
							_("Digital signature should be set when e-AWB status is 'Signed' or later."),
							indicator="blue",
							title=_("e-AWB Information")
						)
					
					if not self.eawb_signed_date:
						frappe.msgprint(
							_("e-AWB signed date should be set when e-AWB is signed."),
							indicator="blue",
							title=_("e-AWB Information")
						)
	
	def validate_revenue(self):
		"""Validate revenue recognition fields"""
		# Validate revenue amount is positive
		if self.revenue_amount and flt(self.revenue_amount) <= 0:
			frappe.throw(_("Revenue amount must be greater than zero"), title=_("Validation Error"))
		
		# If partial revenue is enabled, validate recognized amount
		if self.partial_revenue_enabled:
			if self.revenue_amount and self.recognized_revenue_amount:
				if flt(self.recognized_revenue_amount) > flt(self.revenue_amount):
					frappe.throw(
						_("Recognized revenue amount cannot exceed total revenue amount."),
						title=_("Validation Error")
					)
		
		# If revenue recognition date is set, validate it's not in the future
		if self.revenue_recognition_date:
			from frappe.utils import getdate, today
			if getdate(self.revenue_recognition_date) > today():
				frappe.msgprint(
					_("Revenue recognition date is in the future. Please verify this is correct."),
					indicator="orange",
					title=_("Revenue Recognition Warning")
				)
	
	def validate_billing(self):
		"""Validate billing automation fields"""
		# If auto billing is enabled, validate billing status
		if self.auto_billing_enabled:
			if not self.billing_status or self.billing_status == "Not Billed":
				frappe.msgprint(
					_("Billing status should be updated when auto billing is enabled."),
					indicator="blue",
					title=_("Billing Information")
				)
		
		# If billed, validate sales invoice link
		if self.billing_status in ["Billed", "Partially Billed"]:
			if not self.sales_invoice:
				frappe.msgprint(
					_("Sales invoice should be linked when billing status is 'Billed' or 'Partially Billed'."),
					indicator="blue",
					title=_("Billing Information")
				)
			
			if not self.billing_date:
				frappe.msgprint(
					_("Billing date should be set when billing status is 'Billed' or 'Partially Billed'."),
					indicator="blue",
					title=_("Billing Information")
				)
		
		# Validate billing amount is positive
		if self.billing_amount and flt(self.billing_amount) <= 0:
			frappe.throw(_("Billing amount must be greater than zero"), title=_("Validation Error"))
	
	@frappe.whitelist()
	def lookup_tact_rate(self):
		"""Lookup TACT rate for this shipment"""
		try:
			# Get IATA Settings
			iata_settings = frappe.get_single("IATA Settings")
			
			if not iata_settings.tact_subscription:
				frappe.throw(_("TACT subscription is not enabled in IATA Settings"))
			
			if not iata_settings.tact_api_key:
				frappe.throw(_("TACT API key is not configured in IATA Settings"))
			
			# Build rate lookup request
			rate_params = {
				"origin": self.origin_port,
				"destination": self.destination_port,
				"weight": self.weight,
				"volume": self.volume,
				"chargeable_weight": self.chargeable
			}
			
			# Call TACT API (placeholder - actual implementation would call TACT API)
			# This is a placeholder for the actual TACT API integration
			frappe.msgprint(
				_("TACT rate lookup functionality requires TACT API integration. Please configure TACT API endpoint."),
				indicator="blue",
				title=_("TACT Integration")
			)
			
			return {
				"status": "info",
				"message": "TACT rate lookup requires API integration"
			}
			
		except Exception as e:
			frappe.log_error(f"TACT rate lookup error: {str(e)}", "Air Shipment - TACT Rate Lookup")
			frappe.throw(_("Error looking up TACT rate: {0}").format(str(e)))
	
	@frappe.whitelist()
	def create_eawb(self):
		"""Create e-AWB for this shipment"""
		try:
			if not self.eawb_enabled:
				frappe.throw(_("e-AWB is not enabled for this shipment"))
			
			# Validate required fields for e-AWB
			if not self.house_awb_no:
				frappe.throw(_("House AWB number is required to create e-AWB"))
			
			if not self.shipper or not self.consignee:
				frappe.throw(_("Shipper and Consignee are required to create e-AWB"))
			
			# Create e-AWB (placeholder - actual implementation would create e-AWB via IATA API)
			self.eawb_status = "Created"
			self.save()
			
			frappe.msgprint(_("e-AWB created successfully. Please sign and submit."), indicator="green")
			
			return {
				"status": "success",
				"message": "e-AWB created successfully",
				"eawb_status": self.eawb_status
			}
			
		except Exception as e:
			frappe.log_error(f"e-AWB creation error: {str(e)}", "Air Shipment - e-AWB Creation")
			frappe.throw(_("Error creating e-AWB: {0}").format(str(e)))
	
	@frappe.whitelist()
	def sign_eawb(self):
		"""Sign e-AWB digitally"""
		try:
			if not self.eawb_enabled:
				frappe.throw(_("e-AWB is not enabled for this shipment"))
			
			if self.eawb_status not in ["Created", "Not Created"]:
				frappe.throw(_("e-AWB must be in 'Created' status to sign"))
			
			# Generate digital signature (placeholder - actual implementation would use digital signature service)
			from frappe.utils import now_datetime
			import hashlib
			
			# Create a simple hash-based signature (in production, use proper digital signature)
			signature_data = f"{self.name}{self.house_awb_no}{now_datetime()}"
			digital_signature = hashlib.sha256(signature_data.encode()).hexdigest()
			
			self.eawb_digital_signature = digital_signature
			self.eawb_signed_date = now_datetime()
			self.eawb_signed_by = frappe.session.user
			self.eawb_status = "Signed"
			self.save()
			
			frappe.msgprint(_("e-AWB signed successfully"), indicator="green")
			
			return {
				"status": "success",
				"message": "e-AWB signed successfully",
				"eawb_status": self.eawb_status,
				"signed_date": self.eawb_signed_date
			}
			
		except Exception as e:
			frappe.log_error(f"e-AWB signing error: {str(e)}", "Air Shipment - e-AWB Signing")
			frappe.throw(_("Error signing e-AWB: {0}").format(str(e)))
	
	@frappe.whitelist()
	def update_tracking_status(self):
		"""Update tracking status from tracking provider"""
		try:
			if not self.real_time_tracking_enabled:
				frappe.throw(_("Real-time tracking is not enabled for this shipment"))
			
			if not self.tracking_provider or not self.tracking_number:
				frappe.throw(_("Tracking provider and tracking number are required"))
			
			# Update tracking status (placeholder - actual implementation would call tracking API)
			from frappe.utils import now_datetime
			
			# This is a placeholder for actual tracking API integration
			frappe.msgprint(
				_("Tracking status update requires tracking provider API integration."),
				indicator="blue",
				title=_("Tracking Integration")
			)
			
			self.last_tracking_update = now_datetime()
			self.save()
			
			return {
				"status": "info",
				"message": "Tracking update requires API integration",
				"last_update": self.last_tracking_update
			}
			
		except Exception as e:
			frappe.log_error(f"Tracking update error: {str(e)}", "Air Shipment - Tracking Update")
			frappe.throw(_("Error updating tracking status: {0}").format(str(e)))
	
	@frappe.whitelist()
	def recognize_revenue(self, recognition_date=None, method=None):
		"""Recognize revenue for this shipment"""
		try:
			if not self.revenue_amount:
				frappe.throw(_("Revenue amount is not set for this shipment"))
			
			from frappe.utils import getdate, today
			
			# Set recognition date
			if recognition_date:
				self.revenue_recognition_date = getdate(recognition_date)
			elif not self.revenue_recognition_date:
				self.revenue_recognition_date = today()
			
			# Set recognition method
			if method:
				self.revenue_recognition_method = method
			elif not self.revenue_recognition_method:
				# Default to "On Delivery" if not set
				self.revenue_recognition_method = "On Delivery"
			
			# Calculate recognized amount based on method
			if self.partial_revenue_enabled:
				# For partial revenue, use recognized_revenue_amount if set
				if not self.recognized_revenue_amount:
					# Default to full amount if not specified
					self.recognized_revenue_amount = self.revenue_amount
			else:
				# Full revenue recognition
				self.recognized_revenue_amount = self.revenue_amount
			
			self.save()
			
			frappe.msgprint(
				_("Revenue recognized: {0} on {1} using method: {2}").format(
					self.recognized_revenue_amount,
					self.revenue_recognition_date,
					self.revenue_recognition_method
				),
				indicator="green"
			)
			
			return {
				"status": "success",
				"message": "Revenue recognized successfully",
				"recognized_amount": self.recognized_revenue_amount,
				"recognition_date": self.revenue_recognition_date,
				"method": self.revenue_recognition_method
			}
			
		except Exception as e:
			frappe.log_error(f"Revenue recognition error: {str(e)}", "Air Shipment - Revenue Recognition")
			frappe.throw(_("Error recognizing revenue: {0}").format(str(e)))
	
	@frappe.whitelist()
	def create_sales_invoice(self):
		"""Create Sales Invoice for this shipment"""
		try:
			if not self.auto_billing_enabled:
				frappe.throw(_("Auto billing is not enabled for this shipment"))
			
			if not self.local_customer:
				frappe.throw(_("Local customer is required to create Sales Invoice"))
			
			if not self.company:
				frappe.throw(_("Company is required to create Sales Invoice"))
			
			# Check if invoice already exists
			if self.sales_invoice:
				frappe.throw(_("Sales Invoice {0} already exists for this shipment").format(self.sales_invoice))
			
			# Create Sales Invoice (placeholder - actual implementation would create proper invoice)
			# This is a placeholder for the actual billing automation
			frappe.msgprint(
				_("Sales Invoice creation requires billing automation integration. Please configure billing automation."),
				indicator="blue",
				title=_("Billing Automation")
			)
			
			return {
				"status": "info",
				"message": "Sales Invoice creation requires billing automation integration"
			}
			
		except Exception as e:
			frappe.log_error(f"Sales Invoice creation error: {str(e)}", "Air Shipment - Sales Invoice Creation")
			frappe.throw(_("Error creating Sales Invoice: {0}").format(str(e)))
	
	@frappe.whitelist()
	def populate_charges_from_sales_quote(self):
		"""Populate charges from Sales Quote Air Freight"""
		if not self.sales_quote:
			frappe.throw(_("Sales Quote is not set for this Air Shipment"))
		
		try:
			# Verify that the sales_quote exists
			if not frappe.db.exists("Sales Quote", self.sales_quote):
				frappe.msgprint(
					f"Sales Quote {self.sales_quote} does not exist",
					title="Error",
					indicator="red"
				)
				return
			
			# Clear existing charges
			self.set("charges", [])
			
			# Get Sales Quote Air Freight records
			sales_quote_air_freight_records = frappe.get_all(
				"Sales Quote Air Freight",
				filters={"parent": self.sales_quote, "parenttype": "Sales Quote"},
				fields=[
					"item_code",
					"item_name", 
					"calculation_method",
					"uom",
					"currency",
					"unit_rate",
					"unit_type",
					"minimum_quantity",
					"minimum_charge",
					"maximum_charge",
					"base_amount",
					"estimated_revenue"
				],
				order_by="idx"
			)
			
			if not sales_quote_air_freight_records:
				frappe.msgprint(
					f"No Air Freight charges found in Sales Quote: {self.sales_quote}",
					title="No Charges Found",
					indicator="orange"
				)
				return
			
			# Map and populate charges
			charges_added = 0
			for sqaf_record in sales_quote_air_freight_records:
				charge_row = self._map_sales_quote_air_freight_to_charge(sqaf_record)
				if charge_row:
					self.append("charges", charge_row)
					charges_added += 1
			
			if charges_added > 0:
				frappe.msgprint(
					f"Successfully populated {charges_added} charges from Sales Quote",
					title="Charges Updated",
					indicator="green"
				)
			
			return {
				"success": True,
				"message": f"Successfully populated {charges_added} charges",
				"charges_added": charges_added
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error populating charges from Sales Quote: {str(e)}",
				"Air Shipment - Populate Charges Error"
			)
			frappe.throw(_("Error populating charges: {0}").format(str(e)))
	
	def _map_sales_quote_air_freight_to_charge(self, sqaf_record):
		"""Map sales_quote_air_freight record to air_shipment_charges format"""
		try:
			# Get the item details to fetch additional required fields
			item_doc = frappe.get_doc("Item", sqaf_record.item_code)
			
			# Get default currency from system settings
			default_currency = frappe.get_system_settings("currency") or "USD"
			
			# Map unit_type to charge_basis
			unit_type_to_charge_basis = {
				"Weight": "Per kg",
				"Volume": "Per m³",
				"Package": "Per package",
				"Piece": "Per package",
				"Shipment": "Per shipment"
			}
			charge_basis = unit_type_to_charge_basis.get(sqaf_record.unit_type, "Fixed amount")
			
			# Get quantity based on charge basis
			quantity = 0
			if charge_basis == "Per kg":
				quantity = flt(self.weight) or 0
			elif charge_basis == "Per m³":
				quantity = flt(self.volume) or 0
			elif charge_basis == "Per package":
				# Get package count from Air Shipment if available
				if hasattr(self, 'packages') and self.packages:
					quantity = len(self.packages)
				else:
					quantity = 1
			elif charge_basis == "Per shipment":
				quantity = 1
			
			# Determine charge_type and charge_category from item or use defaults
			charge_type = "Other"
			charge_category = "Other"
			
			# Try to get charge type from item custom fields or item name
			if hasattr(item_doc, 'custom_charge_type'):
				charge_type = item_doc.custom_charge_type or "Other"
			if hasattr(item_doc, 'custom_charge_category'):
				charge_category = item_doc.custom_charge_category or "Other"
			
			# Map the fields from sales_quote_air_freight to air_shipment_charges
			charge_data = {
				"item_code": sqaf_record.item_code,
				"item_name": sqaf_record.item_name or item_doc.item_name,
				"charge_type": charge_type,
				"charge_category": charge_category,
				"charge_basis": charge_basis,
				"rate": sqaf_record.unit_rate or 0,
				"currency": sqaf_record.currency or default_currency,
				"quantity": quantity,
				"unit_of_measure": sqaf_record.uom or (charge_basis.replace("Per ", "").replace("kg", "kg").replace("m³", "m³")),
				"calculation_method": sqaf_record.calculation_method or "Manual",
				"billing_status": "Pending"
			}
			
			return charge_data
			
		except Exception as e:
			frappe.log_error(
				f"Error mapping sales quote air freight record: {str(e)}",
				"Air Shipment - Charge Mapping Error"
			)
			return None
	
	@frappe.whitelist()
	def calculate_total_charges(self):
		"""Calculate total charges for this Air Shipment"""
		total_charges = 0
		
		if hasattr(self, 'charges') and self.charges:
			for charge in self.charges:
				# Recalculate charge amount
				charge.calculate_charge_amount()
				total_charges += flt(charge.total_amount) or 0
		
		return {
			"total_charges": total_charges,
			"currency": self.get("charges")[0].currency if self.get("charges") else None
		}
	
	@frappe.whitelist()
	def recalculate_all_charges(self):
		"""Recalculate all charges based on current Air Shipment data"""
		if not hasattr(self, 'charges') or not self.charges:
			return {
				"success": False,
				"message": "No charges found to recalculate"
			}
		
		try:
			charges_recalculated = 0
			for charge in self.charges:
				# Update quantity based on charge basis
				if charge.charge_basis == "Per kg":
					charge.quantity = flt(self.weight) or 0
				elif charge.charge_basis == "Per m³":
					charge.quantity = flt(self.volume) or 0
				elif charge.charge_basis == "Per package":
					if hasattr(self, 'packages') and self.packages:
						charge.quantity = len(self.packages)
					else:
						charge.quantity = 1
				elif charge.charge_basis == "Per shipment":
					charge.quantity = 1
				
				# Recalculate charge amount
				charge.calculate_charge_amount()
				charges_recalculated += 1
			
			self.save()
			
			frappe.msgprint(
				f"Successfully recalculated {charges_recalculated} charges",
				title="Charges Recalculated",
				indicator="green"
			)
			
			return {
				"success": True,
				"message": f"Successfully recalculated {charges_recalculated} charges",
				"charges_recalculated": charges_recalculated
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error recalculating charges: {str(e)}",
				"Air Shipment - Recalculate Charges Error"
			)
			frappe.throw(_("Error recalculating charges: {0}").format(str(e)))
	
	def get_air_freight_settings(self):
		"""Get Air Freight Settings for the company"""
		if not self.company:
			return None
		
		try:
			from logistics.air_freight.doctype.air_freight_settings.air_freight_settings import AirFreightSettings
			return AirFreightSettings.get_settings(self.company)
		except Exception as e:
			frappe.log_error(f"Error getting Air Freight Settings: {str(e)}", "Air Shipment - Get Settings")
			return None
	
	def apply_settings_defaults(self):
		"""Apply default values from Air Freight Settings"""
		if hasattr(self, '_settings_applied'):
			return
		
		settings = self.get_air_freight_settings()
		if not settings:
			return
		
		# Apply general settings
		if not self.branch and settings.default_branch:
			self.branch = settings.default_branch
		if not self.cost_center and settings.default_cost_center:
			self.cost_center = settings.default_cost_center
		if not self.profit_center and settings.default_profit_center:
			self.profit_center = settings.default_profit_center
		if not self.incoterm and settings.default_incoterm:
			self.incoterm = settings.default_incoterm
		# Only set service_level if default_service_level exists as a valid Service Level Agreement record
		# Note: default_service_level is a Select field (text), but service_level is a Link field
		if not self.service_level and settings.default_service_level:
			# Check if the default_service_level value exists as a Service Level Agreement record
			if frappe.db.exists("Service Level Agreement", settings.default_service_level):
				self.service_level = settings.default_service_level
			# Otherwise, don't set it (leave it empty)
		
		# Apply location settings
		if not self.origin_port and settings.default_origin_port:
			self.origin_port = settings.default_origin_port
		if not self.destination_port and settings.default_destination_port:
			self.destination_port = settings.default_destination_port
		
		# Apply business settings
		if not self.airline and settings.default_airline:
			self.airline = settings.default_airline
		if not self.freight_agent and settings.default_freight_agent:
			self.freight_agent = settings.default_freight_agent
		if not self.house_type and settings.default_house_type:
			self.house_type = settings.default_house_type
		if not self.direction and settings.default_direction:
			self.direction = settings.default_direction
		if not self.release_type and settings.default_release_type:
			self.release_type = settings.default_release_type
		if not self.entry_type and settings.default_entry_type:
			self.entry_type = settings.default_entry_type
		
		# Apply document settings
		if not self.uld_type and settings.default_uld_type:
			self.uld_type = settings.default_uld_type
		
		# Mark as applied
		self._settings_applied = True
	
	@frappe.whitelist()
	def generate_house_awb_number(self):
		"""Generate House AWB number"""
		import random
		import string
		
		# Generate 11-digit AWB number (IATA standard)
		# Format: 3-digit prefix + 8-digit number
		prefix = "000"  # Default prefix, can be configured
		number = ''.join([str(random.randint(0, 9)) for _ in range(8)])
		awb_number = prefix + number
		
		self.house_awb_no = awb_number
		return awb_number
	
	@frappe.whitelist()
	def generate_master_awb_reference(self):
		"""Generate Master AWB reference"""
		# This would typically create or link to a Master Air Waybill
		# For now, just generate a reference number
		import random
		import string
		
		reference = f"MAWB-{self.name}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
		
		# Try to create or find a Master Air Waybill
		try:
			# Check if Master Air Waybill doctype exists
			if frappe.db.exists("DocType", "Master Air Waybill"):
				# Create a new Master Air Waybill
				mawb = frappe.new_doc("Master Air Waybill")
				mawb.airline = self.airline
				mawb.origin_airport = self.origin_port
				mawb.destination_airport = self.destination_port
				mawb.flight_date = self.etd
				mawb.insert(ignore_permissions=True)
				self.master_awb = mawb.name
				return mawb.name
		except Exception as e:
			frappe.log_error(f"Error generating Master AWB: {str(e)}", "Air Shipment - Generate Master AWB")
		
		return reference
	
	def validate_accounts(self):
		"""Validate accounting fields"""
		if not self.company:
			frappe.throw(_("Company is required"), title=_("Validation Error"))
		
		# Validate cost center belongs to company
		if self.cost_center:
			cost_center_company = frappe.get_cached_value("Cost Center", self.cost_center, "company")
			if cost_center_company and cost_center_company != self.company:
				frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
					self.cost_center, self.company), title=_("Validation Error"))
		
		# Validate profit center belongs to company
		if self.profit_center:
			profit_center_company = frappe.get_cached_value("Profit Center", self.profit_center, "company")
			if profit_center_company and profit_center_company != self.company:
				frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
					self.profit_center, self.company), title=_("Validation Error"))
		
		# Validate branch belongs to company
		if self.branch:
			branch_company = frappe.get_cached_value("Branch", self.branch, "company")
			if branch_company and branch_company != self.company:
				frappe.throw(_("Branch {0} does not belong to Company {1}").format(
					self.branch, self.company), title=_("Validation Error"))
	
	def create_job_costing_number_if_needed(self):
		"""Create Job Costing Number when document is first saved"""
		# Check settings for auto-create job costing
		settings = self.get_air_freight_settings()
		if settings and not settings.auto_create_job_costing:
			return
		
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


# Whitelisted API methods for client-side calls (module-level functions, same pattern as run sheet)

@frappe.whitelist()
def get_google_maps_api_key():
	"""
	Get the Google Maps API key for client-side use.
	This properly decrypts the Password field from Logistics Settings.
	
	Returns:
		dict: {
			"api_key": str or None,
			"has_key": bool
		}
	"""
	try:
		from frappe.utils.password import get_decrypted_password
		
		# Get the API key using get_decrypted_password for Password fields
		api_key = get_decrypted_password(
			"Logistics Settings",
			"Logistics Settings",
			"routing_google_api_key",
			raise_exception=False
		)
		
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
		frappe.log_error(f"Error getting Google Maps API key: {str(e)}", "Air Shipment - Get Google Maps API Key")
		return {
			"api_key": None,
			"has_key": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_google_route_polyline(waypoints):
	"""
	Get Google Directions API route polyline for waypoints.
	This returns an encoded polyline that can be used in Google Maps.
	
	Args:
		waypoints: String of "lat,lon|lat,lon|..." format
	
	Returns:
		dict: {
			"routes": list of route options with polyline, distance, duration,
			"success": bool
		}
	"""
	try:
		import requests
		from frappe.utils.password import get_decrypted_password
		
		# Get API key
		api_key = get_decrypted_password(
			"Logistics Settings",
			"Logistics Settings",
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
			points = waypoints.split('|')
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
			"alternatives": "true",
			"key": api_key
		}
		
		if waypoint_str:
			params["waypoints"] = waypoint_str
		
		# Call Directions API
		response = requests.get(url, params=params, timeout=10)
		data = response.json()
		
		status = data.get("status")
		
		# For air freight, if Directions API returns ZERO_RESULTS (common for air routes),
		# return coordinates for JavaScript to create a geodesic path
		if status == "ZERO_RESULTS":
			# Parse coordinates
			origin_parts = origin.split(',')
			dest_parts = destination.split(',')
			
			if len(origin_parts) == 2 and len(dest_parts) == 2:
				origin_lat = float(origin_parts[0])
				origin_lon = float(origin_parts[1])
				dest_lat = float(dest_parts[0])
				dest_lon = float(dest_parts[1])
				
				# Calculate great circle distance (Haversine formula)
				from math import radians, sin, cos, sqrt, atan2
				R = 6371  # Earth radius in km
				lat1, lon1 = radians(origin_lat), radians(origin_lon)
				lat2, lon2 = radians(dest_lat), radians(dest_lon)
				dlat = lat2 - lat1
				dlon = lon2 - lon1
				a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
				c = 2 * atan2(sqrt(a), sqrt(1-a))
				distance_km = R * c
				
				# Estimate duration (assuming average airspeed of 800 km/h)
				estimated_duration_min = (distance_km / 800) * 60
				
				# Return coordinates for JavaScript to create geodesic path
				# JavaScript will create a simple polyline with just start/end points
				# and set geodesic: true, which will automatically create a great circle route
				return {
					"success": True,
					"routes": [{
						"index": 0,
						"polyline": None,  # Will be created in JavaScript
						"origin": {"lat": origin_lat, "lon": origin_lon},
						"destination": {"lat": dest_lat, "lon": dest_lon},
						"distance_km": round(distance_km, 2),
						"duration_min": round(estimated_duration_min, 1),
						"summary": "Air Route (Great Circle)",
						"is_air_route": True
					}],
					"is_air_route": True
				}
		
		if status != "OK":
			error_msg = data.get("error_message", status)
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
		frappe.log_error(f"Error getting Google route polyline: {str(e)}", "Air Shipment - Get Google Route Polyline")
		return {
			"success": False,
			"error": str(e)
		}