# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
PandaGo Provider Implementation

ODDS provider for PandaGo on-demand delivery service.
"""

import frappe
from typing import Dict, Any
from ..base import ODDSProvider, ODDSClient, ODDSMapper
from ..exceptions import ODDSProviderNotSupportedException


class PandaGoProvider(ODDSProvider):
    """PandaGo provider implementation (stub)"""
    
    @property
    def provider_name(self) -> str:
        return "PandaGo"
    
    @property
    def provider_code(self) -> str:
        return "pandago"
    
    def get_client(self, settings: Dict[str, Any] = None) -> ODDSClient:
        """Get PandaGo API client"""
        # TODO: Implement PandaGo client
        raise ODDSProviderNotSupportedException("PandaGo provider not yet implemented")
    
    def get_mapper(self) -> ODDSMapper:
        """Get PandaGo mapper"""
        # TODO: Implement PandaGo mapper
        raise ODDSProviderNotSupportedException("PandaGo provider not yet implemented")
    
    def get_settings_doctype(self) -> str:
        return "ODDS Settings"

