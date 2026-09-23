# logistics/transport/constraint_validator.py

"""
Constraint Validator Module

Validates vehicles against various constraints during transport planning:
- Time window constraints
- Address day availability
- Truck ban constraints by Constraint Type (Area / Route / Time / Weight / Vehicle Type / Plate Coding)
- Ad-hoc transport factors
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, get_time, add_to_date


def _combine_datetime(date_val, time_val):
	"""Combine date + time into datetime (frappe.utils.combine_datetime is unavailable)."""
	from datetime import datetime, time as time_type, timedelta

	d = getdate(date_val)
	t = get_time(time_val)
	if isinstance(t, timedelta):
		total = int(t.total_seconds())
		t = time_type(total // 3600, (total % 3600) // 60, total % 60)
	return datetime.combine(d, t)


def validate_vehicle_constraints(
    vehicle: Dict[str, Any],
    leg: Dict[str, Any],
    scheduled_datetime: datetime,
    debug: Optional[List[str]] = None
) -> Tuple[bool, Optional[str], int, List[Dict[str, Any]]]:
    """
    Validate vehicle against all applicable constraints.
    
    Args:
        vehicle: Vehicle dictionary with vehicle_type, avg_speed, license_plate_number, etc.
        leg: Transport Leg dictionary with pick_address, drop_address, pick_mode, drop_mode, etc.
        scheduled_datetime: Scheduled datetime for the operation
        debug: Optional list to append debug messages
    
    Returns:
        (is_valid, reason_if_invalid, delay_minutes, alternative_routes)
        - is_valid: True if vehicle can be assigned, False if blocked
        - reason_if_invalid: Error message if blocked, warning message if delays
        - delay_minutes: Total estimated delay in minutes (0 if no delays)
        - alternative_routes: List of alternative route suggestions
    """
    debug = debug or []
    
    # Check Transport Settings to see which constraints are enabled
    try:
        settings = frappe.get_single("Transport Settings")
    except Exception:
        # If Transport Settings doesn't exist or can't be loaded, skip constraint checking
        debug.append("Transport Settings not available, skipping constraint checks")
        return True, None, 0, []
    
    # Master switch check
    if not settings.get("enable_constraint_system", False):
        debug.append("Constraint system disabled in Transport Settings")
        return True, None, 0, []
    
    # Get constraint checking mode
    checking_mode = settings.get("constraint_checking_mode", "Strict")
    if checking_mode == "Disabled":
        debug.append("Constraint checking mode is Disabled")
        return True, None, 0, []
    
    violations = []
    warnings = []
    total_delay_minutes = 0
    alternative_routes = []
    
    # Check each constraint type only if enabled in settings
    # 1. Time window constraints
    if settings.get("enable_time_window_constraints", False):
        is_valid, reason, delay = check_time_window_constraints(vehicle, leg, scheduled_datetime, debug)
        if not is_valid:
            if checking_mode == "Strict":
                return False, reason, delay or 0, []
            warnings.append(reason or "Time window constraint violation")
        if delay:
            total_delay_minutes += delay
    
    # 2. Address day availability
    if settings.get("enable_address_day_availability", False):
        is_valid, reason = check_address_day_availability(leg, scheduled_datetime, debug)
        if not is_valid:
            if checking_mode == "Strict":
                return False, reason, 0, []
            warnings.append(reason or "Address day availability constraint violation")
    
    # 2.5. PEZA address classification
    if settings.get("enable_peza_validation", False):
        is_valid, reason = check_peza_address_classification(leg, debug)
        if not is_valid:
            if checking_mode == "Strict":
                return False, reason, 0, []
            warnings.append(reason or "PEZA address classification constraint violation")
    
    # 3. Plate number coding — deprecated (use Truck Ban Constraint → Plate Coding)
    # Legacy Plate Coding Rule is no longer enforced; plate coding is checked under truck bans.

    # 4. Truck bans (includes optional plate-coding child rows)
    if settings.get("enable_truck_ban_constraints", False):
        is_valid, reason = check_truck_ban_constraints(
            vehicle, scheduled_datetime, 
            leg.get("pick_address"), leg.get("drop_address"), debug
        )
        if not is_valid:
            if checking_mode == "Strict":
                return False, reason, 0, []
            warnings.append(reason or "Truck ban constraint violation")
    
    # 5. Ad-hoc factors
    if settings.get("enable_adhoc_factors", False):
        is_valid, reason, delay, alternatives = check_adhoc_factors(
            scheduled_datetime,
            leg.get("pick_address"),
            leg.get("drop_address"),
            vehicle.get("vehicle_type"), debug
        )
        if not is_valid:
            delay_threshold = settings.get("adhoc_factor_delay_threshold_minutes", 60)
            if delay and delay > delay_threshold:
                if checking_mode == "Strict":
                    return False, reason, delay or 0, alternatives or []
                warnings.append(reason or "Ad-hoc factor blocking route")
            else:
                total_delay_minutes += delay or 0
        if alternatives:
            alternative_routes.extend(alternatives)
    
    # Return result based on checking mode
    if checking_mode == "Strict" and violations:
        return False, "; ".join(violations), total_delay_minutes, alternative_routes
    elif warnings:
        # In Warning mode, return True but include warnings in debug
        debug.extend(warnings)
        return True, None, total_delay_minutes, alternative_routes
    
    return True, None, total_delay_minutes, alternative_routes


def check_time_window_constraints(
    vehicle: Dict[str, Any],
    leg: Dict[str, Any],
    scheduled_datetime: datetime,
    debug: Optional[List[str]] = None
) -> Tuple[bool, Optional[str], Optional[float]]:
    """Check if vehicle can meet pick/drop time windows"""
    debug = debug or []
    
    try:
        
        # Get vehicle average speed
        vehicle_avg_speed = vehicle.get("avg_speed", 0) or 0
        if not vehicle_avg_speed or vehicle_avg_speed <= 0:
            settings = frappe.get_single("Transport Settings")
            vehicle_avg_speed = settings.get("routing_default_avg_speed_kmh", 50) or 50
        
        # Get cargo volume and weight
        cargo_weight_kg = leg.get("cargo_weight_kg", 0) or 0
        cargo_volume_m3 = calculate_leg_volume(leg)
        
        # Calculate loading and unloading times
        loading_time_minutes = calculate_loading_time(leg, cargo_weight_kg, cargo_volume_m3)
        unloading_time_minutes = calculate_unloading_time(leg, cargo_weight_kg, cargo_volume_m3)
        
        # Get time windows (prefer Address schedule for the scheduled weekday)
        pick_window_start = leg.get("pick_window_start")
        pick_window_end = leg.get("pick_window_end")
        drop_window_start = leg.get("drop_window_start")
        drop_window_end = leg.get("drop_window_end")
        leg_date = leg.get("date") or leg.get("run_date")
        if not leg_date and scheduled_datetime:
            leg_date = getdate(scheduled_datetime)

        from logistics.transport.address_windows import resolve_address_window

        pick_address = leg.get("pick_address")
        if pick_address and leg_date:
            resolved_pick = resolve_address_window(pick_address, "Pick", leg_date)
            if resolved_pick:
                pick_window_start, pick_window_end = resolved_pick

        drop_address = leg.get("drop_address")
        if drop_address and leg_date:
            resolved_drop = resolve_address_window(drop_address, "Drop", leg_date)
            if resolved_drop:
                drop_window_start, drop_window_end = resolved_drop
        
        if not leg_date:
            debug.append("No date specified for leg, skipping time window check")
            return True, None, 0
        
        # Calculate travel time to pick location
        if pick_address:
            distance_to_pick = get_distance(None, pick_address, leg.get("routing_provider")) or leg.get("distance_km", 0)
            travel_to_pick_minutes = calculate_travel_time_minutes(distance_to_pick, vehicle_avg_speed)
        else:
            travel_to_pick_minutes = 0
        
        # Estimated pick arrival
        estimated_pick_arrival = add_to_date(scheduled_datetime, minutes=travel_to_pick_minutes)
        
        # Check pick window
        if pick_window_start and pick_window_end:
            pick_window_start_dt = _combine_datetime(leg_date, pick_window_start)
            pick_window_end_dt = _combine_datetime(leg_date, pick_window_end)
            
            if not (pick_window_start_dt <= estimated_pick_arrival <= pick_window_end_dt):
                return False, f"Cannot meet pick window. Estimated arrival: {estimated_pick_arrival}, Window: {pick_window_start_dt} - {pick_window_end_dt}", None
            
            # Pick departure = arrival + loading time
            estimated_pick_departure = add_to_date(estimated_pick_arrival, minutes=loading_time_minutes)
            
            # Calculate travel time from pick to drop
            if drop_address:
                distance_pick_to_drop = get_distance(pick_address, drop_address, leg.get("routing_provider")) or leg.get("distance_km", 0)
                travel_pick_to_drop_minutes = calculate_travel_time_minutes(distance_pick_to_drop, vehicle_avg_speed)
            else:
                travel_pick_to_drop_minutes = 0
            
            # Estimated drop arrival
            estimated_drop_arrival = add_to_date(estimated_pick_departure, minutes=travel_pick_to_drop_minutes)
            
            # Estimated drop completion = arrival + unloading time
            estimated_drop_completion = add_to_date(estimated_drop_arrival, minutes=unloading_time_minutes)
            
            # Check drop window
            if drop_window_start and drop_window_end:
                drop_window_start_dt = _combine_datetime(leg_date, drop_window_start)
                drop_window_end_dt = _combine_datetime(leg_date, drop_window_end)
                
                if not (drop_window_start_dt <= estimated_drop_completion <= drop_window_end_dt):
                    return False, f"Cannot meet drop window. Estimated completion: {estimated_drop_completion}, Window: {drop_window_start_dt} - {drop_window_end_dt}", None
        
        return True, None, 0
        
    except Exception as e:
        debug.append(f"Error checking time window constraints: {str(e)}")
        return True, None, 0  # Fail gracefully


def check_address_day_availability(
    leg: Dict[str, Any],
    scheduled_datetime: datetime,
    debug: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """Check if address allows pick/drop operations on scheduled day"""
    debug = debug or []
    
    try:
        day_of_week = scheduled_datetime.strftime("%A").lower()
        day_name = scheduled_datetime.strftime("%A")
        
        # Check pick address
        pick_address = leg.get("pick_address")
        if pick_address:
            pick_available, pick_reason = _check_address_day_availability(
                pick_address, day_of_week, day_name, "pick", debug, scheduled_datetime
            )
            if not pick_available:
                return False, pick_reason
        
        # Check drop address
        drop_address = leg.get("drop_address")
        if drop_address:
            drop_available, drop_reason = _check_address_day_availability(
                drop_address, day_of_week, day_name, "drop", debug, scheduled_datetime
            )
            if not drop_available:
                return False, drop_reason
        
        return True, None
        
    except Exception as e:
        debug.append(f"Error checking address day availability: {str(e)}")
        return True, None  # Fail gracefully


def check_peza_address_classification(
    leg: Dict[str, Any],
    debug: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """Check if addresses have PEZA/non-PEZA classification set"""
    debug = debug or []
    
    try:
        # Check pick address
        pick_address = leg.get("pick_address")
        if pick_address:
            if not frappe.db.exists("Address", pick_address):
                return True, None  # Address doesn't exist, skip validation
            
            address_doc = frappe.get_doc("Address", pick_address)
            if address_doc.meta.has_field("custom_peza_classification"):
                peza_classification = getattr(address_doc, "custom_peza_classification", None)
                if not peza_classification:
                    return False, f"Pick address {pick_address} must have PEZA classification set (PEZA or Non-PEZA)"
        
        # Check drop address
        drop_address = leg.get("drop_address")
        if drop_address:
            if not frappe.db.exists("Address", drop_address):
                return True, None  # Address doesn't exist, skip validation
            
            address_doc = frappe.get_doc("Address", drop_address)
            if address_doc.meta.has_field("custom_peza_classification"):
                peza_classification = getattr(address_doc, "custom_peza_classification", None)
                if not peza_classification:
                    return False, f"Drop address {drop_address} must have PEZA classification set (PEZA or Non-PEZA)"
        
        return True, None
        
    except Exception as e:
        debug.append(f"Error checking PEZA address classification: {str(e)}")
        return True, None  # Fail gracefully


def _check_address_day_availability(
    address_name: str,
    day_of_week: str,
    day_name: str,
    operation_type: str,
    debug: Optional[List[str]] = None,
    scheduled_datetime: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """Helper to check if address allows operation on specific day via Pick / Drop Windows table."""
    debug = debug or []
    
    try:
        if not frappe.db.exists("Address", address_name):
            return True, None  # Address doesn't exist, assume available

        from logistics.transport.address_windows import (
            SCHEDULE_DOCTYPE,
            SCHEDULE_FIELD,
            is_operation_allowed,
        )

        # Table-only schedule: if DocType + field exist, row presence is availability
        if frappe.db.exists("DocType", SCHEDULE_DOCTYPE):
            address_meta = frappe.get_meta("Address")
            if address_meta.has_field(SCHEDULE_FIELD):
                if not scheduled_datetime:
                    return True, None
                if not is_operation_allowed(address_name, operation_type, scheduled_datetime):
                    return (
                        False,
                        f"Address {address_name} does not allow {operation_type} operations on {day_name}",
                    )
                return True, None

        # Legacy fallback only when schedule field is not installed
        field_name = f"custom_{operation_type}_{day_of_week}"
        address_doc = frappe.get_doc("Address", address_name)
        if not address_doc.meta.has_field(field_name):
            return True, None  # Field doesn't exist, assume available
        
        is_available = getattr(address_doc, field_name, False)
        
        if not is_available:
            return False, f"Address {address_name} does not allow {operation_type} operations on {day_name}"
        
        return True, None
        
    except Exception as e:
        debug.append(f"Error checking address {address_name} day availability: {str(e)}")
        return True, None  # Fail gracefully


def check_plate_coding_constraints(
    vehicle: Dict[str, Any],
    scheduled_datetime: datetime,
    address: Optional[str] = None,
    debug: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """Deprecated: Plate Coding Rule is no longer enforced.

    Configure plate coding on Truck Ban Constraint → Plate Coding instead.
    Kept as a no-op for any remaining callers.
    """
    debug = debug or []
    debug.append("check_plate_coding_constraints is deprecated; use Truck Ban Constraint plate coding")
    return True, None


def _as_time(value):
    """Normalize Frappe Time / timedelta / time to datetime.time for comparison."""
    from datetime import time as time_type

    if value is None:
        return None
    t = get_time(value)
    if isinstance(t, timedelta):
        total = int(t.total_seconds()) % (24 * 3600)
        return time_type(total // 3600, (total % 3600) // 60, total % 60)
    return t


def _plate_last_digit(plate_number: Optional[str]) -> Optional[int]:
    if not plate_number:
        return None
    plate_number = str(plate_number).strip()
    if not plate_number or not plate_number[-1].isdigit():
        return None
    return int(plate_number[-1])


def _vehicle_type_exempt_from_plate_coding(vehicle_type: Optional[str]) -> bool:
    if not vehicle_type:
        return False
    try:
        return bool(frappe.db.get_value("Vehicle Type", vehicle_type, "exempt_from_plate_coding"))
    except Exception:
        return False


def _plate_coding_matches(
    coding_rows: List[Dict[str, Any]],
    day_of_week: str,
    last_digit: int,
    scheduled_time,
) -> bool:
    sched_t = _as_time(scheduled_time)
    for row in coding_rows:
        if row.get("restricted_digit") != last_digit:
            continue
        if row.get("restricted_day") and row.get("restricted_day") != day_of_week:
            continue
        ban_start = _as_time(row.get("ban_start"))
        ban_end = _as_time(row.get("ban_end"))
        if ban_start is None or ban_end is None or sched_t is None:
            continue
        if ban_start <= sched_t <= ban_end:
            return True
    return False


def _truck_ban_parent_time_matches(ban: Dict[str, Any], scheduled_time) -> bool:
    """True when parent All Day / Start / End Time covers scheduled_time."""
    if ban.get("all_day"):
        return True
    start_t = _as_time(ban.get("start_time"))
    end_t = _as_time(ban.get("end_time"))
    if start_t is None or end_t is None or scheduled_time is None:
        return False
    return start_t <= scheduled_time <= end_t


def _truck_ban_address_hit(
    restricted_addresses: List[Dict[str, Any]],
    pick_address: Optional[str],
    drop_address: Optional[str],
) -> Optional[Tuple[str, str]]:
    """Return (addr_type, address) on first restricted-address match."""
    addresses_to_check = []
    if pick_address:
        addresses_to_check.append(("pick", pick_address))
    if drop_address:
        addresses_to_check.append(("drop", drop_address))
    for addr_type, address in addresses_to_check:
        for ra in restricted_addresses:
            if ra.get("address") == address:
                return addr_type, address
    return None


def _truck_ban_route_hit(
    restricted_routes: List[Dict[str, Any]],
    pick_address: Optional[str],
    drop_address: Optional[str],
) -> Optional[str]:
    """Return route display name on first restricted-route match."""
    if not pick_address or not drop_address:
        return None
    for route in restricted_routes:
        if (
            route.get("from_address") == pick_address
            and route.get("to_address") == drop_address
        ) or (
            route.get("from_address") == drop_address
            and route.get("to_address") == pick_address
        ):
            return (
                route.get("route_name")
                or f"{route.get('from_address')} to {route.get('to_address')}"
            )
    return None


def check_truck_ban_constraints(
    vehicle: Dict[str, Any],
    scheduled_datetime: datetime,
    pick_address: Optional[str] = None,
    drop_address: Optional[str] = None,
    debug: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """Check if vehicle is banned from area/route at scheduled time.

    Enforcement is gated by ``constraint_type`` when set:
    Area / Route / Time / Weight / Vehicle Type / Plate Coding.
    Legacy bans without ``constraint_type`` keep the previous hybrid behaviour.
    """
    debug = debug or []

    try:
        scheduled_date = scheduled_datetime.date()
        scheduled_time = scheduled_datetime.time()
        day_of_week = scheduled_datetime.strftime("%A")
        plate_number = vehicle.get("license_plate_number")
        last_digit = _plate_last_digit(plate_number)

        filters = [
            ["is_active", "=", 1],
            ["start_date", "<=", scheduled_date],
            ["end_date", ">=", scheduled_date],
        ]

        truck_bans = frappe.get_all(
            "Truck Ban Constraint",
            filters=filters,
            fields=[
                "name",
                "ban_name",
                "constraint_type",
                "all_day",
                "start_time",
                "end_time",
                "min_vehicle_weight_restriction",
            ],
            limit_page_length=100,
        )

        for ban in truck_bans:
            ban_name = ban.get("ban_name") or ban.name
            ctype = (ban.get("constraint_type") or "").strip()

            restricted_vehicle_types = frappe.get_all(
                "Truck Ban Constraint Vehicle Types",
                filters={"parent": ban.name},
                pluck="vehicle_type",
                limit_page_length=100,
            )

            # Vehicle-type filter: required gate for Vehicle Type Ban; optional elsewhere
            # except Weight-Based Ban (field hidden for that type).
            if ctype == "Weight-Based Ban":
                pass
            elif ctype == "Vehicle Type Ban":
                if not restricted_vehicle_types:
                    continue
                if vehicle.get("vehicle_type") not in restricted_vehicle_types:
                    continue
            elif restricted_vehicle_types and vehicle.get("vehicle_type") not in restricted_vehicle_types:
                continue

            coding_rows = frappe.get_all(
                "Truck Ban Plate Coding",
                filters={"parent": ban.name},
                fields=["restricted_digit", "restricted_day", "ban_start", "ban_end"],
                limit_page_length=500,
            ) if (not ctype or ctype == "Plate Coding") else []

            coding_matched = False
            if ctype == "Plate Coding" or (not ctype and coding_rows):
                if _vehicle_type_exempt_from_plate_coding(vehicle.get("vehicle_type")):
                    debug.append(f"Vehicle type exempt from plate coding for ban {ban_name}")
                    continue
                if last_digit is None:
                    continue
                if not coding_rows or not _plate_coding_matches(
                    coding_rows, day_of_week, last_digit, scheduled_time
                ):
                    continue
                coding_matched = True
            elif ctype in (
                "Area Ban",
                "Route Ban",
                "Time-Based Ban",
                "Weight-Based Ban",
                "Vehicle Type Ban",
            ):
                if not _truck_ban_parent_time_matches(ban, scheduled_time):
                    continue
            else:
                # Legacy untyped: parent time when no coding rows
                if not _truck_ban_parent_time_matches(ban, scheduled_time):
                    continue

            if ctype == "Plate Coding":
                return False, (
                    f"Vehicle plate {plate_number} (last digit {last_digit}) is restricted "
                    f"on {day_of_week} by constraint {ban_name}"
                )

            if ctype == "Weight-Based Ban":
                limit = ban.get("min_vehicle_weight_restriction")
                if not limit:
                    continue
                vehicle_weight = vehicle.get("capacity_weight", 0) or 0
                if vehicle_weight >= limit:
                    return False, (
                        f"Vehicle weight {vehicle_weight}kg exceeds ban limit "
                        f"{limit}kg for constraint {ban_name}"
                    )
                continue

            if ctype == "Time-Based Ban":
                return False, (
                    f"Vehicle is blocked by time-based constraint {ban_name} "
                    f"at {scheduled_datetime}"
                )

            if ctype == "Vehicle Type Ban":
                return False, (
                    f"Vehicle type {vehicle.get('vehicle_type')} is restricted "
                    f"by constraint {ban_name}"
                )

            restricted_addresses = frappe.get_all(
                "Truck Ban Restricted Addresses",
                filters={"parent": ban.name},
                fields=["address", "radius_km"],
                limit_page_length=100,
            ) if (not ctype or ctype == "Area Ban") else []

            restricted_routes = frappe.get_all(
                "Truck Ban Restricted Routes",
                filters={"parent": ban.name},
                fields=["from_address", "to_address", "route_name"],
                limit_page_length=100,
            ) if (not ctype or ctype == "Route Ban") else []

            if ctype == "Area Ban":
                hit = _truck_ban_address_hit(restricted_addresses, pick_address, drop_address)
                if hit:
                    addr_type, address = hit
                    return False, (
                        f"{addr_type.capitalize()} address {address} is in banned area "
                        f"for constraint {ban_name}"
                    )
                continue

            if ctype == "Route Ban":
                route_name = _truck_ban_route_hit(restricted_routes, pick_address, drop_address)
                if route_name:
                    return False, f"Route {route_name} is banned by constraint {ban_name}"
                continue

            # ---- Legacy untyped bans (no constraint_type) ----
            if ban.get("min_vehicle_weight_restriction"):
                vehicle_weight = vehicle.get("capacity_weight", 0) or 0
                if vehicle_weight >= ban.get("min_vehicle_weight_restriction"):
                    return False, (
                        f"Vehicle weight {vehicle_weight}kg exceeds ban limit "
                        f"{ban.get('min_vehicle_weight_restriction')}kg for constraint {ban_name}"
                    )

            location_hit = False
            hit = _truck_ban_address_hit(restricted_addresses, pick_address, drop_address)
            if hit:
                location_hit = True
                addr_type, address = hit
                if coding_matched:
                    return False, (
                        f"Vehicle plate {plate_number} (last digit {last_digit}) is restricted "
                        f"on {day_of_week} at {addr_type} address {address} by constraint {ban_name}"
                    )
                return False, (
                    f"{addr_type.capitalize()} address {address} is in banned area "
                    f"for constraint {ban_name}"
                )

            route_name = _truck_ban_route_hit(restricted_routes, pick_address, drop_address)
            if route_name:
                location_hit = True
                if coding_matched:
                    return False, (
                        f"Vehicle plate {plate_number} (last digit {last_digit}) is restricted "
                        f"on {day_of_week} on route {route_name} by constraint {ban_name}"
                    )
                return False, f"Route {route_name} is banned by constraint {ban_name}"

            if coding_matched and not restricted_addresses and not restricted_routes:
                return False, (
                    f"Vehicle plate {plate_number} (last digit {last_digit}) is restricted "
                    f"on {day_of_week} by constraint {ban_name}"
                )

            if coding_matched and (restricted_addresses or restricted_routes) and not location_hit:
                continue

        return True, None

    except Exception as e:
        debug.append(f"Error checking truck ban constraints: {str(e)}")
        return True, None  # Fail gracefully


def check_adhoc_factors(
    scheduled_datetime: datetime,
    pick_address: Optional[str] = None,
    drop_address: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    debug: Optional[List[str]] = None
) -> Tuple[bool, Optional[str], Optional[float], List[Dict[str, Any]]]:
    """Check for ad-hoc factors affecting transport"""
    debug = debug or []
    
    try:
        scheduled_date = scheduled_datetime.date()
        scheduled_time = scheduled_datetime.time()
        
        # Build filters for active factors
        filters = [
            ["is_active", "=", 1],
            ["start_datetime", "<=", scheduled_datetime],
            ["end_datetime", ">=", scheduled_datetime]
        ]
        
        # Get active ad-hoc factors
        factors = frappe.get_all(
            "Ad-Hoc Transport Factor",
            filters=filters,
            fields=["name", "factor_name", "factor_type", "severity", "impact_type",
                    "estimated_delay_minutes", "restricted_vehicle_types"],
            limit_page_length=100
        )
        
        total_delay = 0
        blocking_factors = []
        alternative_routes = []
        
        for factor in factors:
            # Check vehicle type restriction
            if factor.get("restricted_vehicle_types"):
                # Get restricted types from child table
                restricted_types = frappe.get_all(
                    "Ad-Hoc Factor Vehicle Types",
                    filters={"parent": factor.name},
                    pluck="vehicle_type",
                    limit_page_length=100
                )
                if vehicle_type and vehicle_type in restricted_types:
                    continue  # Factor doesn't apply to this vehicle type
            
            # Check affected addresses
            affected_addresses = frappe.get_all(
                "Ad-Hoc Factor Affected Addresses",
                filters={"parent": factor.name},
                fields=["address", "radius_km", "impact_type"],
                limit_page_length=100
            )
            
            # Check if pick or drop address is affected
            for aa in affected_addresses:
                if pick_address and (aa.get("address") == pick_address or 
                    (aa.get("radius_km", 0) > 0 and _is_within_radius(pick_address, aa.get("address"), aa.get("radius_km", 0)))):
                    impact_type = aa.get("impact_type") or factor.get("impact_type")
                    if impact_type == "Complete Blockage":
                        blocking_factors.append(f"{factor.get('factor_name')} - Pick address blocked")
                    elif impact_type == "Partial Blockage":
                        delay = factor.get("estimated_delay_minutes", 0) or 0
                        total_delay += delay
                        blocking_factors.append(f"{factor.get('factor_name')} - Pick address partially blocked (delay: {delay} min)")
                
                if drop_address and (aa.get("address") == drop_address or 
                    (aa.get("radius_km", 0) > 0 and _is_within_radius(drop_address, aa.get("address"), aa.get("radius_km", 0)))):
                    impact_type = aa.get("impact_type") or factor.get("impact_type")
                    if impact_type == "Complete Blockage":
                        blocking_factors.append(f"{factor.get('factor_name')} - Drop address blocked")
                    elif impact_type == "Partial Blockage":
                        delay = factor.get("estimated_delay_minutes", 0) or 0
                        total_delay += delay
                        blocking_factors.append(f"{factor.get('factor_name')} - Drop address partially blocked (delay: {delay} min)")
            
            # Check affected routes
            if pick_address and drop_address:
                affected_routes = frappe.get_all(
                    "Ad-Hoc Factor Affected Routes",
                    filters={"parent": factor.name},
                    fields=["from_address", "to_address", "impact_type"],
                    limit_page_length=100
                )
                
                for route in affected_routes:
                    if (route.get("from_address") == pick_address and route.get("to_address") == drop_address) or \
                       (route.get("from_address") == drop_address and route.get("to_address") == pick_address):
                        impact_type = route.get("impact_type") or factor.get("impact_type")
                        if impact_type == "Complete Blockage":
                            blocking_factors.append(f"{factor.get('factor_name')} - Route blocked")
                        else:
                            delay = factor.get("estimated_delay_minutes", 0) or 0
                            total_delay += delay
        
        if blocking_factors:
            reason = "; ".join(blocking_factors)
            return False, reason, total_delay if total_delay > 0 else None, alternative_routes
        
        if total_delay > 0:
            return True, None, total_delay, alternative_routes
        
        return True, None, 0, []
        
    except Exception as e:
        debug.append(f"Error checking ad-hoc factors: {str(e)}")
        return True, None, 0, []  # Fail gracefully


def _is_within_radius(address1: str, address2: str, radius_km: float) -> bool:
    """Check if address1 is within radius_km of address2"""
    # TODO: Implement actual distance calculation
    # For now, return False (conservative approach)
    return False


# Helper functions for time calculations

def calculate_travel_time_minutes(distance_km: float, avg_speed_kmh: float) -> float:
    """Calculate travel time in minutes from distance and average speed"""
    if not distance_km or distance_km <= 0:
        return 0
    if not avg_speed_kmh or avg_speed_kmh <= 0:
        return 0
    
    # Time in hours = distance / speed
    # Convert to minutes
    return (distance_km / avg_speed_kmh) * 60


def get_distance(from_address: Optional[str], to_address: Optional[str], routing_provider: Optional[str] = None) -> Optional[float]:
    """
    Get distance between two addresses.
    Priority:
    1. Use routing provider if available
    2. Use cached distance if available
    3. Use existing distance_km from leg if available
    4. Calculate using routing service
    """
    # TODO: Integrate with existing routing infrastructure
    # For now, return None to use existing distance_km from leg
    return None


def calculate_leg_volume(leg: Dict[str, Any]) -> float:
    """Calculate total volume from leg packages or use leg field"""
    # Try to get volume from leg field first
    if leg.get("cargo_volume_m3"):
        return float(leg.get("cargo_volume_m3"))
    
    # Otherwise, sum from packages
    volume = 0.0
    transport_job = leg.get("transport_job")
    if transport_job:
        try:
            packages = frappe.get_all(
                "Transport Job Package",
                filters={"parent": transport_job},
                fields=["volume", "length", "width", "height"],
                limit_page_length=1000
            )
            for pkg in packages:
                if pkg.get("volume"):
                    volume += float(pkg.get("volume"))
                elif all([pkg.get("length"), pkg.get("width"), pkg.get("height")]):
                    # Calculate volume: length × width × height (convert to m³)
                    # Assuming dimensions are in cm, convert to m³
                    vol_cm3 = float(pkg.get("length")) * float(pkg.get("width")) * float(pkg.get("height"))
                    vol_m3 = vol_cm3 / 1000000  # Convert cm³ to m³
                    volume += vol_m3
        except Exception:
            pass
    
    return volume


def calculate_loading_time(leg: Dict[str, Any], cargo_weight_kg: float, cargo_volume_m3: float) -> float:
    """
    Calculate loading time based on Pick Mode settings, volume, and weight.
    
    Priority:
    1. Address custom settings (if override specified)
    2. Pick Mode settings
    3. Transport Settings defaults
    """
    pick_mode = leg.get("pick_mode")
    pick_address = leg.get("pick_address")
    
    # Check if address has custom settings
    if pick_address:
        try:
            address_doc = frappe.get_doc("Address", pick_address)
            if hasattr(address_doc, "custom_loading_time_calculation_method") and \
               address_doc.custom_loading_time_calculation_method and \
               address_doc.custom_loading_time_calculation_method != "Use Pick Mode Settings":
                return _calculate_time_from_settings(
                    address_doc,
                    cargo_weight_kg,
                    cargo_volume_m3,
                    prefix="custom_loading_time",
                    operation="loading"
                )
        except Exception:
            pass
    
    # Use Pick Mode settings
    if pick_mode:
        try:
            mode_doc = frappe.get_doc("Pick and Drop Mode", pick_mode)
            return _calculate_time_from_settings(
                mode_doc,
                cargo_weight_kg,
                cargo_volume_m3,
                prefix="loading_time",
                operation="loading"
            )
        except Exception:
            pass
    
    # Fallback to Transport Settings defaults
    return _calculate_time_from_defaults(
        cargo_weight_kg,
        cargo_volume_m3,
        operation="loading"
    )


def calculate_unloading_time(leg: Dict[str, Any], cargo_weight_kg: float, cargo_volume_m3: float) -> float:
    """
    Calculate unloading time based on Drop Mode settings, volume, and weight.
    
    Priority:
    1. Address custom settings (if override specified)
    2. Drop Mode settings
    3. Transport Settings defaults
    """
    drop_mode = leg.get("drop_mode")
    drop_address = leg.get("drop_address")
    
    # Check if address has custom settings
    if drop_address:
        try:
            address_doc = frappe.get_doc("Address", drop_address)
            if hasattr(address_doc, "custom_unloading_time_calculation_method") and \
               address_doc.custom_unloading_time_calculation_method and \
               address_doc.custom_unloading_time_calculation_method != "Use Drop Mode Settings":
                return _calculate_time_from_settings(
                    address_doc,
                    cargo_weight_kg,
                    cargo_volume_m3,
                    prefix="custom_unloading_time",
                    operation="unloading"
                )
        except Exception:
            pass
    
    # Use Drop Mode settings
    if drop_mode:
        try:
            mode_doc = frappe.get_doc("Pick and Drop Mode", drop_mode)
            return _calculate_time_from_settings(
                mode_doc,
                cargo_weight_kg,
                cargo_volume_m3,
                prefix="unloading_time",
                operation="unloading"
            )
        except Exception:
            pass
    
    # Fallback to Transport Settings defaults
    return _calculate_time_from_defaults(
        cargo_weight_kg,
        cargo_volume_m3,
        operation="unloading"
    )


def _calculate_time_from_settings(doc, cargo_weight_kg: float, cargo_volume_m3: float, 
                                  prefix: str, operation: str) -> float:
    """Calculate time from document settings (Mode or Address)"""
    # Get base time
    base_time = getattr(doc, f"{prefix}_base_{operation}_minutes", None) or \
                getattr(doc, f"base_{operation}_time_minutes", None) or 0
    
    # Get calculation method
    method = getattr(doc, f"{prefix}_calculation_method", None) or \
             getattr(doc, f"{operation}_time_calculation_method", None) or \
             "Volume-Based"
    
    calculated_time = float(base_time) if base_time else 0.0
    
    if method == "Fixed Time":
        # Just use base time
        pass
    elif method == "Volume-Based":
        time_per_volume = getattr(doc, f"{prefix}_per_volume_m3", None) or \
                         getattr(doc, f"{operation}_time_per_volume_m3", None) or 0
        calculated_time += cargo_volume_m3 * float(time_per_volume)
    elif method == "Weight-Based":
        time_per_weight = getattr(doc, f"{prefix}_per_weight_kg", None) or \
                         getattr(doc, f"{operation}_time_per_weight_kg", None) or 0
        # time_per_weight is per 100kg
        calculated_time += (cargo_weight_kg / 100.0) * float(time_per_weight)
    elif method == "Volume and Weight Combined":
        time_per_volume = getattr(doc, f"{prefix}_per_volume_m3", None) or \
                          getattr(doc, f"{operation}_time_per_volume_m3", None) or 0
        time_per_weight = getattr(doc, f"{prefix}_per_weight_kg", None) or \
                         getattr(doc, f"{operation}_time_per_weight_kg", None) or 0
        calculated_time += (cargo_volume_m3 * float(time_per_volume)) + \
                          ((cargo_weight_kg / 100.0) * float(time_per_weight))
    
    # Apply maximum cap if set
    max_time = getattr(doc, f"max_{operation}_time_minutes", None) or 0
    if max_time and max_time > 0:
        calculated_time = min(calculated_time, float(max_time))
    
    return max(calculated_time, 0)  # Ensure non-negative


def _calculate_time_from_defaults(cargo_weight_kg: float, cargo_volume_m3: float, 
                                   operation: str) -> float:
    """Calculate time from Transport Settings defaults"""
    try:
        settings = frappe.get_single("Transport Settings")
        
        base_time = getattr(settings, f"default_base_{operation}_time_minutes", 15) or 15
        time_per_volume = getattr(settings, f"default_{operation}_time_per_volume_m3", 5) or 5
        
        # Use volume-based calculation as default
        calculated_time = float(base_time) + (cargo_volume_m3 * float(time_per_volume))
        
        return max(calculated_time, 0)
    except Exception:
        # Fallback to simple defaults
        return 15.0 + (cargo_volume_m3 * 5.0)


def evaluate_truck_ban_for_planned_leg(
    vehicle_type: Optional[str],
    pick_address: Optional[str],
    drop_address: Optional[str],
    scheduled_datetime: datetime,
    capacity_weight: Optional[float] = None,
    debug: Optional[List[str]] = None,
) -> Tuple[str, Optional[str]]:
    """
    Evaluate truck ban for a planned leg (e.g. Transport Order) before a specific vehicle is assigned.

    Returns:
        (action, reason) where action is one of:
        - "skip": constraint system / truck ban disabled
        - "ok": no violation
        - "block": Strict mode violation (caller should throw)
        - "warn": Warning mode violation (caller should msgprint)
    """
    debug = debug or []

    try:
        settings = frappe.get_single("Transport Settings")
    except Exception:
        debug.append("Transport Settings not available, skipping truck ban check")
        return "skip", None

    if not settings.get("enable_constraint_system", False):
        return "skip", None

    checking_mode = settings.get("constraint_checking_mode", "Strict")
    if checking_mode == "Disabled":
        return "skip", None

    if not settings.get("enable_truck_ban_constraints", False):
        return "skip", None

    vehicle = {
        "vehicle_type": vehicle_type,
        "capacity_weight": capacity_weight or 0,
    }
    is_valid, reason = check_truck_ban_constraints(
        vehicle, scheduled_datetime, pick_address, drop_address, debug
    )
    if is_valid:
        return "ok", None

    if checking_mode == "Strict":
        return "block", reason or _("Truck ban constraint violation")
    return "warn", reason or _("Truck ban constraint violation")

