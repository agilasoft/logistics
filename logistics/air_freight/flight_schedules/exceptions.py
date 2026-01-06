# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

class FlightScheduleException(Exception):
	"""Base exception for flight schedule operations"""
	pass

class APIConnectionError(FlightScheduleException):
	"""Raised when API connection fails"""
	pass

class APIAuthenticationError(FlightScheduleException):
	"""Raised when API authentication fails"""
	pass

class APIRateLimitError(FlightScheduleException):
	"""Raised when API rate limit is exceeded"""
	pass

class DataValidationError(FlightScheduleException):
	"""Raised when data validation fails"""
	pass

class FlightNotFoundError(FlightScheduleException):
	"""Raised when flight is not found"""
	pass

class AirportNotFoundError(FlightScheduleException):
	"""Raised when airport is not found"""
	pass

class AirlineNotFoundError(FlightScheduleException):
	"""Raised when airline is not found"""
	pass


