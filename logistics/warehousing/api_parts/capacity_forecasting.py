# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Capacity Forecasting and Analytics System
=========================================

This module provides advanced capacity forecasting, analytics, and optimization
for warehouse operations, enabling proactive capacity planning and management.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate, add_days, add_months
from datetime import datetime, timedelta
import json


class CapacityForecaster:
    """Advanced capacity forecasting and analytics"""
    
    def __init__(self):
        self.forecast_cache = {}
        self.analytics_cache = {}
    
    def generate_capacity_forecast(
        self,
        location: Optional[str] = None,
        company: Optional[str] = None,
        branch: Optional[str] = None,
        forecast_days: int = 30,
        include_seasonality: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive capacity forecast
        
        Args:
            location: Specific location to forecast (optional)
            company: Company filter (optional)
            branch: Branch filter (optional)
            forecast_days: Number of days to forecast
            include_seasonality: Include seasonal patterns
            
        Returns:
            Dict with forecast data and recommendations
        """
        try:
            # Get historical capacity data
            historical_data = self._get_historical_capacity_data(
                location, company, branch, days=90
            )
            
            # Analyze trends and patterns
            trend_analysis = self._analyze_capacity_trends(historical_data)
            
            # Generate forecast
            forecast_data = self._generate_forecast_data(
                historical_data, trend_analysis, forecast_days, include_seasonality
            )
            
            # Calculate capacity recommendations
            recommendations = self._generate_capacity_recommendations(
                forecast_data, trend_analysis
            )
            
            # Generate alerts for potential capacity issues
            alerts = self._generate_forecast_alerts(forecast_data)
            
            return {
                "forecast_period": forecast_days,
                "historical_data": historical_data,
                "trend_analysis": trend_analysis,
                "forecast_data": forecast_data,
                "recommendations": recommendations,
                "alerts": alerts,
                "generated_at": now_datetime(),
                "confidence_score": self._calculate_forecast_confidence(historical_data)
            }
            
        except Exception as e:
            frappe.log_error(f"Capacity forecasting error: {str(e)}")
            return {"error": str(e)}
    
    def _get_historical_capacity_data(
        self,
        location: Optional[str] = None,
        company: Optional[str] = None,
        branch: Optional[str] = None,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """Get historical capacity utilization data"""
        try:
            # Build filters
            filters = {}
            if location:
                filters["storage_location"] = location
            if company:
                filters["company"] = company
            if branch:
                filters["branch"] = branch
            
            # Get date range
            end_date = getdate()
            start_date = add_days(end_date, -days)
            
            # Get historical stock data
            historical_data = frappe.db.sql("""
                SELECT 
                    DATE(l.posting_date) as date,
                    l.storage_location,
                    sl.site,
                    sl.building,
                    sl.zone,
                    COUNT(DISTINCT l.handling_unit) as hu_count,
                    SUM(l.quantity) as total_quantity,
                    SUM(wi.volume * l.quantity) as total_volume,
                    SUM(wi.weight * l.quantity) as total_weight,
                    sl.max_volume,
                    sl.max_weight,
                    sl.max_hu_slot
                FROM `tabWarehouse Stock Ledger` l
                LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
                LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
                WHERE l.posting_date >= %s AND l.posting_date <= %s
                {filters}
                GROUP BY DATE(l.posting_date), l.storage_location
                ORDER BY DATE(l.posting_date), l.storage_location
            """.format(
                filters=" AND " + " AND ".join([f"{k} = %s" for k in filters.keys()]) if filters else ""
            ), 
            [start_date, end_date] + list(filters.values()),
            as_dict=True)
            
            # Calculate utilization percentages
            for record in historical_data:
                if record.get("max_volume", 0) > 0:
                    record["volume_utilization"] = (record["total_volume"] / record["max_volume"]) * 100
                else:
                    record["volume_utilization"] = 0
                
                if record.get("max_weight", 0) > 0:
                    record["weight_utilization"] = (record["total_weight"] / record["max_weight"]) * 100
                else:
                    record["weight_utilization"] = 0
                
                if record.get("max_hu_slot", 0) > 0:
                    record["hu_utilization"] = (record["hu_count"] / record["max_hu_slot"]) * 100
                else:
                    record["hu_utilization"] = 0
                
                # Overall utilization (max of all metrics)
                record["overall_utilization"] = max(
                    record["volume_utilization"],
                    record["weight_utilization"],
                    record["hu_utilization"]
                )
            
            return historical_data
            
        except Exception as e:
            frappe.log_error(f"Error getting historical capacity data: {str(e)}")
            return []
    
    def _analyze_capacity_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze capacity utilization trends"""
        if not historical_data:
            return {"trend": "insufficient_data", "growth_rate": 0, "seasonality": False}
        
        # Calculate average utilization over time
        daily_utilization = {}
        for record in historical_data:
            date = record["date"]
            if date not in daily_utilization:
                daily_utilization[date] = []
            daily_utilization[date].append(record["overall_utilization"])
        
        # Calculate daily averages
        daily_averages = {}
        for date, utilizations in daily_utilization.items():
            daily_averages[date] = sum(utilizations) / len(utilizations)
        
        # Calculate trend
        dates = sorted(daily_averages.keys())
        if len(dates) < 7:
            return {"trend": "insufficient_data", "growth_rate": 0, "seasonality": False}
        
        # Simple linear trend calculation
        recent_avg = sum(daily_averages[d] for d in dates[-7:]) / 7
        older_avg = sum(daily_averages[d] for d in dates[:7]) / 7
        growth_rate = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
        
        # Determine trend direction
        if growth_rate > 5:
            trend = "increasing"
        elif growth_rate < -5:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Check for seasonality (simplified - look for weekly patterns)
        weekly_patterns = {}
        for date in dates:
            weekday = date.weekday()
            if weekday not in weekly_patterns:
                weekly_patterns[weekday] = []
            weekly_patterns[weekday].append(daily_averages[date])
        
        # Calculate weekly variation
        weekly_avgs = {}
        for weekday, values in weekly_patterns.items():
            weekly_avgs[weekday] = sum(values) / len(values)
        
        weekly_variation = max(weekly_avgs.values()) - min(weekly_avgs.values())
        has_seasonality = weekly_variation > 10  # 10% variation indicates seasonality
        
        return {
            "trend": trend,
            "growth_rate": growth_rate,
            "seasonality": has_seasonality,
            "weekly_patterns": weekly_avgs,
            "average_utilization": sum(daily_averages.values()) / len(daily_averages),
            "peak_utilization": max(daily_averages.values()),
            "low_utilization": min(daily_averages.values())
        }
    
    def _generate_forecast_data(
        self,
        historical_data: List[Dict[str, Any]],
        trend_analysis: Dict[str, Any],
        forecast_days: int,
        include_seasonality: bool
    ) -> List[Dict[str, Any]]:
        """Generate forecast data for the specified period"""
        forecast_data = []
        
        # Get baseline utilization
        if historical_data:
            baseline_utilization = sum(record["overall_utilization"] for record in historical_data) / len(historical_data)
        else:
            baseline_utilization = 50  # Default baseline
        
        # Apply growth rate
        growth_rate = trend_analysis.get("growth_rate", 0)
        daily_growth = growth_rate / 100 / 30  # Convert monthly growth to daily
        
        # Generate forecast for each day
        start_date = getdate()
        for i in range(forecast_days):
            forecast_date = add_days(start_date, i)
            
            # Calculate base utilization with growth
            base_utilization = baseline_utilization * (1 + daily_growth * i)
            
            # Apply seasonality if enabled
            if include_seasonality and trend_analysis.get("seasonality"):
                weekday = forecast_date.weekday()
                weekly_patterns = trend_analysis.get("weekly_patterns", {})
                if weekday in weekly_patterns:
                    seasonal_factor = weekly_patterns[weekday] / baseline_utilization
                    base_utilization *= seasonal_factor
            
            # Add some randomness for realistic forecasting
            import random
            random_factor = random.uniform(0.95, 1.05)
            forecast_utilization = min(100, max(0, base_utilization * random_factor))
            
            forecast_data.append({
                "date": forecast_date,
                "predicted_utilization": forecast_utilization,
                "confidence_level": self._calculate_daily_confidence(i, forecast_days),
                "risk_level": self._assess_risk_level(forecast_utilization)
            })
        
        return forecast_data
    
    def _calculate_daily_confidence(self, day_index: int, total_days: int) -> float:
        """Calculate confidence level for forecast (decreases over time)"""
        # Confidence starts at 85% and decreases to 60% over the forecast period
        base_confidence = 85
        decline_rate = (85 - 60) / total_days
        return max(60, base_confidence - (decline_rate * day_index))
    
    def _assess_risk_level(self, utilization: float) -> str:
        """Assess risk level based on predicted utilization"""
        if utilization >= 95:
            return "critical"
        elif utilization >= 85:
            return "high"
        elif utilization >= 70:
            return "medium"
        else:
            return "low"
    
    def _generate_capacity_recommendations(
        self,
        forecast_data: List[Dict[str, Any]],
        trend_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate capacity optimization recommendations"""
        recommendations = []
        
        # Check for capacity constraints
        high_utilization_days = [d for d in forecast_data if d["predicted_utilization"] > 85]
        critical_days = [d for d in forecast_data if d["predicted_utilization"] > 95]
        
        if critical_days:
            recommendations.append({
                "type": "urgent",
                "title": "Critical Capacity Issues Predicted",
                "description": f"{len(critical_days)} days with >95% utilization predicted",
                "action": "Consider immediate capacity expansion or redistribution",
                "priority": "high"
            })
        
        if high_utilization_days:
            recommendations.append({
                "type": "warning",
                "title": "High Utilization Periods",
                "description": f"{len(high_utilization_days)} days with >85% utilization predicted",
                "action": "Plan capacity optimization or temporary storage solutions",
                "priority": "medium"
            })
        
        # Growth-based recommendations
        growth_rate = trend_analysis.get("growth_rate", 0)
        if growth_rate > 10:
            recommendations.append({
                "type": "growth",
                "title": "Rapid Growth Detected",
                "description": f"Utilization growing at {growth_rate:.1f}% rate",
                "action": "Consider proactive capacity expansion",
                "priority": "medium"
            })
        
        # Seasonality recommendations
        if trend_analysis.get("seasonality"):
            recommendations.append({
                "type": "seasonal",
                "title": "Seasonal Patterns Detected",
                "description": "Weekly utilization patterns identified",
                "action": "Implement seasonal capacity planning",
                "priority": "low"
            })
        
        return recommendations
    
    def _generate_forecast_alerts(self, forecast_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate alerts for potential capacity issues"""
        alerts = []
        
        for forecast in forecast_data:
            if forecast["risk_level"] == "critical":
                alerts.append({
                    "date": forecast["date"],
                    "type": "critical",
                    "message": f"Critical capacity risk predicted: {forecast['predicted_utilization']:.1f}% utilization",
                    "action_required": "Immediate capacity planning needed"
                })
            elif forecast["risk_level"] == "high":
                alerts.append({
                    "date": forecast["date"],
                    "type": "warning",
                    "message": f"High capacity utilization predicted: {forecast['predicted_utilization']:.1f}%",
                    "action_required": "Monitor and prepare capacity optimization"
                })
        
        return alerts
    
    def _calculate_forecast_confidence(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence in the forecast"""
        if not historical_data:
            return 0.0
        
        # More historical data = higher confidence
        data_points = len(historical_data)
        if data_points >= 60:  # 2 months of data
            return 0.9
        elif data_points >= 30:  # 1 month of data
            return 0.8
        elif data_points >= 14:  # 2 weeks of data
            return 0.7
        else:
            return 0.5
    
    def get_capacity_analytics(
        self,
        company: Optional[str] = None,
        branch: Optional[str] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive capacity analytics"""
        try:
            # Get current capacity status
            current_status = self._get_current_capacity_status(company, branch)
            
            # Get utilization trends
            utilization_trends = self._analyze_utilization_trends(company, branch, period_days)
            
            # Get capacity bottlenecks
            bottlenecks = self._identify_capacity_bottlenecks(company, branch)
            
            # Get optimization opportunities
            optimization_opportunities = self._identify_optimization_opportunities(company, branch)
            
            return {
                "current_status": current_status,
                "utilization_trends": utilization_trends,
                "bottlenecks": bottlenecks,
                "optimization_opportunities": optimization_opportunities,
                "generated_at": now_datetime()
            }
            
        except Exception as e:
            frappe.log_error(f"Capacity analytics error: {str(e)}")
            return {"error": str(e)}
    
    def _get_current_capacity_status(
        self, 
        company: Optional[str] = None, 
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current capacity status across all locations"""
        try:
            # Build filters
            filters = {}
            if company:
                filters["company"] = company
            if branch:
                filters["branch"] = branch
            
            # Get all storage locations
            locations = frappe.get_all(
                "Storage Location",
                filters=filters,
                fields=[
                    "name", "site", "building", "zone", "aisle", "bay", "level",
                    "max_volume", "max_weight", "max_hu_slot",
                    "current_volume", "current_weight", "utilization_percentage"
                ]
            )
            
            # Calculate summary statistics
            total_locations = len(locations)
            if total_locations == 0:
                return {"total_locations": 0, "average_utilization": 0}
            
            # Calculate utilization statistics
            utilizations = [flt(loc.utilization_percentage) for loc in locations if loc.utilization_percentage]
            avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
            
            # Categorize locations by utilization
            high_utilization = [loc for loc in locations if flt(loc.utilization_percentage) > 85]
            critical_utilization = [loc for loc in locations if flt(loc.utilization_percentage) > 95]
            low_utilization = [loc for loc in locations if flt(loc.utilization_percentage) < 50]
            
            return {
                "total_locations": total_locations,
                "average_utilization": avg_utilization,
                "high_utilization_count": len(high_utilization),
                "critical_utilization_count": len(critical_utilization),
                "low_utilization_count": len(low_utilization),
                "high_utilization_locations": high_utilization,
                "critical_locations": critical_utilization,
                "low_utilization_locations": low_utilization
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting current capacity status: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_utilization_trends(
        self, 
        company: Optional[str] = None, 
        branch: Optional[str] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Analyze utilization trends over time"""
        try:
            # Get historical data
            historical_data = self._get_historical_capacity_data(company=company, branch=branch, days=period_days)
            
            if not historical_data:
                return {"trend": "no_data", "growth_rate": 0}
            
            # Analyze trends
            trend_analysis = self._analyze_capacity_trends(historical_data)
            
            return trend_analysis
            
        except Exception as e:
            frappe.log_error(f"Error analyzing utilization trends: {str(e)}")
            return {"error": str(e)}
    
    def _identify_capacity_bottlenecks(
        self, 
        company: Optional[str] = None, 
        branch: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Identify capacity bottlenecks"""
        try:
            # Get locations with high utilization
            filters = {}
            if company:
                filters["company"] = company
            if branch:
                filters["branch"] = branch
            
            bottlenecks = frappe.db.sql("""
                SELECT 
                    sl.name,
                    sl.site,
                    sl.building,
                    sl.zone,
                    sl.utilization_percentage,
                    sl.max_volume,
                    sl.max_weight,
                    sl.max_hu_slot,
                    sl.current_volume,
                    sl.current_weight
                FROM `tabStorage Location` sl
                WHERE sl.utilization_percentage > 80
                ORDER BY sl.utilization_percentage DESC
                LIMIT 10
            """, as_dict=True)
            
            return bottlenecks
            
        except Exception as e:
            frappe.log_error(f"Error identifying bottlenecks: {str(e)}")
            return []
    
    def _identify_optimization_opportunities(
        self, 
        company: Optional[str] = None, 
        branch: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Identify capacity optimization opportunities"""
        try:
            # Get locations with low utilization that could be optimized
            filters = {}
            if company:
                filters["company"] = company
            if branch:
                filters["branch"] = branch
            
            opportunities = frappe.db.sql("""
                SELECT 
                    sl.name,
                    sl.site,
                    sl.building,
                    sl.zone,
                    sl.utilization_percentage,
                    sl.max_volume,
                    sl.max_weight,
                    sl.max_hu_slot
                FROM `tabStorage Location` sl
                WHERE sl.utilization_percentage < 50
                ORDER BY sl.utilization_percentage ASC
                LIMIT 10
            """, as_dict=True)
            
            return opportunities
            
        except Exception as e:
            frappe.log_error(f"Error identifying optimization opportunities: {str(e)}")
            return []


# API Functions
@frappe.whitelist()
def generate_capacity_forecast(
    location: Optional[str] = None,
    company: Optional[str] = None,
    branch: Optional[str] = None,
    forecast_days: int = 30,
    include_seasonality: bool = True
) -> Dict[str, Any]:
    """API function to generate capacity forecast"""
    try:
        forecaster = CapacityForecaster()
        return forecaster.generate_capacity_forecast(
            location, company, branch, forecast_days, include_seasonality
        )
    except Exception as e:
        frappe.log_error(f"Capacity forecast API error: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def get_capacity_analytics(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    period_days: int = 30
) -> Dict[str, Any]:
    """API function to get capacity analytics"""
    try:
        forecaster = CapacityForecaster()
        return forecaster.get_capacity_analytics(company, branch, period_days)
    except Exception as e:
        frappe.log_error(f"Capacity analytics API error: {str(e)}")
        return {"error": str(e)}
