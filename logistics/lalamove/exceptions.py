# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Custom exceptions for Lalamove integration
"""


class LalamoveException(Exception):
    """Base exception for Lalamove integration"""
    pass


class LalamoveAPIException(LalamoveException):
    """Exception raised for API-related errors"""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class LalamoveAuthenticationException(LalamoveAPIException):
    """Exception raised for authentication errors"""
    pass


class LalamoveValidationException(LalamoveException):
    """Exception raised for validation errors"""
    pass


class LalamoveQuotationExpiredException(LalamoveException):
    """Exception raised when quotation has expired"""
    pass


class LalamoveOrderException(LalamoveException):
    """Exception raised for order-related errors"""
    pass


