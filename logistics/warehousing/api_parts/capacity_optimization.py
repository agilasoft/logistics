# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Capacity Optimization System
============================

This module provides intelligent capacity optimization algorithms for warehouse
operations, including dynamic reallocation, load balancing, and space optimization.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate
from .capacity_management import CapacityManager, CapacityValidationError


class CapacityOptimizer:
    """Intelligent capacity optimization for warehouse operations"""
    
    def __init__(self):
        self.capacity_manager = CapacityManager()
        self.optimization_cache = {}
    
    def optimize_warehouse_capacity(
        self,
        company: Optional[str] = None,
        branch: Optional[str] = None,
        site: Optional[str] = None,
        building: Optional[str] = None,
        zone: Optional[str] = None,
        optimization_type: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Optimize warehouse capacity across locations
        
        Args:
            company: Company filter
            branch: Branch filter
            site: Site filter
            building: Building filter
            zone: Zone filter
            optimization_type: Type of optimization (balanced, volume, weight, hu)
            
        Returns:
            Dict with optimization recommendations and actions
        """
        try:
            # Get current capacity status
            current_status = self._get_capacity_status(company, branch, site, building, zone)
            
            # Identify optimization opportunities
            opportunities = self._identify_optimization_opportunities(current_status, optimization_type)
            
            # Generate optimization recommendations
            recommendations = self._generate_optimization_recommendations(opportunities, optimization_type)
            
            # Calculate potential savings
            potential_savings = self._calculate_optimization_savings(recommendations)
            
            # Generate optimization actions
            actions = self._generate_optimization_actions(recommendations)
            
            return {
                "optimization_type": optimization_type,
                "current_status": current_status,
                "opportunities": opportunities,
                "recommendations": recommendations,
                "potential_savings": potential_savings,
                "actions": actions,
                "generated_at": now_datetime(),
                "optimization_score": self._calculate_optimization_score(current_status)
            }
            
        except Exception as e:
            frappe.log_error(f"Capacity optimization error: {str(e)}")
            return {"error": str(e)}
    
    def _get_capacity_status(
        self,
        company: Optional[str] = None,
        branch: Optional[str] = None,
        site: Optional[str] = None,
        building: Optional[str] = None,
        zone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current capacity status for all locations"""
        try:
            # Build filters
            filters = {}
            if company:
                filters["company"] = company
            if branch:
                filters["branch"] = branch
            if site:
                filters["site"] = site
            if building:
                filters["building"] = building
            if zone:
                filters["zone"] = zone
            
            # Get storage locations with capacity data
            locations = frappe.get_all(
                "Storage Location",
                filters=filters,
                fields=[
                    "name", "site", "building", "zone", "aisle", "bay", "level",
                    "max_volume", "max_weight", "max_hu_slot",
                    "current_volume", "current_weight", "utilization_percentage",
                    "status", "storage_type", "bin_priority"
                ]
            )
            
            # Get current stock data for each location
            for location in locations:
                stock_data = frappe.db.sql("""
                    SELECT 
                        COUNT(DISTINCT l.handling_unit) as hu_count,
                        COUNT(DISTINCT l.item) as item_count,
                        SUM(l.quantity) as total_quantity,
                        SUM(wi.volume * l.quantity) as total_volume,
                        SUM(wi.weight * l.quantity) as total_weight
                    FROM `tabWarehouse Stock Ledger` l
                    LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
                    WHERE l.storage_location = %s AND l.quantity > 0
                """, (location.name,), as_dict=True)
                
                if stock_data:
                    stock = stock_data[0]
                    location["current_hu_count"] = stock["hu_count"]
                    location["current_item_count"] = stock["item_count"]
                    location["current_total_quantity"] = stock["total_quantity"]
                    location["calculated_volume"] = stock["total_volume"]
                    location["calculated_weight"] = stock["total_weight"]
                else:
                    location["current_hu_count"] = 0
                    location["current_item_count"] = 0
                    location["current_total_quantity"] = 0
                    location["calculated_volume"] = 0
                    location["calculated_weight"] = 0
                
                # Calculate utilization metrics
                if location.get("max_volume", 0) > 0:
                    location["volume_utilization"] = (location["calculated_volume"] / location["max_volume"]) * 100
                else:
                    location["volume_utilization"] = 0
                
                if location.get("max_weight", 0) > 0:
                    location["weight_utilization"] = (location["calculated_weight"] / location["max_weight"]) * 100
                else:
                    location["weight_utilization"] = 0
                
                if location.get("max_hu_slot", 0) > 0:
                    location["hu_utilization"] = (location["current_hu_count"] / location["max_hu_slot"]) * 100
                else:
                    location["hu_utilization"] = 0
                
                # Overall utilization
                location["overall_utilization"] = max(
                    location["volume_utilization"],
                    location["weight_utilization"],
                    location["hu_utilization"]
                )
            
            # Categorize locations
            overutilized = [loc for loc in locations if loc["overall_utilization"] > 85]
            underutilized = [loc for loc in locations if loc["overall_utilization"] < 50]
            balanced = [loc for loc in locations if 50 <= loc["overall_utilization"] <= 85]
            
            return {
                "total_locations": len(locations),
                "overutilized_count": len(overutilized),
                "underutilized_count": len(underutilized),
                "balanced_count": len(balanced),
                "overutilized_locations": overutilized,
                "underutilized_locations": underutilized,
                "balanced_locations": balanced,
                "all_locations": locations
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting capacity status: {str(e)}")
            return {"error": str(e)}
    
    def _identify_optimization_opportunities(
        self, 
        capacity_status: Dict[str, Any], 
        optimization_type: str
    ) -> List[Dict[str, Any]]:
        """Identify specific optimization opportunities"""
        opportunities = []
        
        overutilized = capacity_status.get("overutilized_locations", [])
        underutilized = capacity_status.get("underutilized_locations", [])
        
        # Find relocation opportunities
        for over_loc in overutilized:
            for under_loc in underutilized:
                # Check if they can be optimized together
                opportunity = self._analyze_relocation_opportunity(over_loc, under_loc, optimization_type)
                if opportunity:
                    opportunities.append(opportunity)
        
        # Find consolidation opportunities
        consolidation_opportunities = self._find_consolidation_opportunities(
            capacity_status.get("all_locations", []), optimization_type
        )
        opportunities.extend(consolidation_opportunities)
        
        # Find load balancing opportunities
        load_balancing_opportunities = self._find_load_balancing_opportunities(
            capacity_status.get("all_locations", []), optimization_type
        )
        opportunities.extend(load_balancing_opportunities)
        
        return opportunities
    
    def _analyze_relocation_opportunity(
        self, 
        over_loc: Dict[str, Any], 
        under_loc: Dict[str, Any], 
        optimization_type: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze potential relocation between locations"""
        try:
            # Check if locations are compatible
            if not self._are_locations_compatible(over_loc, under_loc):
                return None
            
            # Calculate potential improvement
            over_util = over_loc["overall_utilization"]
            under_util = under_loc["overall_utilization"]
            
            # Calculate how much we can move
            max_move_volume = min(
                over_loc["calculated_volume"] * 0.2,  # Move up to 20% from overutilized
                (under_loc["max_volume"] - under_loc["calculated_volume"]) * 0.8  # Fill up to 80% of underutilized
            )
            
            if max_move_volume <= 0:
                return None
            
            # Calculate new utilization levels
            new_over_util = max(0, over_util - (max_move_volume / over_loc["max_volume"]) * 100)
            new_under_util = min(100, under_util + (max_move_volume / under_loc["max_volume"]) * 100)
            
            # Calculate improvement score
            improvement_score = self._calculate_improvement_score(
                over_util, under_util, new_over_util, new_under_util
            )
            
            if improvement_score > 0:
                return {
                    "type": "relocation",
                    "from_location": over_loc["name"],
                    "to_location": under_loc["name"],
                    "current_from_utilization": over_util,
                    "current_to_utilization": under_util,
                    "projected_from_utilization": new_over_util,
                    "projected_to_utilization": new_under_util,
                    "max_move_volume": max_move_volume,
                    "improvement_score": improvement_score,
                    "priority": "high" if improvement_score > 20 else "medium"
                }
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Error analyzing relocation opportunity: {str(e)}")
            return None
    
    def _are_locations_compatible(self, loc1: Dict[str, Any], loc2: Dict[str, Any]) -> bool:
        """Check if two locations are compatible for optimization"""
        # Same company and branch
        if loc1.get("company") != loc2.get("company") or loc1.get("branch") != loc2.get("branch"):
            return False
        
        # Same site and building (for easier movement)
        if loc1.get("site") != loc2.get("site") or loc1.get("building") != loc2.get("building"):
            return False
        
        # Both locations are available
        if loc1.get("status") != "Available" or loc2.get("status") != "Available":
            return False
        
        return True
    
    def _calculate_improvement_score(
        self, 
        over_util: float, 
        under_util: float, 
        new_over_util: float, 
        new_under_util: float
    ) -> float:
        """Calculate improvement score for optimization"""
        # Original imbalance
        original_imbalance = abs(over_util - under_util)
        
        # New imbalance
        new_imbalance = abs(new_over_util - new_under_util)
        
        # Improvement is reduction in imbalance
        improvement = original_imbalance - new_imbalance
        
        return improvement
    
    def _find_consolidation_opportunities(
        self, 
        locations: List[Dict[str, Any]], 
        optimization_type: str
    ) -> List[Dict[str, Any]]:
        """Find opportunities to consolidate items in similar locations"""
        opportunities = []
        
        # Group locations by similar characteristics
        location_groups = self._group_similar_locations(locations)
        
        for group in location_groups:
            if len(group) < 2:
                continue
            
            # Find items that could be consolidated
            consolidation_candidates = self._find_consolidation_candidates(group)
            
            for candidate in consolidation_candidates:
                opportunities.append({
                    "type": "consolidation",
                    "locations": [loc["name"] for loc in group],
                    "item": candidate["item"],
                    "total_quantity": candidate["total_quantity"],
                    "potential_savings": candidate["potential_savings"],
                    "priority": "medium"
                })
        
        return opportunities
    
    def _group_similar_locations(self, locations: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group locations with similar characteristics"""
        groups = []
        processed = set()
        
        for loc in locations:
            if loc["name"] in processed:
                continue
            
            group = [loc]
            processed.add(loc["name"])
            
            # Find similar locations
            for other_loc in locations:
                if (other_loc["name"] not in processed and 
                    other_loc["site"] == loc["site"] and 
                    other_loc["building"] == loc["building"] and
                    other_loc["zone"] == loc["zone"]):
                    group.append(other_loc)
                    processed.add(other_loc["name"])
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _find_consolidation_candidates(self, location_group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find items that could be consolidated across locations"""
        candidates = []
        
        # Get all items across the location group
        location_names = [loc["name"] for loc in location_group]
        
        items_data = frappe.db.sql("""
            SELECT 
                l.item,
                l.storage_location,
                SUM(l.quantity) as quantity,
                wi.item_name,
                wi.volume,
                wi.weight
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
            WHERE l.storage_location IN %s AND l.quantity > 0
            GROUP BY l.item, l.storage_location
        """, (location_names,), as_dict=True)
        
        # Group by item
        item_groups = {}
        for item_data in items_data:
            item = item_data["item"]
            if item not in item_groups:
                item_groups[item] = []
            item_groups[item].append(item_data)
        
        # Find items spread across multiple locations
        for item, locations in item_groups.items():
            if len(locations) > 1:
                total_quantity = sum(loc["quantity"] for loc in locations)
                total_volume = sum(loc["quantity"] * flt(loc["volume"]) for loc in locations)
                
                # Calculate potential savings (reduced handling units, better space utilization)
                potential_savings = len(locations) - 1  # One less location needed
                
                candidates.append({
                    "item": item,
                    "item_name": locations[0]["item_name"],
                    "total_quantity": total_quantity,
                    "total_volume": total_volume,
                    "current_locations": [loc["storage_location"] for loc in locations],
                    "potential_savings": potential_savings
                })
        
        return candidates
    
    def _find_load_balancing_opportunities(
        self, 
        locations: List[Dict[str, Any]], 
        optimization_type: str
    ) -> List[Dict[str, Any]]:
        """Find opportunities to balance load across locations"""
        opportunities = []
        
        # Calculate average utilization
        utilizations = [loc["overall_utilization"] for loc in locations]
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
        
        # Find locations significantly above or below average
        high_util_locations = [loc for loc in locations if loc["overall_utilization"] > avg_utilization + 20]
        low_util_locations = [loc for loc in locations if loc["overall_utilization"] < avg_utilization - 20]
        
        # Create load balancing opportunities
        for high_loc in high_util_locations:
            for low_loc in low_util_locations:
                if self._are_locations_compatible(high_loc, low_loc):
                    opportunity = {
                        "type": "load_balancing",
                        "from_location": high_loc["name"],
                        "to_location": low_loc["name"],
                        "current_imbalance": high_loc["overall_utilization"] - low_loc["overall_utilization"],
                        "priority": "medium"
                    }
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _generate_optimization_recommendations(
        self, 
        opportunities: List[Dict[str, Any]], 
        optimization_type: str
    ) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations"""
        recommendations = []
        
        # Sort opportunities by improvement score and priority
        sorted_opportunities = sorted(
            opportunities, 
            key=lambda x: (x.get("improvement_score", 0), x.get("priority", "low") == "high"), 
            reverse=True
        )
        
        for opportunity in sorted_opportunities[:10]:  # Top 10 opportunities
            if opportunity["type"] == "relocation":
                recommendations.append({
                    "action": "relocate_items",
                    "description": f"Move items from {opportunity['from_location']} to {opportunity['to_location']}",
                    "expected_improvement": f"Reduce utilization from {opportunity['current_from_utilization']:.1f}% to {opportunity['projected_from_utilization']:.1f}%",
                    "priority": opportunity["priority"],
                    "implementation_effort": "medium"
                })
            elif opportunity["type"] == "consolidation":
                recommendations.append({
                    "action": "consolidate_items",
                    "description": f"Consolidate {opportunity['item']} across {len(opportunity['locations'])} locations",
                    "expected_improvement": f"Reduce handling units by {opportunity['potential_savings']}",
                    "priority": opportunity["priority"],
                    "implementation_effort": "high"
                })
            elif opportunity["type"] == "load_balancing":
                recommendations.append({
                    "action": "balance_load",
                    "description": f"Balance load between {opportunity['from_location']} and {opportunity['to_location']}",
                    "expected_improvement": f"Reduce imbalance by {opportunity['current_imbalance']:.1f}%",
                    "priority": opportunity["priority"],
                    "implementation_effort": "medium"
                })
        
        return recommendations
    
    def _calculate_optimization_savings(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate potential savings from optimization"""
        total_recommendations = len(recommendations)
        high_priority = len([r for r in recommendations if r.get("priority") == "high"])
        medium_priority = len([r for r in recommendations if r.get("priority") == "medium"])
        
        # Estimate potential space savings (simplified calculation)
        estimated_space_savings = high_priority * 15 + medium_priority * 8  # Percentage points
        
        return {
            "total_recommendations": total_recommendations,
            "high_priority_count": high_priority,
            "medium_priority_count": medium_priority,
            "estimated_space_savings": f"{estimated_space_savings}%",
            "estimated_efficiency_gain": f"{min(25, estimated_space_savings * 0.8)}%"
        }
    
    def _generate_optimization_actions(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate specific actions to implement optimizations"""
        actions = []
        
        for i, recommendation in enumerate(recommendations[:5]):  # Top 5 actions
            action = {
                "sequence": i + 1,
                "action_type": recommendation["action"],
                "description": recommendation["description"],
                "priority": recommendation["priority"],
                "estimated_duration": "2-4 hours" if recommendation["implementation_effort"] == "medium" else "4-8 hours",
                "required_resources": ["warehouse_operator", "forklift"] if recommendation["implementation_effort"] == "high" else ["warehouse_operator"],
                "expected_outcome": recommendation["expected_improvement"]
            }
            actions.append(action)
        
        return actions
    
    def _calculate_optimization_score(self, capacity_status: Dict[str, Any]) -> float:
        """Calculate overall optimization score"""
        total_locations = capacity_status.get("total_locations", 0)
        if total_locations == 0:
            return 0.0
        
        overutilized_count = capacity_status.get("overutilized_count", 0)
        underutilized_count = capacity_status.get("underutilized_count", 0)
        
        # Calculate imbalance ratio
        imbalance_ratio = (overutilized_count + underutilized_count) / total_locations
        
        # Optimization score (higher is better)
        optimization_score = (1 - imbalance_ratio) * 100
        
        return max(0, min(100, optimization_score))


# API Functions
@frappe.whitelist()
def optimize_warehouse_capacity(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    site: Optional[str] = None,
    building: Optional[str] = None,
    zone: Optional[str] = None,
    optimization_type: str = "balanced"
) -> Dict[str, Any]:
    """API function to optimize warehouse capacity"""
    try:
        optimizer = CapacityOptimizer()
        return optimizer.optimize_warehouse_capacity(
            company, branch, site, building, zone, optimization_type
        )
    except Exception as e:
        frappe.log_error(f"Capacity optimization API error: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def get_capacity_optimization_status(
    company: Optional[str] = None,
    branch: Optional[str] = None
) -> Dict[str, Any]:
    """Get current capacity optimization status"""
    try:
        optimizer = CapacityOptimizer()
        status = optimizer._get_capacity_status(company, branch)
        return {
            "status": status,
            "optimization_score": optimizer._calculate_optimization_score(status),
            "generated_at": now_datetime()
        }
    except Exception as e:
        frappe.log_error(f"Capacity optimization status API error: {str(e)}")
        return {"error": str(e)}
