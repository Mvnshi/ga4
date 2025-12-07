"""
Global Settings and Configuration
=================================
Central configuration management for the analytics platform.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
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
class ClientConfig:
    """Configuration for a single client."""
    name: str
    display_name: str
    ga4_property_id: str
    gsc_site_url: str
    credentials_file: str
    
    # Optional customization
    primary_color: str = "#F4C430"  # Honey gold default
    secondary_color: str = "#2D5016"  # Forest green
    logo_path: Optional[str] = None
    timezone: str = "America/New_York"
    
    # Report customization
    homepage_paths: list = field(default_factory=lambda: ["/", "/home"])
    exclude_paths: list = field(default_factory=lambda: ["/admin", "/wp-admin"])
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ClientConfig":
        """Load client config from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def get_credentials_path(self) -> Path:
        """Get full path to credentials file."""
        return CREDENTIALS_DIR / self.credentials_file


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

