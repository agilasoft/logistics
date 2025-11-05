# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate
from frappe import _


class SustainabilityGoals(Document):
	def before_save(self):
		"""Calculate progress and update status before saving"""
		self.calculate_progress()
		self.update_status()
	
	def calculate_progress(self):
		"""Calculate progress percentage based on current and target values"""
		if not self.target_value or self.target_value == 0:
			self.progress_percentage = 0
			return
		
		if not self.current_value:
			self.current_value = 0
		
		# Calculate progress based on goal type
		if self.goal_type in ["Energy Efficiency", "Renewable Energy"]:
			# For efficiency goals, higher is better
			if self.baseline_value and self.baseline_value > 0:
				baseline_progress = ((self.current_value - self.baseline_value) / self.baseline_value) * 100
				target_progress = ((self.target_value - self.baseline_value) / self.baseline_value) * 100
				if target_progress > 0:
					self.progress_percentage = min(100, (baseline_progress / target_progress) * 100)
				else:
					self.progress_percentage = 0
			else:
				self.progress_percentage = min(100, (self.current_value / self.target_value) * 100)
		else:
			# For reduction goals, lower is better
			if self.baseline_value and self.baseline_value > 0:
				reduction_achieved = ((self.baseline_value - self.current_value) / self.baseline_value) * 100
				target_reduction = ((self.baseline_value - self.target_value) / self.baseline_value) * 100
				if target_reduction > 0:
					self.progress_percentage = min(100, (reduction_achieved / target_reduction) * 100)
				else:
					self.progress_percentage = 0
			else:
				self.progress_percentage = min(100, (self.current_value / self.target_value) * 100)
	
	def update_status(self):
		"""Update status based on progress and target date"""
		if not self.target_date:
			return
		
		today = getdate()
		progress = self.progress_percentage or 0
		
		if progress >= 100:
			self.status = "Completed"
		elif self.target_date < today:
			if progress >= 80:
				self.status = "At Risk"
			else:
				self.status = "At Risk"
		elif progress >= 80:
			self.status = "On Track"
		elif progress >= 50:
			self.status = "In Progress"
		else:
			self.status = "Not Started"
	
	def get_remaining_value(self):
		"""Get remaining value to achieve target"""
		if not self.target_value or not self.current_value:
			return self.target_value or 0
		
		if self.goal_type in ["Energy Efficiency", "Renewable Energy"]:
			# For efficiency goals, higher is better
			return max(0, self.target_value - self.current_value)
		else:
			# For reduction goals, lower is better
			return max(0, self.current_value - self.target_value)
	
	def get_days_remaining(self):
		"""Get days remaining to target date"""
		if not self.target_date:
			return None
		
		today = getdate()
		if self.target_date < today:
			return 0
		
		return (self.target_date - today).days
	
	def get_required_daily_progress(self):
		"""Get required daily progress to achieve target"""
		days_remaining = self.get_days_remaining()
		if not days_remaining or days_remaining <= 0:
			return 0
		
		remaining_value = self.get_remaining_value()
		if not remaining_value or remaining_value <= 0:
			return 0
		
		return remaining_value / days_remaining


@frappe.whitelist()
def get_sustainability_goals_summary(module=None, branch=None, facility=None):
	"""Get sustainability goals summary for a specific module or all modules"""
	
	filters = {}
	if module:
		filters["module"] = module
	if branch:
		filters["branch"] = branch
	if facility:
		filters["facility"] = facility
	
	# Get sustainability goals
	goals = frappe.get_all("Sustainability Goals",
		filters=filters,
		fields=["*"],
		order_by="target_date asc"
	)
	
	# Calculate summary statistics
	summary = {
		"total_goals": len(goals),
		"completed_goals": 0,
		"in_progress_goals": 0,
		"at_risk_goals": 0,
		"not_started_goals": 0,
		"average_progress": 0,
		"goals_by_type": {},
		"goals_by_status": {}
	}
	
	if goals:
		# Count goals by status
		for goal in goals:
			status = goal.status or "Not Started"
			if status not in summary["goals_by_status"]:
				summary["goals_by_status"][status] = 0
			summary["goals_by_status"][status] += 1
			
			# Count by type
			goal_type = goal.goal_type or "Other"
			if goal_type not in summary["goals_by_type"]:
				summary["goals_by_type"][goal_type] = 0
			summary["goals_by_type"][goal_type] += 1
		
		# Calculate counts
		summary["completed_goals"] = summary["goals_by_status"].get("Completed", 0)
		summary["in_progress_goals"] = summary["goals_by_status"].get("In Progress", 0)
		summary["at_risk_goals"] = summary["goals_by_status"].get("At Risk", 0)
		summary["not_started_goals"] = summary["goals_by_status"].get("Not Started", 0)
		
		# Calculate average progress
		progress_values = [flt(g.progress_percentage) for g in goals if g.progress_percentage]
		if progress_values:
			summary["average_progress"] = sum(progress_values) / len(progress_values)
	
	return {
		"goals": goals,
		"summary": summary
	}


@frappe.whitelist()
def create_sustainability_goal(goal_name, goal_type, target_value, unit_of_measure, target_date, **kwargs):
	"""Create a new sustainability goal"""
	
	doc = frappe.new_doc("Sustainability Goals")
	doc.goal_name = goal_name
	doc.goal_type = goal_type
	doc.target_value = flt(target_value)
	doc.unit_of_measure = unit_of_measure
	doc.target_date = target_date
	doc.module = kwargs.get("module", "All")
	doc.branch = kwargs.get("branch")
	doc.facility = kwargs.get("facility")
	doc.company = kwargs.get("company", frappe.defaults.get_user_default("Company"))
	doc.baseline_value = flt(kwargs.get("baseline_value", 0))
	doc.baseline_date = kwargs.get("baseline_date")
	doc.current_value = flt(kwargs.get("current_value", 0))
	doc.description = kwargs.get("description")
	doc.action_plan = kwargs.get("action_plan")
	doc.responsible_person = kwargs.get("responsible_person")
	doc.notes = kwargs.get("notes")
	
	doc.insert(ignore_permissions=True)
	return doc.name
