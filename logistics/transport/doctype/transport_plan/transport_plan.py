# logistics/transport/doctype/transport_plan/transport_plan.py

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import itertools

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, cint, cstr, flt


@frappe.whitelist()
def auto_allocate_and_create(plan_name: str, consolidate_legs: bool = True) -> Dict[str, Any]:
    """
    Allocate vehicles & drivers to Transport Legs, create/reuse Run Sheets,
    and append legs (we link only the Transport Leg, then prefill child fields
    from the leg so validations don't complain about facility types).
    """
    _ensure_controller_class()

    result: Dict[str, Any] = {
        "plan": plan_name,
        "created": [],
        "reused": [],
        "created_with_vehicle": [],
        "created_without_vehicle": [],
        "attached_legs": 0,
        "skipped": [],
        "errors": [],
        "debug": [],
        "leg_date_field": None,
        "window": None,
        "consolidated_trips": 0,
        "total_legs": 0,
        "consolidations_created": [],
        "load_type_consolidations": 0,
    }

    try:
        plan = frappe.get_doc("Transport Plan", plan_name)
    except Exception as e:
        frappe.msgprint(
            _("Cannot load Transport Plan {0}: {1}").format(plan_name, cstr(e)),
            title=_("Run Sheet Allocation"),
            indicator="red",
        )
        return result

    try:
        legs, leg_date_field, window = _get_transport_legs(plan, result["debug"])
        result["leg_date_field"] = leg_date_field
        result["window"] = window
    except Exception as e:
        result["errors"].append(f"Failed fetching legs: {cstr(e)}")
        return _finalize_and_msgprint(plan_name, result)

    if not legs:
        result["skipped"].append({
            "leg": "—",
            "reason": f"No eligible Transport Legs in date window {window} (field '{result['leg_date_field'] or '—'}')."
        })
        return _finalize_and_msgprint(plan_name, result)

    def _date_key(leg: Dict[str, Any]) -> str:
        return _get_leg_date_value(leg) or ""

    for _, group in itertools.groupby(sorted(legs, key=_date_key), key=_date_key):
        day_legs = list(group)
        day_legs.sort(key=lambda l: cstr(l.get("name") or ""))

        # Group legs by Run Sheet (vehicle + driver + date combination)
        runsheet_groups = {}
        
        if consolidate_legs:
            # Consolidate legs into optimized trips
            consolidated_trips = _consolidate_legs(day_legs, result["debug"])
            result["consolidated_trips"] = len(consolidated_trips)
            result["total_legs"] = len(day_legs)
            
            for trip in consolidated_trips:
                trip_debug: List[str] = []
                try:
                    # Find vehicle and driver for the entire trip
                    vehicle = _find_vehicle_for_trip(trip["legs"], trip_debug)
                    driver = None
                    
                    if vehicle:
                        driver = _find_candidate_driver(trip["legs"][0], vehicle, trip_debug)
                        if not driver:
                            trip_debug.append("No driver available for the selected vehicle.")
                    else:
                        trip_debug.append("No vehicle available for this trip.")

                    # Create run sheet for the entire trip
                    consolidation = trip.get("consolidation")
                    rs_name, reused = _create_or_reuse_run_sheet(trip["legs"][0], vehicle, driver, trip_debug, consolidation)

                    # Append all legs in the trip to the run sheet
                    trip_legs_added = 0
                    for leg in trip["legs"]:
                        appended = _append_leg_to_runsheet(rs_name, leg, trip_debug)
                        if appended:
                            trip_legs_added += 1
                            result["attached_legs"] += 1

                        if _has_field("Transport Leg", "run_sheet"):
                            frappe.db.set_value("Transport Leg", leg["name"], "run_sheet", rs_name)

                    # Group legs by Run Sheet for additional leg creation
                    if rs_name not in runsheet_groups:
                        runsheet_groups[rs_name] = {
                            "legs": [],
                            "reused": reused,
                            "debug": []
                        }
                    runsheet_groups[rs_name]["legs"].extend(trip["legs"])
                    runsheet_groups[rs_name]["debug"].extend(trip_debug)

                    # Track run sheets with and without vehicles
                    if vehicle:
                        if reused:
                            result["reused"].append(rs_name)
                        else:
                            result["created_with_vehicle"].append(rs_name)
                    else:
                        if reused:
                            result["reused"].append(rs_name)
                        else:
                            result["created_without_vehicle"].append(rs_name)
                    
                    # Keep backward compatibility
                    (result["reused"] if reused else result["created"]).append(rs_name)
                    
                    # Track consolidation if present
                    if consolidation:
                        result["consolidations_created"].append({
                            "consolidation": consolidation["name"],
                            "run_sheet": rs_name,
                            "load_type": trip.get("load_type"),
                            "legs_count": len(trip["legs"])
                        })
                        result["load_type_consolidations"] += 1

                except Exception as e:
                    result["errors"].append(f"Trip consolidation failed: {cstr(e)}")
                    continue
        else:
            # Original logic: one run sheet per leg
            for leg in day_legs:
                leg_debug: List[str] = []
                try:
                    vehicle = _find_candidate_vehicle(leg, leg_debug)
                    driver = None
                    
                    if vehicle:
                        driver = _find_candidate_driver(leg, vehicle, leg_debug)
                        if not driver:
                            leg_debug.append("No driver available for the selected vehicle.")
                    else:
                        leg_debug.append("No vehicle available for this leg.")

                    # Create run sheet with or without vehicle/driver
                    rs_name, reused = _create_or_reuse_run_sheet(leg, vehicle, driver, leg_debug)

                    # Append child row: set transport_leg THEN prefill other child fields from the leg
                    appended = _append_leg_to_runsheet(rs_name, leg, leg_debug)
                    if appended:
                        result["attached_legs"] += 1

                    if _has_field("Transport Leg", "run_sheet"):
                        frappe.db.set_value("Transport Leg", leg["name"], "run_sheet", rs_name)

                    # Group legs by Run Sheet for additional leg creation
                    if rs_name not in runsheet_groups:
                        runsheet_groups[rs_name] = {
                            "legs": [],
                            "reused": reused,
                            "debug": []
                        }
                    runsheet_groups[rs_name]["legs"].append(leg)
                    runsheet_groups[rs_name]["debug"].extend(leg_debug)

                    # Track run sheets with and without vehicles
                    if vehicle:
                        if reused:
                            result["reused"].append(rs_name)
                        else:
                            result["created_with_vehicle"].append(rs_name)
                    else:
                        if reused:
                            result["reused"].append(rs_name)
                        else:
                            result["created_without_vehicle"].append(rs_name)
                    
                    # Keep backward compatibility
                    (result["reused"] if reused else result["created"]).append(rs_name)

                except Exception as e:
                    result["errors"].append(f"{_fmt_leg(leg)}: {cstr(e)}")
                    continue

        # Add additional legs (base-to-first-pick, connecting, last-drop-to-base) to each Run Sheet
        for rs_name, group_data in runsheet_groups.items():
            try:
                additional_legs = _add_additional_legs_to_runsheet(
                    rs_name, 
                    group_data["legs"], 
                    group_data["debug"]
                )
                result["attached_legs"] += additional_legs
            except Exception as e:
                result["errors"].append(f"Failed to add additional legs to {rs_name}: {cstr(e)}")
                continue

    try:
        _update_plan_runsheets(plan, result["created"] + result["reused"])
    except Exception as e:
        result["errors"].append(f"Failed updating Transport Plan runsheets: {cstr(e)}")

    return _finalize_and_msgprint(plan_name, result)


# ------------------------ Legs & window ------------------------

def _date_window_for_plan(plan: Document) -> Tuple[str, str]:
    base = getdate(plan.plan_date) if getattr(plan, "plan_date", None) else getdate(nowdate())
    fwd = 0
    back = 0
    try:
        ts = frappe.get_single("Transport Settings")
        fwd = cint(getattr(ts, "forward_days_in_transport_plan", 0)) or 0
        back = cint(getattr(ts, "backward_days_in_transport_plan", 0)) or 0
    except Exception:
        pass

    start = add_days(base, -back).isoformat()
    end = add_days(base, fwd).isoformat()
    return (start, end)


def _leg_date_candidates() -> List[str]:
    return ["date", "scheduled_date", "booking_date", "planned_date", "posting_date"]


def _detect_leg_date_field() -> str:
    for f in _leg_date_candidates():
        if _has_field("Transport Leg", f):
            return f
    raise Exception(
        "No date field found on Transport Leg "
        "(tried: date, scheduled_date, booking_date, planned_date, posting_date)."
    )


def _get_transport_legs(plan: Document, debug: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], str, str]:
    debug = debug or []
    if not _doctype_exists("Transport Leg"):
        raise Exception("Doctype 'Transport Leg' does not exist.")

    leg_date_field = _detect_leg_date_field()
    start, end = _date_window_for_plan(plan)
    window = f"{start} → {end}"

    filters = [[leg_date_field, ">=", start], [leg_date_field, "<=", end]]
    if _has_field("Transport Leg", "run_sheet"):
        filters.append(["run_sheet", "is", "not set"])
    if _has_field("Transport Leg", "docstatus"):
        filters.append(["docstatus", "<", 2])

    base_fields = ["name", leg_date_field]
    opt_fields = []
    for f in [
        "vehicle_type", "hazardous", "order",
        "facility_type_from", "facility_from",
        "facility_type_to", "facility_to",
        "run_date", "transport_job",
    ]:
        if _has_field("Transport Leg", f):
            opt_fields.append(f)

    fields = list(dict.fromkeys(base_fields + opt_fields))
    legs = frappe.get_all(
        "Transport Leg",
        filters=filters,
        fields=fields,
        order_by=f"{leg_date_field} asc, `order` asc, modified asc",
    )
    debug.append(f"Legs fetched: {len(legs)} | Window {window} | Field '{leg_date_field}'")
    return legs, leg_date_field, window


def _get_leg_date_value(leg: Dict[str, Any]) -> Optional[str]:
    for f in _leg_date_candidates():
        v = leg.get(f)
        if v:
            return cstr(v)[:10]
    return None


# ------------------------ Consolidation & Optimization ------------------------

def _consolidate_legs(day_legs: List[Dict[str, Any]], debug: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Consolidate legs into optimized trips based on Load Type consolidation rules and route optimization.
    """
    debug = debug or []
    trips = []
    
    # First, check for Load Type-based consolidations
    consolidation_trips = _create_load_type_consolidations(day_legs, debug)
    if consolidation_trips:
        trips.extend(consolidation_trips)
        # Remove legs that were consolidated
        consolidated_leg_names = set()
        for trip in consolidation_trips:
            for leg in trip["legs"]:
                consolidated_leg_names.add(leg["name"])
        
        # Filter out consolidated legs
        remaining_legs = [leg for leg in day_legs if leg["name"] not in consolidated_leg_names]
        debug.append(f"Created {len(consolidation_trips)} Load Type consolidations, {len(remaining_legs)} legs remaining")
    else:
        remaining_legs = day_legs
        debug.append("No Load Type consolidations found, using route optimization")
    
    # For remaining legs, use traditional route optimization
    if remaining_legs:
        # Group legs by vehicle type
        legs_by_vehicle_type = {}
        for leg in remaining_legs:
            vt = leg.get("vehicle_type", "Unknown")
            if vt not in legs_by_vehicle_type:
                legs_by_vehicle_type[vt] = []
            legs_by_vehicle_type[vt].append(leg)
        
        debug.append(f"Grouped {len(remaining_legs)} remaining legs into {len(legs_by_vehicle_type)} vehicle types")
        
        # For each vehicle type, create optimized trips
        for vehicle_type, legs in legs_by_vehicle_type.items():
            debug.append(f"Processing {len(legs)} legs for vehicle type: {vehicle_type}")
            
            # Sort legs by priority and time windows
            sorted_legs = _sort_legs_for_optimization(legs)
            
            # Create trips based on capacity and route optimization
            vehicle_trips = _create_optimized_trips(sorted_legs, vehicle_type, debug)
            trips.extend(vehicle_trips)
    
    debug.append(f"Created {len(trips)} total trips from {len(day_legs)} legs")
    return trips


def _create_load_type_consolidations(day_legs: List[Dict[str, Any]], debug: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Create consolidations based on Load Type rules for LTL jobs.
    """
    debug = debug or []
    consolidation_trips = []
    
    # Group legs by load type
    legs_by_load_type = {}
    for leg in day_legs:
        # Get load type from transport job
        load_type = _get_leg_load_type(leg)
        if load_type:
            if load_type not in legs_by_load_type:
                legs_by_load_type[load_type] = []
            legs_by_load_type[load_type].append(leg)
    
    debug.append(f"Found {len(legs_by_load_type)} load types with consolidatable legs")
    
    # Process each load type
    for load_type, legs in legs_by_load_type.items():
        debug.append(f"Processing {len(legs)} legs for Load Type: {load_type}")
        
        # Check if load type allows consolidation
        load_type_doc = frappe.get_doc("Load Type", load_type)
        if not load_type_doc.can_consolidate:
            debug.append(f"Load Type {load_type} does not allow consolidation, skipping")
            continue
        
        # Create consolidation for this load type
        consolidation = _create_transport_consolidation(load_type, legs, debug)
        if consolidation:
            # Create trip for this consolidation
            trip = {
                "legs": legs,
                "vehicle_type": legs[0].get("vehicle_type") if legs else None,
                "consolidation": consolidation,
                "total_weight": sum(flt(leg.get("weight") or 0) for leg in legs),
                "total_volume": sum(flt(leg.get("volume") or 0) for leg in legs),
                "total_pallets": sum(flt(leg.get("pallets") or 0) for leg in legs),
                "hazardous": any(leg.get("hazardous") for leg in legs),
                "leg_count": len(legs),
                "load_type": load_type
            }
            consolidation_trips.append(trip)
            debug.append(f"Created consolidation {consolidation['name']} for {len(legs)} legs")
    
    return consolidation_trips


def _get_leg_load_type(leg: Dict[str, Any]) -> Optional[str]:
    """
    Get the load type for a transport leg by looking up the transport job.
    """
    transport_job = leg.get("transport_job")
    if not transport_job:
        return None
    
    try:
        load_type = frappe.db.get_value("Transport Job", transport_job, "load_type")
        return load_type
    except Exception:
        return None


def _create_transport_consolidation(load_type: str, legs: List[Dict[str, Any]], debug: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Create a Transport Consolidation for the given legs.
    """
    debug = debug or []
    
    try:
        # Get transport jobs from legs
        transport_jobs = [leg.get("transport_job") for leg in legs if leg.get("transport_job")]
        if not transport_jobs:
            debug.append("No transport jobs found in legs")
            return None
        
        # Create consolidation
        consolidation = frappe.new_doc("Transport Consolidation")
        consolidation.consolidation_date = _get_leg_date_value(legs[0]) or nowdate()
        consolidation.status = "Draft"
        consolidation.consolidation_type = "LTL"
        
        # Set accounting fields from first transport job
        if legs and legs[0].get("transport_job"):
            first_job = frappe.get_doc("Transport Job", legs[0]["transport_job"])
            consolidation.company = getattr(first_job, "company", None)
            consolidation.branch = getattr(first_job, "branch", None)
            consolidation.cost_center = getattr(first_job, "cost_center", None)
            consolidation.profit_center = getattr(first_job, "profit_center", None)
            consolidation.job_reference = getattr(first_job, "job_reference", None)
        
        # Add transport jobs
        for job_name in transport_jobs:
            consolidation.append("transport_jobs", {
                "transport_job": job_name,
                "weight": 0,  # Will be calculated from packages
                "volume": 0    # Will be calculated from packages
            })
        
        consolidation.save()
        debug.append(f"Created Transport Consolidation: {consolidation.name}")
        
        return {
            "name": consolidation.name,
            "load_type": load_type,
            "jobs_count": len(transport_jobs)
        }
        
    except Exception as e:
        debug.append(f"Failed to create consolidation: {cstr(e)}")
        return None


def _sort_legs_for_optimization(legs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort legs for optimization considering priority, time windows, and geographic proximity.
    """
    def sort_key(leg):
        # Priority: hazardous first, then by order, then by time
        priority = 0
        if leg.get("hazardous"):
            priority += 1000
        
        order = cint(leg.get("order") or 0)
        time_factor = 0
        
        # Consider time windows if available
        for time_field in ["pick_window_start", "drop_window_start", "run_date"]:
            if leg.get(time_field):
                try:
                    time_factor = cint(str(leg[time_field]).replace(":", "").replace("-", "").replace(" ", ""))
                except (ValueError, TypeError, AttributeError):
                    time_factor = 0
                break
        
        return (priority, order, time_factor)
    
    return sorted(legs, key=sort_key)


def _create_optimized_trips(legs: List[Dict[str, Any]], vehicle_type: str, debug: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Create optimized trips by grouping legs that can be served by the same vehicle.
    """
    debug = debug or []
    trips = []
    remaining_legs = legs.copy()
    
    while remaining_legs:
        # Start a new trip with the first leg
        current_trip = [remaining_legs.pop(0)]
        trip_capacity = _calculate_trip_capacity(current_trip)
        
        # Try to add more legs to this trip
        legs_to_remove = []
        for leg in remaining_legs:
            if _can_add_leg_to_trip(current_trip, leg, trip_capacity):
                current_trip.append(leg)
                legs_to_remove.append(leg)
                trip_capacity = _calculate_trip_capacity(current_trip)
        
        # Remove added legs from remaining
        for leg in legs_to_remove:
            remaining_legs.remove(leg)
        
        # Create trip object
        trip = {
            "legs": current_trip,
            "vehicle_type": vehicle_type,
            "total_weight": sum(flt(leg.get("weight") or 0) for leg in current_trip),
            "total_volume": sum(flt(leg.get("volume") or 0) for leg in current_trip),
            "total_pallets": sum(flt(leg.get("pallets") or 0) for leg in current_trip),
            "hazardous": any(leg.get("hazardous") for leg in current_trip),
            "leg_count": len(current_trip)
        }
        
        trips.append(trip)
        debug.append(f"Created trip with {len(current_trip)} legs for vehicle type {vehicle_type}")
    
    return trips


def _can_add_leg_to_trip(trip_legs: List[Dict[str, Any]], new_leg: Dict[str, Any], current_capacity: Dict[str, float]) -> bool:
    """
    Check if a leg can be added to an existing trip based on capacity and compatibility.
    """
    # Check vehicle type compatibility
    if new_leg.get("vehicle_type") != trip_legs[0].get("vehicle_type"):
        return False
    
    # Check hazardous material compatibility
    if new_leg.get("hazardous") and not all(leg.get("hazardous") for leg in trip_legs):
        return False
    
    # Check capacity constraints
    new_weight = flt(new_leg.get("weight") or 0)
    new_volume = flt(new_leg.get("volume") or 0)
    new_pallets = flt(new_leg.get("pallets") or 0)
    
    # Get vehicle capacity (we'll need to find a vehicle to check this)
    # For now, use reasonable defaults
    max_weight = 10000  # kg
    max_volume = 100    # m³
    max_pallets = 50
    
    if current_capacity["weight"] + new_weight > max_weight:
        return False
    if current_capacity["volume"] + new_volume > max_volume:
        return False
    if current_capacity["pallets"] + new_pallets > max_pallets:
        return False
    
    return True


def _calculate_trip_capacity(trip_legs: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate total capacity requirements for a trip.
    """
    return {
        "weight": sum(flt(leg.get("weight") or 0) for leg in trip_legs),
        "volume": sum(flt(leg.get("volume") or 0) for leg in trip_legs),
        "pallets": sum(flt(leg.get("pallets") or 0) for leg in trip_legs)
    }


def _find_vehicle_for_trip(trip_legs: List[Dict[str, Any]], debug: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Find a suitable vehicle for an entire trip based on capacity requirements.
    """
    debug = debug or []
    if not trip_legs:
        return None
    
    # Use the first leg to determine vehicle type and requirements
    first_leg = trip_legs[0]
    vehicle_type = first_leg.get("vehicle_type")
    
    if not vehicle_type:
        debug.append("No vehicle type specified for trip")
        return None
    
    # Calculate total trip requirements
    total_weight = sum(flt(leg.get("weight") or 0) for leg in trip_legs)
    total_volume = sum(flt(leg.get("volume") or 0) for leg in trip_legs)
    total_pallets = sum(flt(leg.get("pallets") or 0) for leg in trip_legs)
    has_hazardous = any(leg.get("hazardous") for leg in trip_legs)
    
    debug.append(f"Trip requirements: {total_weight}kg, {total_volume}m³, {total_pallets}pallets, hazardous: {has_hazardous}")
    
    # Find vehicles that can handle the entire trip
    v_filters: List[Any] = [
        ["company_owned", "=", 1],  # Only internal vehicles
        ["vehicle_type", "=", vehicle_type]
    ]
    
    v_fields = ["name", "vehicle_name", "company_owned"]
    for vf in ["vehicle_type", "transport_company", "capacity_weight", "capacity_volume", "capacity_pallets"]:
        if _has_field("Transport Vehicle", vf):
            v_fields.append(vf)

    vehicles = frappe.get_all(
        "Transport Vehicle",
        filters=v_filters,
        fields=v_fields,
        limit_page_length=200,
        order_by="modified desc",
    )
    
    if not vehicles:
        debug.append("No internal vehicles available for trip")
        return None
    
    # Check vehicle availability for the entire trip duration
    trip_date = _get_leg_date_value(first_leg)
    
    for vehicle in vehicles:
        # Check if vehicle is available for the entire trip
        if not _vehicle_free_on_date(vehicle["name"], trip_date):
            debug.append(f"Vehicle {vehicle.get('vehicle_name') or vehicle['name']} busy on {trip_date}")
            continue
        
        # Check capacity
        vehicle_weight = flt(vehicle.get("capacity_weight") or 0)
        vehicle_volume = flt(vehicle.get("capacity_volume") or 0)
        vehicle_pallets = flt(vehicle.get("capacity_pallets") or 0)
        
        if total_weight > 0 and vehicle_weight < total_weight:
            debug.append(f"Vehicle {vehicle.get('vehicle_name')} insufficient weight capacity")
            continue
        if total_volume > 0 and vehicle_volume < total_volume:
            debug.append(f"Vehicle {vehicle.get('vehicle_name')} insufficient volume capacity")
            continue
        if total_pallets > 0 and vehicle_pallets < total_pallets:
            debug.append(f"Vehicle {vehicle.get('vehicle_name')} insufficient pallet capacity")
            continue
        
        debug.append(f"Selected vehicle for trip: {vehicle.get('vehicle_name') or vehicle['name']}")
        return vehicle
    
    debug.append("No suitable vehicle found for trip")
    return None


# ------------------------ Vehicle & Driver ------------------------

def _find_candidate_vehicle(leg: Dict[str, Any], debug: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    debug = debug or []
    if not _doctype_exists("Transport Vehicle"):
        debug.append("No 'Transport Vehicle' doctype.")
        return None

    v_filters: List[Any] = [
        ["company_owned", "=", 1]  # Only internal vehicles
    ]
    if leg.get("vehicle_type") and _has_field("Transport Vehicle", "vehicle_type"):
        v_filters.append(["vehicle_type", "=", leg["vehicle_type"]])

    v_fields = ["name", "vehicle_name", "company_owned"]
    for vf in ["vehicle_type", "transport_company", "capacity_weight", "capacity_volume", "capacity_pallets"]:
        if _has_field("Transport Vehicle", vf):
            v_fields.append(vf)

    vehicles = frappe.get_all(
        "Transport Vehicle",
        filters=v_filters,
        fields=v_fields,
        limit_page_length=200,
        order_by="modified desc",
    )
    if not vehicles:
        debug.append("No internal vehicles match filters.")
        return None

    sched = _get_leg_date_value(leg)
    need_w = flt(leg.get("weight") or 0)
    need_v = flt(leg.get("volume") or 0)
    need_p = flt(leg.get("pallets") or 0)

    for v in vehicles:
        if not _vehicle_free_on_date(v["name"], sched):
            debug.append(f"Internal vehicle busy on {sched}: {v.get('vehicle_name') or v['name']}")
            continue

        ok = True
        if need_w and _has_field("Transport Vehicle", "capacity_weight"):
            ok = ok and flt(v.get("capacity_weight") or 0) >= need_w
        if ok and need_v and _has_field("Transport Vehicle", "capacity_volume"):
            ok = ok and flt(v.get("capacity_volume") or 0) >= need_v
        if ok and need_p and _has_field("Transport Vehicle", "capacity_pallets"):
            ok = ok and flt(v.get("capacity_pallets") or 0) >= need_p

        if ok:
            debug.append(f"Internal vehicle selected: {v.get('vehicle_name') or v['name']}")
            return v

    debug.append("All internal vehicles failed availability/capacity.")
    return None


def _fmt_reason_no_vehicle(leg: Dict[str, Any]) -> str:
    vt = cstr(leg.get("vehicle_type") or "—")
    sched = _get_leg_date_value(leg) or "—"
    return f"No eligible internal Transport Vehicle found (Vehicle Type: {vt}, Date: {sched})."


def _find_candidate_driver(leg: Dict[str, Any], vehicle: Dict[str, Any], debug: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    debug = debug or []
    if not _doctype_exists("Driver"):
        debug.append("No 'Driver' doctype.")
        return None

    filters: List[Any] = []
    if _has_field("Driver", "status"):
        filters.append(["status", "=", "Active"])
    if leg.get("hazardous") and _has_field("Driver", "custom_hazmat_endorsement"):
        filters.append(["custom_hazmat_endorsement", "=", 1])
    if vehicle.get("transport_company") and _has_field("Driver", "custom_transport_company"):
        filters.append(["custom_transport_company", "=", vehicle["transport_company"]])

    d_fields = ["name"]
    if _has_field("Driver", "full_name"):
        d_fields.append("full_name")

    drivers = frappe.get_all(
        "Driver",
        filters=filters,
        fields=d_fields,
        limit_page_length=200,
        order_by="modified desc",
    )
    if not drivers:
        debug.append("No drivers match filters.")
        return None

    sched = _get_leg_date_value(leg)
    for d in drivers:
        if _driver_free_on_date(d["name"], sched):
            debug.append(f"Driver selected: {d.get('full_name') or d['name']}")
            return d

    debug.append("All candidate drivers are busy.")
    return None


def _vehicle_free_on_date(vehicle_name: str, day: Optional[str]) -> bool:
    if not _doctype_exists("Run Sheet") or not _has_field("Run Sheet", "vehicle") or not _has_field("Run Sheet", "run_date"):
        return True
    if not day:
        return True

    start = f"{day} 00:00:00"
    end = f"{day} 23:59:59"
    rows = frappe.get_all(
        "Run Sheet",
        filters=[
            ["vehicle", "=", vehicle_name],
            ["run_date", ">=", start],
            ["run_date", "<=", end],
            ["docstatus", "<", 2],
        ],
        fields=["name"],
        limit_page_length=1,
    )
    return not rows


def _driver_free_on_date(driver_name: str, day: Optional[str]) -> bool:
    if not _doctype_exists("Run Sheet") or not _has_field("Run Sheet", "driver") or not _has_field("Run Sheet", "run_date"):
        return True
    if not day:
        return True

    start = f"{day} 00:00:00"
    end = f"{day} 23:59:59"
    rows = frappe.get_all(
        "Run Sheet",
        filters=[
            ["driver", "=", driver_name],
            ["run_date", ">=", start],
            ["run_date", "<=", end],
            ["docstatus", "<", 2],
        ],
        fields=["name"],
        limit_page_length=1,
    )
    return not rows


# ------------------------ Run Sheet & legs ------------------------

def _create_or_reuse_run_sheet(leg: Dict[str, Any], vehicle: Optional[Dict[str, Any]], driver: Optional[Dict[str, Any]], debug: Optional[List[str]] = None, consolidation: Optional[Dict[str, Any]] = None) -> Tuple[str, bool]:
    debug = debug or []
    sched = _get_leg_date_value(leg) or nowdate()
    rs_date = f"{sched} 08:00:00"

    # Only try to reuse if we have both vehicle and driver
    existing = []
    if vehicle and driver and _doctype_exists("Run Sheet") and _has_field("Run Sheet", "vehicle") and _has_field("Run Sheet", "driver") and _has_field("Run Sheet", "run_date"):
        existing = frappe.get_all(
            "Run Sheet",
            filters=[
                ["vehicle", "=", vehicle["name"]],
                ["driver", "=", driver["name"]],
                ["run_date", ">=", f"{sched} 00:00:00"],
                ["run_date", "<=", f"{sched} 23:59:59"],
                ["docstatus", "<", 2],
            ],
            fields=["name"],
            limit_page_length=1,
        )
    if existing:
        rs_name = existing[0]["name"]
        debug.append(f"Reusing Run Sheet: {rs_name}")
        return rs_name, True

    rs = frappe.new_doc("Run Sheet")
    if _has_field("Run Sheet", "run_date"):
        rs.run_date = rs_date
    if _has_field("Run Sheet", "vehicle_type"):
        rs.vehicle_type = leg.get("vehicle_type")
    if _has_field("Run Sheet", "vehicle") and vehicle:
        rs.vehicle = vehicle["name"]
    if _has_field("Run Sheet", "transport_company") and vehicle:
        rs.transport_company = vehicle.get("transport_company")
    if _has_field("Run Sheet", "driver") and driver:
        rs.driver = driver["name"]
    
    # Link to consolidation if provided
    if consolidation and _has_field("Run Sheet", "transport_consolidation"):
        rs.transport_consolidation = consolidation["name"]
        debug.append(f"Linked to Transport Consolidation: {consolidation['name']}")

    try:
        rs.insert(ignore_permissions=True)
        debug.append(f"Created Run Sheet: {rs.name}")
        return rs.name, False
    except Exception as e:
        raise Exception(f"Run Sheet save failed: {cstr(e)}")


# 1) Append only the Transport Leg and skip validations when saving
def _append_leg_to_runsheet(rs_name: str, leg: Dict[str, Any], debug: Optional[List[str]] = None) -> bool:
    debug = debug or []
    rs = frappe.get_doc("Run Sheet", rs_name)

    if not _has_child_table(rs, "legs", "Run Sheet Leg"):
        debug.append("Run Sheet child table 'legs' missing or not 'Run Sheet Leg'.")
        return False

    # Only set the link; the child doctype will auto-fill other fields.
    child = rs.append("legs", {})
    if not _has_field("Run Sheet Leg", "transport_leg"):
        raise Exception("Run Sheet Leg is missing 'transport_leg' link field.")
    child.transport_leg = leg["name"]

    try:
        # Skip validations so we don't hit "Facility Type From must be set first".
        rs.save(ignore_permissions=True)
        debug.append(f"Appended leg {leg['name']} to {rs_name}")
        return True
    except Exception as e:
        raise Exception(f"Run Sheet update failed: {cstr(e)}")


def _copy_leg_to_runsheet_leg(child: Document, leg_doc: Document) -> None:
    """
    Copy fields from Transport Leg → Run Sheet Leg IF those fields exist on the child.
    We do not require them; we just set them when available.
    Order matters for dynamic links (facility_type_* before facility_*).
    """
    # From
    _set_if_exists(child, "facility_type_from", getattr(leg_doc, "facility_type_from", None))
    _set_if_exists(child, "facility_from", getattr(leg_doc, "facility_from", None))
    _set_if_exists(child, "pick_mode", getattr(leg_doc, "pick_mode", None))
    _set_if_exists(child, "pick_address", getattr(leg_doc, "pick_address", None))
    _set_if_exists(child, "pick_window_start", getattr(leg_doc, "pick_window_start", None))
    _set_if_exists(child, "pick_window_end", getattr(leg_doc, "pick_window_end", None))

    # To
    _set_if_exists(child, "facility_type_to", getattr(leg_doc, "facility_type_to", None))
    _set_if_exists(child, "facility_to", getattr(leg_doc, "facility_to", None))
    _set_if_exists(child, "drop_mode", getattr(leg_doc, "drop_mode", None))
    _set_if_exists(child, "drop_address", getattr(leg_doc, "drop_address", None))
    _set_if_exists(child, "drop_window_start", getattr(leg_doc, "drop_window_start", None))
    _set_if_exists(child, "drop_window_end", getattr(leg_doc, "drop_window_end", None))

    # Other handy fields if present
    _set_if_exists(child, "vehicle_type", getattr(leg_doc, "vehicle_type", None))
    _set_if_exists(child, "hazardous", getattr(leg_doc, "hazardous", None))


def _set_if_exists(doc: Document, fieldname: str, value: Any) -> None:
    if value is None:
        return
    doctype = doc.doctype
    if _has_field(doctype, fieldname):
        setattr(doc, fieldname, value)


def _update_plan_runsheets(plan: Document, run_sheet_names: List[str]) -> None:
    if not run_sheet_names:
        return
    if not _has_child_table(plan, "runsheets", "Transport Plan Run Sheets"):
        return

    existing = {row.run_sheet for row in getattr(plan, "runsheets", []) if getattr(row, "run_sheet", None)}
    added = False
    for rs in run_sheet_names:
        if rs in existing:
            continue
        row = plan.append("runsheets", {})
        if hasattr(row, "run_sheet"):
            row.run_sheet = rs
        added = True

    if added:
        plan.save(ignore_permissions=True)


# ------------------------ Formatting & summary ------------------------

def _fmt_leg(leg: Dict[str, Any]) -> str:
    date = _get_leg_date_value(leg) or ""
    vt = cstr(leg.get("vehicle_type") or "—")
    from_txt = _fmt_facility(leg.get("facility_type_from"), leg.get("facility_from"))
    to_txt = _fmt_facility(leg.get("facility_type_to"), leg.get("facility_to"))
    return f"{leg.get('name')} on {date} | From {from_txt} → To {to_txt} | VT: {vt}"


def _fmt_facility(ftype: Optional[str], fname: Optional[str]) -> str:
    if ftype and fname:
        return f"{fname} [{ftype}]"
    if fname:
        return cstr(fname)
    if ftype:
        return f"[{ftype}]"
    return "—"


# 2) Build HTML only; no plain text. Also return a minimal dict.
def _finalize_and_msgprint(plan_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    created = result.get("created") or []
    reused = result.get("reused") or []
    created_with_vehicle = result.get("created_with_vehicle") or []
    created_without_vehicle = result.get("created_without_vehicle") or []
    skipped = result.get("skipped") or []
    errors = result.get("errors") or []

    leg_date_field = cstr(result.get("leg_date_field") or "—")
    window = cstr(result.get("window") or "—")
    attached = cint(result.get("attached_legs") or 0)

    def li(text: str) -> str:
        return f"<li>{frappe.utils.escape_html(text)}</li>"

    # Build HTML only (no text fallback)
    html_parts = []
    html_parts.append('<div class="frappe-card" style="padding:12px; line-height:1.4">')
    html_parts.append('<h3 style="margin:0 0 8px 0">Create ➜ Run Sheets</h3>')
    
    # Show consolidation status
    consolidation_info = ""
    load_type_consolidations = result.get("load_type_consolidations", 0)
    consolidated_trips = result.get("consolidated_trips", 0)
    
    if load_type_consolidations > 0 or consolidated_trips > 0:
        consolidation_details = []
        if load_type_consolidations > 0:
            consolidation_details.append(f"{load_type_consolidations} Load Type consolidations")
        if consolidated_trips > 0:
            consolidation_details.append(f"{consolidated_trips} route-optimized trips")
        
        consolidation_info = f"""
        <div style="background:#e7f3ff; border:1px solid #b3d9ff; padding:8px; border-radius:4px; margin-bottom:10px; font-size:12px;">
          <i class="fa fa-route"></i> <strong>Consolidation Active:</strong> 
          {' + '.join(consolidation_details)} created from {result.get('total_legs', 0)} legs
        </div>
        """
    else:
        consolidation_info = """
        <div style="background:#fff3cd; border:1px solid #ffeaa7; padding:8px; border-radius:4px; margin-bottom:10px; font-size:12px;">
          <i class="fa fa-info-circle"></i> <strong>Individual Mode:</strong> One run sheet per leg
        </div>
        """
    
    html_parts.append(consolidation_info)
    
    # Show consolidation details if any
    consolidations_created = result.get("consolidations_created", [])
    if consolidations_created:
        consolidation_items = []
        for cons in consolidations_created:
            consolidation_items.append(li(f"{cons['consolidation']} ({cons['load_type']}) → {cons['run_sheet']} ({cons['legs_count']} legs)"))
        
        html_parts.append(f"""
        <div style="border:1px solid #28a745; padding:10px; border-radius:8px; background:#f8fff9; margin-bottom:10px">
          <div><b>Load Type Consolidations Created</b> ({len(consolidations_created)})</div>
          <ul style="margin:6px 0 0 18px">{''.join(consolidation_items)}</ul>
        </div>
        """)
    
    html_parts.append(f"""
    <div style="margin-bottom:10px">
      <div><b>Transport Plan:</b> {frappe.utils.escape_html(plan_name)}</div>
      <div><b>Leg date field used:</b> {frappe.utils.escape_html(leg_date_field)}</div>
      <div><b>Window:</b> {frappe.utils.escape_html(window)}</div>
    </div>
    """)
    
    # Add View Unassigned Run Sheets button
    unassigned_count = len(created_without_vehicle)
    if unassigned_count > 0:
        html_parts.append(f"""
        <div style="margin-bottom:15px; text-align:center">
          <button onclick="viewUnassignedRunSheets()" class="btn btn-primary" style="background:#007bff; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer; font-size:14px;">
            <i class="fa fa-list"></i> View Unassigned Run Sheets ({unassigned_count})
          </button>
        </div>
        """)
    
    html_parts.append(f"""
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:10px; margin-bottom:10px">
      <div class="card" style="border:1px solid var(--border-color); padding:10px; border-radius:8px">
        <div><b>Run Sheets with Vehicle</b> ({len(created_with_vehicle)})</div>
        <ul style="margin:6px 0 0 18px">{''.join(li(r) for r in created_with_vehicle) or '<li>—</li>'}</ul>
      </div>
      <div class="card" style="border:1px solid #ffc107; padding:10px; border-radius:8px; background:#fff3cd">
        <div><b>Run Sheets without Vehicle</b> ({len(created_without_vehicle)})</div>
        <ul style="margin:6px 0 0 18px">{''.join(li(r) for r in created_without_vehicle) or '<li>—</li>'}</ul>
      </div>
      <div class="card" style="border:1px solid var(--border-color); padding:10px; border-radius:8px">
        <div><b>Reused Run Sheets</b> ({len(reused)})</div>
        <ul style="margin:6px 0 0 18px">{''.join(li(r) for r in reused) or '<li>—</li>'}</ul>
      </div>
      <div class="card" style="border:1px solid var(--border-color); padding:10px; border-radius:8px">
        <div><b>Legs Attached</b></div>
        <div style="font-size:20px; font-weight:600; margin-top:6px">{attached}</div>
      </div>
    </div>
    """)

    # Skipped
    skip_items = []
    for s in skipped:
        leg_txt = cstr(s.get("leg") or "—")
        reason = cstr(s.get("reason") or "—")
        skip_items.append(li(f"{leg_txt} — {reason}"))
    
    html_parts.append(f"""
    <div style="border:1px solid var(--border-color); padding:10px; border-radius:8px; margin-bottom:10px">
      <div><b>Skipped</b> ({len(skipped)})</div>
      <ul style="margin:6px 0 0 18px">{''.join(skip_items) or '<li>—</li>'}</ul>
    </div>
    """)

    # Errors
    if errors:
        err_items = ''.join(li(cstr(e)) for e in errors)
        html_parts.append(f"""
        <div style="border:1px solid #e66; padding:10px; border-radius:8px; background:#fff6f6">
          <div><b>Errors</b></div>
          <ul style="margin:6px 0 0 18px">{err_items}</ul>
        </div>
        """)

    # Add JavaScript for the View Unassigned Run Sheets button
    html_parts.append("""
    <script>
    function viewUnassignedRunSheets() {
        // Navigate to Run Sheet list with filter for unassigned vehicles
        frappe.set_route("List", "Run Sheet", {
            "vehicle": ["is", "not set"]
        });
    }
    </script>
    """)
    
    html_parts.append("</div>")
    html = "".join(html_parts)

    # Show ONLY HTML; no as_html/as_is flags (v15 renders HTML safely by default).
    frappe.msgprint(html, title=_("Run Sheet Allocation Result"), wide=True)

    # Return minimal payload so the client won't render extra plain text
    return {
        "ok": True,
        "created_count": len(created),
        "created_with_vehicle_count": len(created_with_vehicle),
        "created_without_vehicle_count": len(created_without_vehicle),
        "reused_count": len(reused),
        "attached_legs": attached,
        "skipped_count": len(skipped),
        "error_count": len(errors),
    }


# ------------------------ Helpers ------------------------

def _doctype_exists(doctype: str) -> bool:
    try:
        frappe.get_meta(doctype)
        return True
    except Exception:
        return False


def _has_field(doctype: str, fieldname: str) -> bool:
    try:
        meta = frappe.get_meta(doctype)
        return bool(meta.get_field(fieldname))
    except Exception:
        return False


def _has_child_table(doc_or_doctype: Any, childtable_fieldname: str, child_doctype: str) -> bool:
    try:
        meta = frappe.get_meta(doc_or_doctype.doctype if hasattr(doc_or_doctype, "doctype") else cstr(doc_or_doctype))
        fld = meta.get_field(childtable_fieldname)
        return bool(fld and fld.fieldtype == "Table")
    except Exception:
        return False


def _ensure_controller_class() -> None:
    return


# ------------------------ Additional Leg Creation ------------------------

def _create_base_to_first_pick_leg(rs: Document, first_leg: Dict[str, Any]) -> Optional[Document]:
    """
    Create a leg from base location to the first pick location.
    Returns the created Transport Leg document or None if base location is not set.
    """
    if not rs.get("base_location_type") or not rs.get("base_location"):
        return None
    
    # Check if first leg has valid pick location
    if not first_leg.get("facility_type_from") or not first_leg.get("facility_from"):
        return None
    
    # Create new Transport Leg
    leg = frappe.new_doc("Transport Leg")
    leg.transport_job = first_leg.get("transport_job")
    leg.date = first_leg.get("date")
    leg.vehicle_type = first_leg.get("vehicle_type")
    leg.hazardous = first_leg.get("hazardous")
    
    # Set from base location
    leg.facility_type_from = rs.base_location_type
    leg.facility_from = rs.base_location
    
    # Set to first pick location
    leg.facility_type_to = first_leg.get("facility_type_from")
    leg.facility_to = first_leg.get("facility_from")
    
    # Set operation type to indicate this is a base-to-pick leg
    if _has_field("Transport Leg", "operation_type"):
        leg.operation_type = "Base to Pick"
    
    # Set order to be before the first leg
    if _has_field("Transport Leg", "order"):
        leg.order = cint(first_leg.get("order") or 0) - 1
    
    leg.insert(ignore_permissions=True)
    return leg


def _create_last_drop_to_base_leg(rs: Document, last_leg: Dict[str, Any]) -> Optional[Document]:
    """
    Create a leg from the last drop location back to base.
    Returns the created Transport Leg document or None if base location is not set.
    """
    if not rs.get("base_location_type") or not rs.get("base_location"):
        return None
    
    # Create new Transport Leg
    leg = frappe.new_doc("Transport Leg")
    leg.transport_job = last_leg.get("transport_job")
    leg.date = last_leg.get("date")
    leg.vehicle_type = last_leg.get("vehicle_type")
    leg.hazardous = last_leg.get("hazardous")
    
    # Set from last drop location
    leg.facility_type_from = last_leg.get("facility_type_to")
    leg.facility_from = last_leg.get("facility_to")
    
    # Set to base location
    leg.facility_type_to = rs.base_location_type
    leg.facility_to = rs.base_location
    
    # Set operation type to indicate this is a drop-to-base leg
    if _has_field("Transport Leg", "operation_type"):
        leg.operation_type = "Drop to Base"
    
    # Set order to be after the last leg
    if _has_field("Transport Leg", "order"):
        leg.order = cint(last_leg.get("order") or 0) + 1
    
    leg.insert(ignore_permissions=True)
    return leg


def _create_connecting_leg(rs: Document, from_leg: Dict[str, Any], to_leg: Dict[str, Any]) -> Optional[Document]:
    """
    Create a connecting leg between two jobs (from one job's drop to next job's pick).
    Returns the created Transport Leg document.
    """
    # Create new Transport Leg
    leg = frappe.new_doc("Transport Leg")
    leg.transport_job = to_leg.get("transport_job")  # Associate with the destination job
    leg.date = to_leg.get("date")
    leg.vehicle_type = to_leg.get("vehicle_type")
    leg.hazardous = to_leg.get("hazardous")
    
    # Set from previous job's drop location
    leg.facility_type_from = from_leg.get("facility_type_to")
    leg.facility_from = from_leg.get("facility_to")
    
    # Set to next job's pick location
    leg.facility_type_to = to_leg.get("facility_type_from")
    leg.facility_to = to_leg.get("facility_from")
    
    # Set operation type to indicate this is a connecting leg
    if _has_field("Transport Leg", "operation_type"):
        leg.operation_type = "Connecting"
    
    # Set order to be between the two legs
    if _has_field("Transport Leg", "order"):
        from_order = cint(from_leg.get("order") or 0)
        to_order = cint(to_leg.get("order") or 0)
        leg.order = (from_order + to_order) // 2
    
    leg.insert(ignore_permissions=True)
    return leg


def _add_additional_legs_to_runsheet(rs_name: str, legs: List[Dict[str, Any]], debug: Optional[List[str]] = None) -> int:
    """
    Add base-to-first-pick, connecting, and last-drop-to-base legs to a Run Sheet.
    Returns the number of additional legs added.
    """
    debug = debug or []
    rs = frappe.get_doc("Run Sheet", rs_name)
    
    if not legs:
        debug.append("No legs provided for additional leg creation")
        return 0
    
    additional_legs_added = 0
    
    # Sort legs by order field, then by name to ensure proper order
    sorted_legs = sorted(legs, key=lambda l: (cint(l.get("order") or 0), cstr(l.get("name") or "")))
    
    # 1. Add base-to-first-pick leg (only if base location is set)
    if sorted_legs and rs.get("base_location_type") and rs.get("base_location"):
        first_leg = sorted_legs[0]
        base_to_pick_leg = _create_base_to_first_pick_leg(rs, first_leg)
        if base_to_pick_leg:
            # Add to Run Sheet
            child = rs.append("legs", {})
            child.transport_leg = base_to_pick_leg.name
            if _has_field("Run Sheet Leg", "sequence"):
                child.sequence = base_to_pick_leg.order or 0
            additional_legs_added += 1
            debug.append(f"Added base-to-first-pick leg: {base_to_pick_leg.name}")
    elif sorted_legs:
        debug.append("Skipped base-to-first-pick leg: Run Sheet base location not set")
    
    # 2. Add connecting legs between jobs
    for i in range(len(sorted_legs) - 1):
        current_leg = sorted_legs[i]
        next_leg = sorted_legs[i + 1]
        
        # Check if these are different jobs (different transport_job)
        if current_leg.get("transport_job") != next_leg.get("transport_job"):
            connecting_leg = _create_connecting_leg(rs, current_leg, next_leg)
            if connecting_leg:
                # Add to Run Sheet
                child = rs.append("legs", {})
                child.transport_leg = connecting_leg.name
                if _has_field("Run Sheet Leg", "sequence"):
                    child.sequence = connecting_leg.order or 0
                additional_legs_added += 1
                debug.append(f"Added connecting leg: {connecting_leg.name}")
    
    # 3. Add last-drop-to-base leg (only if base location is set)
    if sorted_legs and rs.get("base_location_type") and rs.get("base_location"):
        last_leg = sorted_legs[-1]
        drop_to_base_leg = _create_last_drop_to_base_leg(rs, last_leg)
        if drop_to_base_leg:
            # Add to Run Sheet
            child = rs.append("legs", {})
            child.transport_leg = drop_to_base_leg.name
            if _has_field("Run Sheet Leg", "sequence"):
                child.sequence = drop_to_base_leg.order or 0
            additional_legs_added += 1
            debug.append(f"Added last-drop-to-base leg: {drop_to_base_leg.name}")
    elif sorted_legs:
        debug.append("Skipped last-drop-to-base leg: Run Sheet base location not set")
    
    # Save the Run Sheet with additional legs
    if additional_legs_added > 0:
        try:
            rs.save(ignore_permissions=True)
            debug.append(f"Added {additional_legs_added} additional legs to {rs_name}")
        except Exception as e:
            debug.append(f"Failed to save additional legs: {cstr(e)}")
            raise Exception(f"Run Sheet update failed: {cstr(e)}")
    else:
        debug.append("No additional legs added to Run Sheet")
    
    return additional_legs_added


class TransportPlan(Document):
    pass
