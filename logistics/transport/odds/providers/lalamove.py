# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Lalamove Provider Implementation

ODDS provider for Lalamove on-demand delivery service.
Self-contained - no dependencies on old logistics/lalamove code.
"""

import frappe
from typing import Dict, Any
from ..base import ODDSProvider, ODDSClient, ODDSMapper
from .lalamove_client_standalone import LalamoveClientStandalone
from .lalamove_mapper_standalone import LalamoveMapperStandalone


class LalamoveProvider(ODDSProvider):
    """Lalamove provider implementation - self-contained"""
    
    @property
    def provider_name(self) -> str:
        return "Lalamove"
    
    @property
    def provider_code(self) -> str:
        return "lalamove"
    
    def get_client(self, settings: Dict[str, Any] = None) -> ODDSClient:
        """Get Lalamove API client"""
        if settings is None:
            settings = self._get_settings()
        return LalamoveClientStandalone(settings)
    
    def get_mapper(self) -> ODDSMapper:
        """Get Lalamove mapper"""
        return LalamoveMapperStandalone()
    
    def get_settings_doctype(self) -> str:
        return "ODDS Settings"
    
    def _get_settings(self) -> Dict[str, Any]:
        """Get Lalamove settings from ODDS Settings or legacy Lalamove Settings"""
        try:
            from frappe.utils.password import get_decrypted_password
            
            # Try ODDS Settings first
            try:
                settings = frappe.get_single("ODDS Settings")
                if hasattr(settings, "lalamove_enabled") and settings.lalamove_enabled:
                    api_secret = get_decrypted_password(
                        "ODDS Settings",
                        "ODDS Settings",
                        "lalamove_api_secret",
                        raise_exception=False
                    )
                    return {
                        "api_key": settings.lalamove_api_key,
                        "api_secret": api_secret,
                        "environment": settings.lalamove_environment or "sandbox",
                        "market": settings.lalamove_market or "HK_HKG"
                    }
            except Exception:
                pass
            
            # Fallback to legacy Lalamove Settings (for backward compatibility)
            try:
                settings = frappe.get_single("Lalamove Settings")
                if not settings.enabled:
                    raise Exception("Lalamove integration is not enabled")
                
                api_secret = get_decrypted_password(
                    "Lalamove Settings",
                    "Lalamove Settings",
                    "api_secret",
                    raise_exception=False
                )
                
                return {
                    "api_key": settings.api_key,
                    "api_secret": api_secret,
                    "environment": settings.environment or "sandbox",
                    "market": settings.market or "HK_HKG"
                }
            except Exception:
                pass
            
            raise Exception("Lalamove settings not found")
            
        except Exception as e:
            frappe.log_error(f"Error getting Lalamove settings: {str(e)}", "Lalamove Settings Error")
            raise

