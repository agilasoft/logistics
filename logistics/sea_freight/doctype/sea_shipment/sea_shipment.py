# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _

class SeaShipment(Document):
    def validate(self):
        """Validate Sea Shipment data"""
        # Normalize legacy house_type values
        self._normalize_house_type()
        self.validate_accounts()
        self.validate_required_fields()
        self.validate_dates()
        try:
            from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
            apply_measurement_uom_conversion_to_children(self, "packages", company=getattr(self, "company", None))
        except Exception:
            pass
        if not getattr(self, "override_volume_weight", False):
            self.aggregate_volume_from_packages()
        self.validate_weight_volume()
        self.validate_packages()
        self.validate_containers()
        self.validate_master_bill()
    
    def aggregate_volume_from_packages(self):
        """Set header volume from sum of package volumes, converted to m³."""
        if getattr(self, "override_volume_weight", False):
            return
        packages = getattr(self, "packages", []) or []
        if not packages:
            return
        try:
            from logistics.utils.measurements import convert_volume, get_aggregation_volume_uom, get_default_uoms
            target_volume_uom = get_aggregation_volume_uom(company=getattr(self, "company", None))
            if not target_volume_uom:
                return
            defaults = get_default_uoms(company=getattr(self, "company", None))
            target_normalized = str(target_volume_uom).strip().upper()
            total = 0
            for pkg in packages:
                pkg_vol = flt(getattr(pkg, "volume", 0) or 0)
                if pkg_vol <= 0:
                    continue
                pkg_volume_uom = getattr(pkg, "volume_uom", None) or defaults.get("volume")
                if not pkg_volume_uom:
                    continue
                if str(pkg_volume_uom).strip().upper() == target_normalized:
                    total += pkg_vol
                else:
                    total += convert_volume(
                        pkg_vol,
                        from_uom=pkg_volume_uom,
                        to_uom=target_volume_uom,
                        company=getattr(self, "company", None),
                    )
            if total > 0:
                self.volume = total
        except Exception:
            pass
    
    @frappe.whitelist()
    def aggregate_volume_from_packages_api(self):
        """Whitelisted API: aggregate volume from packages for client-side refresh when override is unchecked."""
        if not getattr(self, "override_volume_weight", False):
            self.aggregate_volume_from_packages()
        return {"volume": getattr(self, "volume", 0)}
    
    def after_insert(self):
        """Create Job Costing Number when document is first created. Defer to avoid 'not found' during conversion."""
        settings = frappe.get_single("Sea Freight Settings")
        if settings and not getattr(settings, "auto_create_job_costing", True):
            return
        frappe.enqueue(
            "logistics.sea_freight.doctype.sea_shipment.sea_shipment.create_job_costing_for_shipment",
            queue="default",
            shipment_name=self.name,
            company=self.company,
            branch=self.branch,
            cost_center=self.cost_center,
            profit_center=self.profit_center,
            booking_date=self.booking_date,
        )
    
    def before_save(self):
        """Calculate sustainability metrics before saving"""
        self.calculate_sustainability_metrics()
        self.check_delays()
        self.calculate_penalties()
    
    def after_submit(self):
        """Record sustainability metrics after shipment submission"""
        self.record_sustainability_metrics()
    
    def calculate_sustainability_metrics(self):
        """Calculate sustainability metrics for this sea shipment"""
        try:
            # Calculate carbon footprint based on weight and distance
            if hasattr(self, 'weight') and hasattr(self, 'origin_port') and hasattr(self, 'destination_port'):
                # Get distance between ports (simplified calculation)
                distance = self._calculate_port_distance(self.origin_port, self.destination_port)
                if distance and self.weight:
                    # Use sea freight emission factor
                    emission_factor = 0.01  # kg CO2e per ton-km for sea freight
                    carbon_footprint = (flt(self.weight) / 1000) * distance * emission_factor
                    self.estimated_carbon_footprint = carbon_footprint
                    
                    # Calculate fuel consumption estimate
                    fuel_consumption = self._calculate_fuel_consumption(distance, flt(self.weight))
                    self.estimated_fuel_consumption = fuel_consumption
                
        except Exception as e:
            frappe.log_error(f"Error calculating sustainability metrics for Sea Shipment {self.name}: {e}", "Sea Shipment Sustainability Error")
    
    def record_sustainability_metrics(self):
        """Record sustainability metrics in the centralized system"""
        try:
            from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
            
            result = integrate_sustainability(
                doctype=self.doctype,
                docname=self.name,
                module="Sea Freight",
                doc=self
            )
            
            if result.get("status") == "success":
                frappe.msgprint(_("Sustainability metrics recorded successfully"))
            elif result.get("status") == "skipped":
                # Don't show message if sustainability is not enabled
                pass
            else:
                frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Sea Shipment Sustainability Error")
                
        except Exception as e:
            frappe.log_error(f"Error recording sustainability metrics for Sea Shipment {self.name}: {e}", "Sea Shipment Sustainability Error")
    
    def _calculate_port_distance(self, origin: str, destination: str) -> float:
        """Calculate distance between ports (simplified)"""
        # This would typically use a geocoding service or database
        # For now, return a default distance based on common sea routes
        # Supports both UNLOCO codes (5 chars) and legacy 3-letter codes
        route_distances = {
            # UNLOCO codes (5 characters)
            ("USLAX", "SGSIN"): 8500,  # Los Angeles to Singapore
            ("HKHKG", "USLAX"): 12000,  # Hong Kong to Los Angeles
            ("NLRTM", "USNYC"): 5800,  # Rotterdam to New York
            ("SGSIN", "HKHKG"): 2600,  # Singapore to Hong Kong
            # Legacy 3-letter codes (for backward compatibility)
            ("LAX", "SIN"): 8500,
            ("HKG", "LAX"): 12000,
            ("ROT", "NYC"): 5800,
            ("SIN", "HKG"): 2600,
        }
        
        # Try to find exact match
        key = (origin, destination)
        if key in route_distances:
            return route_distances[key]
        
        # Try reverse match
        key = (destination, origin)
        if key in route_distances:
            return route_distances[key]
        
        # If UNLOCO codes, try to get coordinates and calculate distance
        if origin and destination and len(origin) == 5 and len(destination) == 5:
            try:
                origin_coords = self._get_unloco_coordinates(origin)
                dest_coords = self._get_unloco_coordinates(destination)
                
                if origin_coords and dest_coords:
                    # Calculate distance using Haversine formula
                    from math import radians, sin, cos, sqrt, atan2
                    lat1, lon1 = radians(origin_coords[0]), radians(origin_coords[1])
                    lat2, lon2 = radians(dest_coords[0]), radians(dest_coords[1])
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    
                    # Earth radius in km
                    R = 6371
                    distance = R * c
                    
                    return distance
            except Exception:
                pass  # Fall through to default
        
        # Default distance for sea freight
        return 5000.0  # Default 5000 km
    
    def _get_unloco_coordinates(self, unloco_code: str) -> tuple:
        """Get latitude and longitude for UNLOCO code"""
        try:
            coords = frappe.db.get_value("UNLOCO", unloco_code, ["latitude", "longitude"], as_dict=True)
            if coords and coords.latitude and coords.longitude:
                return (coords.latitude, coords.longitude)
        except Exception:
            pass
        return None
    
    def _calculate_fuel_consumption(self, distance: float, weight: float) -> float:
        """Calculate estimated fuel consumption for sea freight"""
        # Sea freight fuel consumption is typically 0.1-0.2 L per 100 km per ton
        fuel_rate = 0.15  # L per 100 km per ton
        return (fuel_rate * distance * (weight / 1000)) / 100.0
    
    def _normalize_house_type(self):
        """Normalize legacy house_type values to current options.
        Converts 'Direct' -> 'Standard House' and 'Consolidation' -> 'Co-load Master'.
        """
        if not hasattr(self, 'house_type') or not self.house_type:
            return
        normalization_map = {
            "Direct": "Standard House",
            "Consolidation": "Co-load Master",
        }
        if self.house_type in normalization_map:
            self.house_type = normalization_map[self.house_type]
    
    def validate_accounts(self):
        """Validate that cost center, profit center, and branch belong to the company"""
        if not self.company:
            return  # Skip validation if company is not set
        
        if self.cost_center:
            cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
            if cost_center_company and cost_center_company != self.company:
                frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                    self.cost_center, self.company
                ))
        
        if self.profit_center:
            # Check if Profit Center doctype has a company field before validating
            # Profit Center may not have a company field in this installation (e.g. logistics custom)
            try:
                profit_center_meta = frappe.get_meta("Profit Center")
                if profit_center_meta.has_field("company"):
                    profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
                    if profit_center_company and profit_center_company != self.company:
                        frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                            self.profit_center, self.company
                        ))
            except Exception as e:
                if "Unknown column" in str(e) or "1054" in str(e):
                    pass  # Field doesn't exist in database, skip validation
                else:
                    raise
        
        if self.branch:
            # Check if Branch doctype has a company field before validating
            try:
                branch_meta = frappe.get_meta("Branch")
                if branch_meta.has_field("company"):
                    branch_company = frappe.db.get_value("Branch", self.branch, "company")
                    if branch_company and branch_company != self.company:
                        frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                            self.branch, self.company
                        ))
            except Exception as e:
                if "Unknown column" in str(e) or "1054" in str(e):
                    pass  # Field doesn't exist in database, skip validation
                else:
                    raise
    
    def create_job_costing_number_if_needed(self):
        """Create Job Costing Number when document is first saved"""
        # Only create if job_costing_number is not set
        if not self.job_costing_number:
            # Check if this is the first save (no existing Job Costing Number)
            existing_job_ref = frappe.db.get_value("Job Costing Number", {
                "job_type": "Sea Shipment",
                "job_no": self.name
            })
            
            if not existing_job_ref:
                # Create Job Costing Number
                job_ref = frappe.new_doc("Job Costing Number")
                job_ref.job_type = "Sea Shipment"
                job_ref.job_no = self.name
                job_ref.company = self.company
                job_ref.branch = self.branch
                job_ref.cost_center = self.cost_center
                job_ref.profit_center = self.profit_center
                # Leave recognition_date blank - will be filled in separate function
                # Use sea shipment's booking_date instead
                job_ref.job_open_date = self.booking_date
                job_ref.insert(ignore_permissions=True)
                
                # Set the job_costing_number field
                self.job_costing_number = job_ref.name
                
                frappe.msgprint(_("Job Costing Number {0} created successfully").format(job_ref.name))

    def validate_required_fields(self):
        """Validate required fields for Sea Shipment"""
        if not self.booking_date:
            frappe.throw(_("Booking Date is required"))
        
        if not self.shipper:
            frappe.throw(_("Shipper is required"))
        
        if not self.consignee:
            frappe.throw(_("Consignee is required"))
        
        if not self.origin_port:
            frappe.throw(_("Origin Port is required"))
        
        if not self.destination_port:
            frappe.throw(_("Destination Port is required"))
        
        if not self.direction:
            frappe.throw(_("Direction is required"))
        
        if not self.local_customer:
            frappe.throw(_("Local Customer is required for billing"))
        
        # Shipping line should be required unless master_bill is set
        if not self.shipping_line and not self.master_bill:
            frappe.throw(_("Shipping Line is required (or link a Master Bill)"))
    
    def validate_dates(self):
        """Validate date logic for Sea Shipment"""
        from frappe.utils import getdate, today
        
        # Validate ETD is before ETA
        if self.etd and self.eta:
            if getdate(self.etd) >= getdate(self.eta):
                frappe.throw(_("ETD (Estimated Time of Departure) must be before ETA (Estimated Time of Arrival)"))
        
        # Warn if booking date is in the future
        if self.booking_date:
            if getdate(self.booking_date) > getdate(today()):
                frappe.msgprint(_("Booking date is in the future"), indicator="orange")
    
    def validate_weight_volume(self):
        """Validate weight and volume for Sea Shipment"""
        # Weight and volume should be positive numbers
        if self.weight and self.weight <= 0:
            frappe.throw(_("Weight must be greater than zero"))
        
        if self.volume and self.volume <= 0:
            frappe.throw(_("Volume must be greater than zero"))
        
        # Chargeable weight should be >= actual weight
        if self.weight and self.chargeable:
            if self.chargeable < self.weight:
                frappe.msgprint(_("Chargeable weight ({0}) is less than actual weight ({1})").format(
                    self.chargeable, self.weight
                ), indicator="orange")
    
    def validate_packages(self):
        """Validate packages for Sea Shipment"""
        # If packages exist, validate them
        if hasattr(self, 'packages') and self.packages:
            total_package_weight = sum(flt(p.weight or 0) for p in self.packages)
            total_package_volume = sum(flt(p.volume or 0) for p in self.packages)
            
            # Check if package weights match total weight (with tolerance)
            if self.weight and total_package_weight > 0:
                weight_diff = abs(total_package_weight - flt(self.weight))
                if weight_diff > 0.01:  # Allow 0.01 kg tolerance
                    frappe.msgprint(_("Package weights ({0} kg) do not match total weight ({1} kg)").format(
                        total_package_weight, self.weight
                    ), indicator="orange")
            
            # Check if package volumes match total volume (with tolerance)
            if self.volume and total_package_volume > 0:
                volume_diff = abs(total_package_volume - flt(self.volume))
                if volume_diff > 0.01:  # Allow 0.01 cbm tolerance
                    frappe.msgprint(_("Package volumes ({0} cbm) do not match total volume ({1} cbm)").format(
                        total_package_volume, self.volume
                    ), indicator="orange")
            
            # Validate each package has commodity
            for i, package in enumerate(self.packages, 1):
                if not package.commodity:
                    frappe.msgprint(_("Package {0}: Commodity is not specified").format(i), indicator="orange")
    
    def validate_containers(self):
        """Validate containers for Sea Shipment"""
        # If containers exist, validate them
        if hasattr(self, 'containers') and self.containers:
            # Validate container count matches total
            container_count = len(self.containers)
            if self.total_containers and container_count != flt(self.total_containers):
                frappe.msgprint(_("Container count ({0}) does not match total containers ({1})").format(
                    container_count, self.total_containers
                ), indicator="orange")
            
            # Validate each container has required fields
            for i, container in enumerate(self.containers, 1):
                if not container.type:
                    frappe.msgprint(_("Container {0}: Container Type is required").format(i), indicator="orange")
                
                # Validate container number format (basic check - should be alphanumeric)
                if container.container_no:
                    if len(container.container_no) < 4:
                        frappe.msgprint(_("Container {0}: Container Number should be at least 4 characters").format(i), 
                                     indicator="orange")
    
    def validate_master_bill(self):
        """Validate Master Bill if linked"""
        if self.master_bill:
            # Validate master bill exists
            if not frappe.db.exists("Master Bill", self.master_bill):
                frappe.throw(_("Master Bill {0} does not exist").format(self.master_bill))
            
            # Get master bill document
            master_bill = frappe.get_doc("Master Bill", self.master_bill)
            
            # Validate vessel and voyage match if both are set
            if self.vessel and master_bill.vessel:
                if self.vessel != master_bill.vessel:
                    frappe.msgprint(_("Vessel ({0}) does not match Master Bill vessel ({1})").format(
                        self.vessel, master_bill.vessel
                    ), indicator="orange")
            
            if self.voyage_no and master_bill.voyage_no:
                if self.voyage_no != master_bill.voyage_no:
                    frappe.msgprint(_("Voyage No ({0}) does not match Master Bill voyage ({1})").format(
                        self.voyage_no, master_bill.voyage_no
                    ), indicator="orange")
            
            # Validate ports match if both are set
            if self.origin_port and master_bill.origin_cto:
                # Note: Master Bill uses origin_cto, origin_cfs, origin_cy - we should check if any match
                pass  # This could be enhanced based on business requirements
            
            if self.destination_port and master_bill.destination_cto:
                # Note: Master Bill uses destination_cto, destination_cfs, destination_cy - we should check if any match
                pass  # This could be enhanced based on business requirements
            
            # Validate shipping line matches
            if self.shipping_line and master_bill.shipping_line:
                if self.shipping_line != master_bill.shipping_line:
                    frappe.msgprint(_("Shipping Line ({0}) does not match Master Bill shipping line ({1})").format(
                        self.shipping_line, master_bill.shipping_line
                    ), indicator="orange")

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
                    "job_type": "Sea Shipment",
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
                    if frappe.db.exists('Shipper', shipper):
                        shipper_doc = frappe.get_doc('Shipper', shipper)
                        shipper_code = getattr(shipper_doc, 'shipper_code', None) or getattr(shipper_doc, 'code', None) or ''
                        shipper_name = getattr(shipper_doc, 'shipper_name', None) or getattr(shipper_doc, 'name', None) or shipper
                        shipper_addr = getattr(shipper_doc, 'address', None)
                        if shipper_addr:
                            shipper_address = shipper_addr
                    else:
                        shipper_name = shipper
                    
                    # Get address if linked separately
                    shipper_addr_field = getattr(self, 'shipper_address', None)
                    if shipper_addr_field:
                        try:
                            addr_doc = frappe.get_doc('Address', shipper_addr_field)
                            addr_line1 = getattr(addr_doc, 'address_line1', None) or ''
                            city = getattr(addr_doc, 'city', None) or ''
                            shipper_address = f"{addr_line1}, {city}".strip(', ')
                        except Exception:
                            pass
                except Exception:
                    shipper_name = shipper
            
            # Get consignee details
            consignee_code = ''
            consignee_name = 'Not specified'
            consignee_address = ''
            consignee = getattr(self, 'consignee', None)
            if consignee:
                try:
                    if frappe.db.exists('Consignee', consignee):
                        consignee_doc = frappe.get_doc('Consignee', consignee)
                        consignee_code = getattr(consignee_doc, 'consignee_code', None) or getattr(consignee_doc, 'code', None) or ''
                        consignee_name = getattr(consignee_doc, 'consignee_name', None) or getattr(consignee_doc, 'name', None) or consignee
                        consignee_addr = getattr(consignee_doc, 'address', None)
                        if consignee_addr:
                            consignee_address = consignee_addr
                    else:
                        consignee_name = consignee
                    
                    # Get address if linked separately
                    consignee_addr_field = getattr(self, 'consignee_address', None)
                    if consignee_addr_field:
                        try:
                            addr_doc = frappe.get_doc('Address', consignee_addr_field)
                            addr_line1 = getattr(addr_doc, 'address_line1', None) or ''
                            city = getattr(addr_doc, 'city', None) or ''
                            consignee_address = f"{addr_line1}, {city}".strip(', ')
                        except Exception:
                            pass
                except Exception:
                    consignee_name = consignee
            
            # Get vessel details
            vessel = getattr(self, 'vessel', None) or 'Not specified'
            voyage_no = getattr(self, 'voyage_no', None) or 'Not specified'
            shipping_line = getattr(self, 'shipping_line', None) or 'Not specified'
            
            # Get port names from UNLOCO
            origin_port_name = self.origin_port
            dest_port_name = self.destination_port
            try:
                if frappe.db.exists('UNLOCO', self.origin_port):
                    origin_unloco = frappe.get_doc('UNLOCO', self.origin_port)
                    origin_port_name = getattr(origin_unloco, 'location_name', None) or self.origin_port
                if frappe.db.exists('UNLOCO', self.destination_port):
                    dest_unloco = frappe.get_doc('UNLOCO', self.destination_port)
                    dest_port_name = getattr(dest_unloco, 'location_name', None) or self.destination_port
            except Exception:
                pass
            
            # Build HTML header
            html = f"""
		<div class="job-header">
			<div class="header-main">
				<div class="header-column">
					<div class="header-section">
						<label class="section-label">ORIGIN</label>
						<div class="location-name">{origin_port_name or 'Origin'}</div>
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
						<div class="location-name">{dest_port_name or 'Destination'}</div>
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
					<label>Shipping Line:</label>
					<span>{shipping_line}</span>
				</div>
				<div class="detail-item">
					<label>Vessel:</label>
					<span>{vessel}</span>
				</div>
				<div class="detail-item">
					<label>Voyage:</label>
					<span>{voyage_no}</span>
				</div>
				<div class="detail-item">
					<label>Incoterm:</label>
					<span>{incoterm}</span>
				</div>
			</div>
		</div>
		
		<div class="milestone-container">
			<div class="milestone-cards">
				<div class="milestone-list">
		"""
            
            # Build milestone cards
            for milestone in milestones:
                milestone_info = milestone_details.get(milestone.milestone, {})
                
                # Get base status
                status = milestone.status or 'Planned'
                status_class = status.lower().replace(' ', '-')
                
                # Check if milestone is delayed
                if (milestone.planned_end and 
                    ((not milestone.actual_end and milestone.planned_end < frappe.utils.now_datetime()) or
                     (milestone.actual_end and milestone.actual_end > milestone.planned_end))):
                    
                    if not milestone.actual_end or milestone.actual_end <= milestone.planned_end:
                        status = 'Delayed'
                        status_class = 'delayed'
                
                # Determine status badges
                status_badges = []
                original_status = milestone.status or 'Planned'
                
                if (milestone.actual_end and milestone.actual_end > milestone.planned_end and 
                    original_status.lower() in ['completed', 'finished', 'done']):
                    status_badges = [
                        '<span class="status-badge completed">Completed</span>',
                        '<span class="status-badge delayed">Delayed</span>'
                    ]
                else:
                    status_badges = [f'<span class="status-badge {status_class}">{status}</span>']
                
                # Build action icons
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
            
            # Build map container and closing HTML
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
								<strong>Origin:</strong> {origin_port_name}<br>
								<strong>Destination:</strong> {dest_port_name}
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
		}}
		
		.party-label {{
			font-size: 11px;
			color: #6c757d;
			font-weight: 600;
			margin-bottom: 2px;
		}}
		
		.party-code {{
			font-size: 10px;
			color: #999;
			margin-bottom: 2px;
		}}
		
		.party-name {{
			font-size: 13px;
			font-weight: 500;
			color: #333;
		}}
		
		.party-address {{
			font-size: 11px;
			color: #666;
			margin-top: 2px;
		}}
		
		.section-label {{
			font-size: 10px;
			color: #6c757d;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 0.5px;
			margin-bottom: 4px;
		}}
		
		.location-name {{
			font-size: 16px;
			font-weight: 600;
			color: #007bff;
		}}
		
		.header-details {{
			display: flex;
			gap: 20px;
			margin-top: 10px;
			padding-top: 10px;
			border-top: 1px solid #f0f0f0;
		}}
		
		.detail-item {{
			display: flex;
			flex-direction: column;
			gap: 2px;
		}}
		
		.detail-item label {{
			font-size: 10px;
			color: #6c757d;
			font-weight: 600;
		}}
		
		.detail-item span {{
			font-size: 12px;
			color: #333;
		}}
		
		.milestone-container {{
			display: flex;
			flex-direction: column;
			gap: 20px;
		}}
		
		.milestone-cards {{
			background: #ffffff;
			border: 1px solid #e0e0e0;
			border-radius: 6px;
			padding: 16px;
		}}
		
		.milestone-list {{
			display: flex;
			flex-direction: column;
			gap: 12px;
		}}
		
		.milestone-card {{
			background: #f8f9fa;
			border: 1px solid #e0e0e0;
			border-radius: 4px;
			padding: 12px;
			transition: all 0.2s;
		}}
		
		.milestone-card:hover {{
			box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
		}}
		
		.milestone-actions {{
			display: flex;
			gap: 8px;
			align-items: center;
		}}
		
		.status-badges {{
			display: flex;
			gap: 4px;
		}}
		
		.status-badge {{
			padding: 2px 8px;
			border-radius: 3px;
			font-size: 10px;
			font-weight: 600;
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
			color: #383d41;
		}}
		
		.status-badge.started {{
			background: #cce5ff;
			color: #004085;
		}}
		
		.action-icons {{
			display: flex;
			gap: 8px;
		}}
		
		.action-icon {{
			font-size: 16px;
			cursor: pointer;
			transition: transform 0.2s;
		}}
		
		.action-icon:hover {{
			transform: scale(1.2);
		}}
		
		.milestone-dates {{
			display: flex;
			flex-direction: column;
			gap: 4px;
		}}
		
		.date-row {{
			display: flex;
			justify-content: space-between;
			align-items: center;
		}}
		
		.date-row label {{
			font-size: 11px;
			color: #6c757d;
			font-weight: 600;
		}}
		
		.date-row span {{
			font-size: 12px;
			color: #333;
		}}
		
		@media (max-width: 768px) {{
			.milestone-container {{
				flex-direction: column;
			}}
			
			.milestone-cards {{
				width: 100%;
			}}
		}}
		</style>
		
		<script>
		// Milestone action functions
		function captureActualStart(milestoneId) {{
			console.log('Capture Actual Start for milestone:', milestoneId);
			frappe.prompt([
				{{fieldname: 'actual_start', fieldtype: 'Datetime', label: 'Actual Start', reqd: 1, default: frappe.datetime.now_datetime()}}
			], function(values) {{
				frappe.call({{
					method: 'frappe.client.set_value',
					args: {{
						doctype: 'Job Milestone',
						name: milestoneId,
						fieldname: 'actual_start',
						value: values.actual_start
					}},
					callback: function(r) {{
						// Refresh the milestone HTML
						frappe.ui.form.get_cur_frm().call('get_milestone_html').then(function(result) {{
							if (result.message) {{
								frappe.ui.form.get_cur_frm().get_field('milestone_html').$wrapper.html(result.message);
							}}
						}});
					}}
				}});
			}});
		}}
		
		function captureActualEnd(milestoneId) {{
			console.log('Capture Actual End for milestone:', milestoneId);
			frappe.prompt([
				{{fieldname: 'actual_end', fieldtype: 'Datetime', label: 'Actual End', reqd: 1, default: frappe.datetime.now_datetime()}}
			], function(values) {{
				frappe.call({{
					method: 'frappe.client.set_value',
					args: {{
						doctype: 'Job Milestone',
						name: milestoneId,
						fieldname: 'actual_end',
						value: values.actual_end
					}},
					callback: function(r) {{
						// Refresh the milestone HTML
						frappe.ui.form.get_cur_frm().call('get_milestone_html').then(function(result) {{
							if (result.message) {{
								frappe.ui.form.get_cur_frm().get_field('milestone_html').$wrapper.html(result.message);
							}}
						}});
					}}
				}});
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
            frappe.log_error(f"Error in get_milestone_html: {str(e)}", "Sea Shipment - Milestone HTML")
            return "<div class='alert alert-danger'>Error loading milestone view. Please check the error log.</div>"
    
    def format_datetime(self, dt):
        """Format datetime for display"""
        if not dt:
            return None
        try:
            from frappe.utils import format_datetime
            return format_datetime(dt)
        except Exception:
            return str(dt)
    
    def check_delays(self):
        """Check for delays in milestones and update delay tracking fields"""
        try:
            from frappe.utils import now_datetime
            
            # Get all milestones for this shipment
            milestones = frappe.get_all(
                "Job Milestone",
                filters={
                    "job_type": "Sea Shipment",
                    "job_number": self.name
                },
                fields=["name", "milestone", "status", "planned_end", "actual_end"]
            )
            
            delay_count = 0
            has_delays = False
            
            for milestone in milestones:
                if milestone.planned_end:
                    planned_end = frappe.utils.get_datetime(milestone.planned_end)
                    now = now_datetime()
                    
                    # Check if milestone is delayed
                    if not milestone.actual_end:
                        # Milestone not completed yet - check if planned end has passed
                        if planned_end < now:
                            delay_count += 1
                            has_delays = True
                    else:
                        # Milestone completed - check if it was completed late
                        actual_end = frappe.utils.get_datetime(milestone.actual_end)
                        if actual_end > planned_end:
                            delay_count += 1
                            has_delays = True
            
            # Update delay tracking fields
            self.has_delays = 1 if has_delays else 0
            self.delay_count = delay_count
            self.last_delay_check = now_datetime()
            
            # Send alert if delays detected and alert not sent yet
            settings = frappe.get_single("Sea Freight Settings")
            if has_delays and not self.delay_alert_sent and getattr(settings, "enable_delay_alerts", 1):
                self.send_delay_alert()
                self.delay_alert_sent = 1
                
        except Exception as e:
            frappe.log_error(f"Error checking delays for Sea Shipment {self.name}: {str(e)}", "Sea Shipment Delay Check")
    
    def calculate_penalties(self):
        """Calculate detention and demurrage penalties"""
        try:
            from frappe.utils import now_datetime, getdate
            from datetime import timedelta
            
            # Get settings for free time and penalty rates
            settings = frappe.get_single("Sea Freight Settings")
            free_time_days = getattr(settings, "default_free_time_days", 7)  # Default 7 days free time
            
            # Calculate based on container return date or discharge date
            # For now, use a simplified calculation based on discharge date
            discharge_date = None
            
            # Try to get discharge date from milestone or status
            if self.shipping_status == "Discharged from Vessel":
                # Get discharge milestone
                discharge_milestone = frappe.get_all(
                    "Job Milestone",
                    filters={
                        "job_type": "Sea Shipment",
                        "job_number": self.name,
                        "milestone": "SF-DISCHARGED"
                    },
                    fields=["actual_end"],
                    limit=1
                )
                
                if discharge_milestone and discharge_milestone[0].actual_end:
                    discharge_date = getdate(discharge_milestone[0].actual_end)
            
            if not discharge_date:
                # Fallback: use ETA if available
                if self.eta:
                    discharge_date = getdate(self.eta)
                else:
                    return  # Cannot calculate without discharge date
            
            today = getdate(now_datetime())
            days_since_discharge = (today - discharge_date).days
            
            # Calculate free time
            self.free_time_days = free_time_days
            
            # Calculate detention (container held beyond free time)
            if days_since_discharge > free_time_days:
                detention_days = days_since_discharge - free_time_days
                self.detention_days = detention_days
                self.has_penalties = 1
            else:
                self.detention_days = 0
            
            # Calculate demurrage (container at port beyond free time)
            # For sea freight, demurrage is typically calculated from gate-in date
            gate_in_date = None
            gate_in_milestone = frappe.get_all(
                "Job Milestone",
                filters={
                    "job_type": "Sea Shipment",
                    "job_number": self.name,
                    "milestone": "SF-GATE-IN"
                },
                fields=["actual_end"],
                limit=1
            )
            
            if gate_in_milestone and gate_in_milestone[0].actual_end:
                gate_in_date = getdate(gate_in_milestone[0].actual_end)
            
            if gate_in_date:
                days_at_port = (today - gate_in_date).days
                if days_at_port > free_time_days:
                    demurrage_days = days_at_port - free_time_days
                    self.demurrage_days = demurrage_days
                    self.has_penalties = 1
                else:
                    self.demurrage_days = 0
            
            # Calculate estimated penalty amount
            self.estimated_penalty_amount = self._calculate_penalty_amount()
            
            # Update last penalty check
            self.last_penalty_check = now_datetime()
            
            # Send alert if penalties detected and alert not sent yet
            if self.has_penalties and not self.penalty_alert_sent and getattr(settings, "enable_penalty_alerts", 1):
                self.send_penalty_alert()
                self.penalty_alert_sent = 1
                
        except Exception as e:
            frappe.log_error(f"Error calculating penalties for Sea Shipment {self.name}: {str(e)}", "Sea Shipment Penalty Calculation")
    
    def _calculate_penalty_amount(self):
        """Calculate estimated penalty amount based on detention and demurrage days"""
        try:
            settings = frappe.get_single("Sea Freight Settings")
            
            # Get penalty rates from settings (if available)
            detention_rate = getattr(settings, "detention_rate_per_day", 0) or 0
            demurrage_rate = getattr(settings, "demurrage_rate_per_day", 0) or 0
            
            # Calculate total penalty
            detention_amount = flt(self.detention_days or 0) * flt(detention_rate)
            demurrage_amount = flt(self.demurrage_days or 0) * flt(demurrage_rate)
            
            return detention_amount + demurrage_amount
            
        except Exception as e:
            frappe.log_error(f"Error calculating penalty amount: {str(e)}")
            return 0
    
    def send_delay_alert(self):
        """Send delay alert notification"""
        try:
            if not self.has_delays:
                return
            
            # Create notification
            notification_message = _("Sea Shipment {0} has {1} delayed milestone(s)").format(
                self.name, self.delay_count
            )
            
            # Get users to notify
            users_to_notify = self._get_users_to_notify()
            
            for user in users_to_notify:
                frappe.publish_realtime(
                    event='sea_shipment_delayed',
                    message={
                        'shipment': self.name,
                        'delay_count': self.delay_count,
                        'message': notification_message
                    },
                    user=user
                )
                
                # Create notification document
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Sea Shipment",
                    "document_name": self.name,
                    "subject": _("Delay Alert: Sea Shipment {0}").format(self.name),
                    "email_content": notification_message
                }).insert(ignore_permissions=True)
            
            frappe.msgprint(_("Delay alert sent for {0} delayed milestone(s)").format(self.delay_count), 
                          indicator="orange")
            
        except Exception as e:
            frappe.log_error(f"Error sending delay alert: {str(e)}", "Sea Shipment Delay Alert")
    
    def send_penalty_alert(self):
        """Send penalty alert notification"""
        try:
            if not self.has_penalties:
                return
            
            # Create notification
            notification_message = _("Sea Shipment {0} has penalties: Detention {1} days, Demurrage {2} days. Estimated amount: {3}").format(
                self.name,
                self.detention_days or 0,
                self.demurrage_days or 0,
                frappe.utils.fmt_money(self.estimated_penalty_amount or 0)
            )
            
            # Get users to notify
            users_to_notify = self._get_users_to_notify()
            
            for user in users_to_notify:
                frappe.publish_realtime(
                    event='sea_shipment_penalty',
                    message={
                        'shipment': self.name,
                        'detention_days': self.detention_days or 0,
                        'demurrage_days': self.demurrage_days or 0,
                        'estimated_amount': self.estimated_penalty_amount or 0,
                        'message': notification_message
                    },
                    user=user
                )
                
                # Create notification document
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Sea Shipment",
                    "document_name": self.name,
                    "subject": _("Penalty Alert: Sea Shipment {0}").format(self.name),
                    "email_content": notification_message
                }).insert(ignore_permissions=True)
            
            frappe.msgprint(_("Penalty alert sent. Estimated penalty: {0}").format(
                frappe.utils.fmt_money(self.estimated_penalty_amount or 0)
            ), indicator="red")
            
        except Exception as e:
            frappe.log_error(f"Error sending penalty alert: {str(e)}", "Sea Shipment Penalty Alert")
    
    def _get_users_to_notify(self):
        """Get list of users who should be notified about this shipment"""
        users = []
        
        try:
            # Add owner and modified_by
            if self.owner:
                users.append(self.owner)
            if self.modified_by:
                users.append(self.modified_by)
            
            # Add users from local_customer
            if self.local_customer:
                customer_doc = frappe.get_doc("Customer", self.local_customer)
                # Get users linked to customer (if any)
                # This could be extended based on business requirements
            
            # Add users from handling branch/department
            if self.handling_branch:
                # Get users from branch (if any user assignment exists)
                pass
            
            # Remove duplicates
            users = list(set(users))
            
        except Exception as e:
            frappe.log_error(f"Error getting users to notify: {str(e)}")
        
        return users
    
    def _send_impending_penalty_alert(self, days_since_discharge, free_time_days):
        """Send alert for impending penalty"""
        try:
            remaining_days = free_time_days - days_since_discharge
            
            notification_message = _("Sea Shipment {0} is approaching penalty threshold. {1} days remaining before penalties apply.").format(
                self.name, remaining_days
            )
            
            users_to_notify = self._get_users_to_notify()
            
            for user in users_to_notify:
                frappe.publish_realtime(
                    event='sea_shipment_impending_penalty',
                    message={
                        'shipment': self.name,
                        'remaining_days': remaining_days,
                        'message': notification_message
                    },
                    user=user
                )
                
                # Create notification document
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Sea Shipment",
                    "document_name": self.name,
                    "subject": _("Impending Penalty Alert: Sea Shipment {0}").format(self.name),
                    "email_content": notification_message
                }).insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error sending impending penalty alert: {str(e)}", "Sea Shipment Impending Penalty Alert")

@frappe.whitelist()
def create_sales_invoice(shipment_name, posting_date, customer, tax_category=None, invoice_type=None):
    """Create Sales Invoice from Sea Shipment"""
    if not shipment_name:
        frappe.throw(_("Sea Shipment name is required."))
    
    shipment = frappe.get_doc('Sea Shipment', shipment_name)
    
    if shipment.docstatus != 1:
        frappe.throw(_("Sea Shipment must be submitted to create Sales Invoice."))

    # Fetch naming series from the Invoice Type doctype
    naming_series = None
    if invoice_type:
        naming_series = frappe.db.get_value("Invoice Type", invoice_type, "naming_series")

    invoice = frappe.new_doc('Sales Invoice')
    invoice.customer = customer
    invoice.company = shipment.company
    invoice.posting_date = posting_date
    invoice.tax_category = tax_category or None
    invoice.naming_series = naming_series or None
    invoice.invoice_type = invoice_type or None  # Optional: standard field if exists
    invoice.custom_invoice_type = invoice_type or None  # Custom field explicitly filled
    
    # Add accounting fields from Sea Shipment
    if getattr(shipment, "branch", None):
        invoice.branch = shipment.branch
    if getattr(shipment, "cost_center", None):
        invoice.cost_center = shipment.cost_center
    if getattr(shipment, "profit_center", None):
        invoice.profit_center = shipment.profit_center
    
    # Add reference to Job Costing Number if it exists
    if getattr(shipment, "job_costing_number", None):
        invoice.job_costing_number = shipment.job_costing_number
    
    # Add reference in remarks
    base_remarks = invoice.remarks or ""
    note = _("Auto-created from Sea Shipment {0}").format(shipment.name)
    invoice.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    # Add items from charges
    for charge in shipment.charges:
        if charge.bill_to == customer and charge.invoice_type == invoice_type:
            item_payload = {
                'item_code': charge.charge_item,
                'item_name': charge.charge_name or charge.charge_item,
                'description': charge.charge_description,
                'qty': 1,
                'rate': charge.selling_amount or 0,
                'currency': charge.selling_currency,
                'item_tax_template': charge.item_tax_template or None
            }
            
            # Add accounting fields to Sales Invoice Item
            if getattr(shipment, "cost_center", None):
                item_payload['cost_center'] = shipment.cost_center
            if getattr(shipment, "profit_center", None):
                item_payload['profit_center'] = shipment.profit_center
            # Link to shipment for Recognition Engine and lifecycle tracking
            si_item_meta = frappe.get_meta("Sales Invoice Item")
            if si_item_meta.get_field("reference_doctype") and si_item_meta.get_field("reference_name"):
                item_payload["reference_doctype"] = "Sea Shipment"
                item_payload["reference_name"] = shipment.name
            
            invoice.append('items', item_payload)

    if not invoice.items:
        frappe.throw(_("No matching charges found for the selected customer and invoice type."))

    invoice.set_missing_values()
    invoice.insert(ignore_permissions=True)
    
    # Update Sea Shipment with Sales Invoice reference and lifecycle
    from frappe.utils import today
    updates = {"sales_invoice": invoice.name, "date_sales_invoice_requested": today()}
    for k, v in updates.items():
        if frappe.get_meta("Sea Shipment").get_field(k):
            frappe.db.set_value("Sea Shipment", shipment.name, k, v, update_modified=False)
    
    return invoice

@frappe.whitelist()
def compute_chargeable(self):
    weight = self.weight or 0
    volume = self.volume or 0

    # Use direction to determine conversion factor
    if self.direction == "Domestic":
        volume_weight = volume * 333  # Philippine domestic standard
    else:
        volume_weight = volume * 1000  # International standard

    self.chargeable = max(weight, volume_weight)

@frappe.whitelist()
def populate_charges_from_sales_quote(self):
	"""Populate charges from Sales Quote Sea Freight"""
	if not self.sales_quote:
		frappe.throw(_("Sales Quote is not set for this Sea Shipment"))
	
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
		
		# Get Sales Quote Sea Freight records
		sales_quote_sea_freight_records = frappe.get_all(
			"Sales Quote Sea Freight",
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
		
		if not sales_quote_sea_freight_records:
			frappe.msgprint(
				f"No Sea Freight charges found in Sales Quote: {self.sales_quote}",
				title="No Charges Found",
				indicator="orange"
			)
			return
		
		# Import the mapping function from Sales Quote
		from logistics.pricing_center.doctype.sales_quote.sales_quote import _map_sales_quote_sea_freight_to_charge
		
		# Map and populate charges
		charges_added = 0
		for sqsf_record in sales_quote_sea_freight_records:
			charge_row = _map_sales_quote_sea_freight_to_charge(sqsf_record, self)
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
			"Sea Shipment - Populate Charges Error"
		)
		frappe.throw(_("Error populating charges: {0}").format(str(e)))

def create_job_costing_for_shipment(
	shipment_name,
	company,
	branch=None,
	cost_center=None,
	profit_center=None,
	booking_date=None,
):
	"""Deferred: create Job Costing Number for Sea Shipment after commit (avoids 'not found' during conversion)."""
	if not frappe.db.exists("Sea Shipment", shipment_name):
		return
	if frappe.db.get_value("Sea Shipment", shipment_name, "job_costing_number"):
		return
	if frappe.db.get_value("Job Costing Number", {"job_type": "Sea Shipment", "job_no": shipment_name}):
		return
	job_ref = frappe.new_doc("Job Costing Number")
	job_ref.job_type = "Sea Shipment"
	job_ref.job_no = shipment_name
	job_ref.company = company
	job_ref.branch = branch
	job_ref.cost_center = cost_center
	job_ref.profit_center = profit_center
	job_ref.job_open_date = booking_date
	job_ref.insert(ignore_permissions=True)
	frappe.db.set_value("Sea Shipment", shipment_name, "job_costing_number", job_ref.name)
	frappe.db.commit()
