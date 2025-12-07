"""
Global Settings and Configuration
=================================
Central configuration management for the analytics platform.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import yaml
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CLIENTS_DIR = CONFIG_DIR / "clients"
CREDENTIALS_DIR = BASE_DIR / "credentials"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR / ".cache"

# Ensure directories exist
for dir_path in [CLIENTS_DIR, CREDENTIALS_DIR, OUTPUT_DIR, CACHE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


@dataclass
class IntegrationConfig:
    """Configuration for optional integrations."""
    
    # Hotjar settings
    hotjar_enabled: bool = False
    hotjar_site_id: Optional[str] = None
    hotjar_api_token: Optional[str] = None
    
    # Google Ads settings
    google_ads_enabled: bool = False
    google_ads_customer_id: Optional[str] = None
    google_ads_developer_token: Optional[str] = None
    google_ads_use_ga4_fallback: bool = True  # Try to get Ads data from GA4
    
    # PageSpeed settings
    pagespeed_enabled: bool = True  # Enabled by default (free, no auth needed)
    pagespeed_api_key: Optional[str] = None  # Optional, for higher rate limits
    pagespeed_analyze_pages: list = field(default_factory=lambda: ["/"])
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntegrationConfig":
        """Create from dictionary, handling missing keys gracefully."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


@dataclass
class ClientConfig:
    """Configuration for a single client."""
    
    # Required settings
    name: str
    display_name: str
    ga4_property_id: str
    gsc_site_url: str
    credentials_file: str
    
    # Branding
    primary_color: str = "#F4C430"  # Honey gold default
    secondary_color: str = "#2D5016"  # Forest green
    logo_path: Optional[str] = None
    timezone: str = "America/New_York"
    
    # Report customization
    homepage_paths: list = field(default_factory=lambda: ["/", "/home"])
    exclude_paths: list = field(default_factory=lambda: ["/admin", "/wp-admin"])
    
    # Optional integrations (loaded separately)
    integrations: IntegrationConfig = field(default_factory=IntegrationConfig)
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ClientConfig":
        """Load client config from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Extract integration config if present
        integrations_data = data.pop("integrations", {})
        
        # Handle old-style flat config (backwards compatibility)
        integration_keys = [
            "hotjar_enabled", "hotjar_site_id", "hotjar_api_token",
            "google_ads_enabled", "google_ads_customer_id", "google_ads_developer_token",
            "google_ads_use_ga4_fallback", "pagespeed_enabled", "pagespeed_api_key",
            "pagespeed_analyze_pages"
        ]
        for key in integration_keys:
            if key in data:
                integrations_data[key] = data.pop(key)
        
        # Create integration config
        integrations = IntegrationConfig.from_dict(integrations_data)
        
        # Filter out any unknown keys to prevent errors
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()} - {"integrations"}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data, integrations=integrations)
    
    def get_credentials_path(self) -> Path:
        """Get full path to credentials file."""
        return CREDENTIALS_DIR / self.credentials_file
    
    def has_hotjar(self) -> bool:
        """Check if Hotjar is configured."""
        return (
            self.integrations.hotjar_enabled and
            self.integrations.hotjar_site_id and
            self.integrations.hotjar_api_token
        )
    
    def has_google_ads(self) -> bool:
        """Check if Google Ads is configured (direct API)."""
        return (
            self.integrations.google_ads_enabled and
            self.integrations.google_ads_customer_id and
            self.integrations.google_ads_developer_token
        )
    
    def has_pagespeed(self) -> bool:
        """Check if PageSpeed is enabled."""
        return self.integrations.pagespeed_enabled


@dataclass
class Settings:
    """Global application settings."""
    
    # API Settings
    api_retry_count: int = 3
    api_retry_delay: float = 1.0
    api_timeout: int = 30
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    
    # Report settings
    default_row_limit: int = 100
    top_keywords_limit: int = 25
    top_pages_limit: int = 20
    
    # Benchmark data (typical nonprofit averages)
    benchmarks: dict = field(default_factory=lambda: {
        "bounce_rate": 55.0,  # Average nonprofit bounce rate
        "avg_session_duration": 120.0,  # 2 minutes
        "pages_per_session": 2.5,
        "new_visitor_rate": 70.0,
        "mobile_traffic_share": 55.0,
        "organic_traffic_share": 40.0,
        # PageSpeed benchmarks
        "mobile_performance_score": 50.0,
        "desktop_performance_score": 70.0,
        "lcp_threshold": 2.5,  # Good LCP is under 2.5s
        "cls_threshold": 0.1,  # Good CLS is under 0.1
    })
    
    # Insight thresholds
    significant_change_threshold: float = 10.0  # % change to flag
    anomaly_threshold: float = 25.0  # % change for anomaly alert
    
    def load_client(self, client_name: str) -> ClientConfig:
        """Load a specific client configuration."""
        yaml_path = CLIENTS_DIR / f"{client_name}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Client config not found: {yaml_path}")
        return ClientConfig.from_yaml(yaml_path)
    
    def list_clients(self) -> list[str]:
        """List all available client configurations."""
        return [f.stem for f in CLIENTS_DIR.glob("*.yaml")]


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
