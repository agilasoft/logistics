# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Custom exceptions for ODDS integration
"""


class ODDSException(Exception):
    """Base exception for ODDS integration"""
    pass


class ODDSAPIException(ODDSException):
    """Exception raised for API-related errors"""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None, provider: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
        self.provider = provider


class ODDSAuthenticationException(ODDSAPIException):
    """Exception raised for authentication errors"""
    pass


class ODDSValidationException(ODDSException):
    """Exception raised for validation errors"""
    pass


class ODDSQuotationExpiredException(ODDSException):
    """Exception raised when quotation has expired"""
    pass


class ODDSOrderException(ODDSException):
    """Exception raised for order-related errors"""
    pass


class ODDSProviderNotSupportedException(ODDSException):
    """Exception raised when provider is not supported"""
    pass

