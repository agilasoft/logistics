# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
On-demand Delivery Services (ODDS) Module

Generic integration system for multiple on-demand delivery service providers:
- Lalamove
- Transportify
- GrabExpress
- PandaGo
- NinjaVAN
"""

from .base import ODDSProvider, ODDSClient, ODDSService, ODDSMapper
from .exceptions import (
    ODDSException,
    ODDSAPIException,
    ODDSAuthenticationException,
    ODDSQuotationExpiredException,
    ODDSOrderException
)

__all__ = [
    "ODDSProvider",
    "ODDSClient",
    "ODDSService",
    "ODDSMapper",
    "ODDSException",
    "ODDSAPIException",
    "ODDSAuthenticationException",
    "ODDSQuotationExpiredException",
    "ODDSOrderException"
]

