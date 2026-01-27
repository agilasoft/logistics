# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
ODDS Provider Registry

Manages registration and retrieval of ODDS providers.
"""

from typing import Dict, Optional
from ..base import ODDSProvider
from ..exceptions import ODDSProviderNotSupportedException

# Provider registry
_providers: Dict[str, ODDSProvider] = {}


def register_provider(provider: ODDSProvider):
    """Register an ODDS provider"""
    _providers[provider.provider_code] = provider


def get_provider(provider_code: str) -> ODDSProvider:
    """
    Get provider by code
    
    Args:
        provider_code: Provider code (e.g., 'lalamove')
        
    Returns:
        ODDSProvider instance
        
    Raises:
        ODDSProviderNotSupportedException: If provider is not registered
    """
    provider = _providers.get(provider_code.lower())
    if not provider:
        raise ODDSProviderNotSupportedException(
            f"Provider '{provider_code}' is not supported. Available providers: {', '.join(_providers.keys())}"
        )
    return provider


def get_all_providers() -> Dict[str, ODDSProvider]:
    """Get all registered providers"""
    return _providers.copy()


def is_provider_supported(provider_code: str) -> bool:
    """Check if provider is supported"""
    return provider_code.lower() in _providers


# Import and register providers
def _register_all_providers():
    """Register all available providers"""
    try:
        from .lalamove import LalamoveProvider
        register_provider(LalamoveProvider())
    except ImportError:
        pass
    
    try:
        from .transportify import TransportifyProvider
        register_provider(TransportifyProvider())
    except ImportError:
        pass
    
    try:
        from .grabexpress import GrabExpressProvider
        register_provider(GrabExpressProvider())
    except ImportError:
        pass
    
    try:
        from .pandago import PandaGoProvider
        register_provider(PandaGoProvider())
    except ImportError:
        pass
    
    try:
        from .ninjavan import NinjaVANProvider
        register_provider(NinjaVANProvider())
    except ImportError:
        pass


# Auto-register on import
_register_all_providers()

