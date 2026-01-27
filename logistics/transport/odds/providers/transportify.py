# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Transportify Provider Implementation

ODDS provider for Transportify on-demand delivery service using Deliveree API.
API Documentation: https://developers.deliveree.com/
"""

import frappe
from typing import Dict, Any
from ..base import ODDSProvider, ODDSClient, ODDSMapper
from .transportify_client import TransportifyClient
from .transportify_mapper import TransportifyMapper


class TransportifyProvider(ODDSProvider):
    """Transportify provider implementation using Deliveree API"""
    
    @property
    def provider_name(self) -> str:
        return "Transportify"
    
    @property
    def provider_code(self) -> str:
        return "transportify"
    
    def get_client(self, settings: Dict[str, Any] = None) -> ODDSClient:
        """Get Transportify API client"""
        if settings is None:
            settings = self._get_settings()
        return TransportifyClient(settings)
    
    def get_mapper(self) -> ODDSMapper:
        """Get Transportify mapper"""
        return TransportifyMapper()
    
    def get_settings_doctype(self) -> str:
        return "ODDS Settings"
    
    def _get_settings(self) -> Dict[str, Any]:
        """Get Transportify settings from ODDS Settings"""
        try:
            settings = frappe.get_single("ODDS Settings")
            
            if not settings.transportify_enabled:
                raise Exception("Transportify integration is not enabled")
            
            return {
                "api_key": settings.transportify_api_key,
                "environment": settings.transportify_environment or "sandbox"
            }
        except Exception as e:
            frappe.log_error(f"Error getting Transportify settings: {str(e)}", "Transportify Settings Error")
            raise

