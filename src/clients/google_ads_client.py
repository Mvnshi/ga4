"""
Google Ads API Client
======================
Google Ads data for paid search performance.

This is especially valuable for nonprofits using the Google Ad Grants program
($10,000/month in free Google Ads for eligible nonprofits).

Note: The Google Ads API requires:
1. A Google Ads manager account
2. Developer token (from Google Ads API Center)
3. OAuth credentials OR service account with domain-wide delegation

For simpler access, we also support fetching Ads data through GA4
if the accounts are linked.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import requests

from config.settings import ClientConfig, get_settings
from src.utils.cache import cached


@dataclass
class CampaignMetrics:
    """Metrics for a single campaign."""
    campaign_id: str
    campaign_name: str
    status: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    ctr: float
    avg_cpc: float
    conversion_rate: float


@dataclass
class AdGroupMetrics:
    """Metrics for an ad group."""
    ad_group_id: str
    ad_group_name: str
    campaign_name: str
    impressions: int
    clicks: int
    ctr: float
    avg_cpc: float


class GoogleAdsClient:
    """
    Google Ads API client.
    
    Provides campaign performance data for quarterly reports.
    
    Note: Full Google Ads API setup is complex. This client also supports
    a "lite" mode that pulls Ads data from GA4 (if linked).
    """
    
    def __init__(
        self,
        client_config: ClientConfig,
        customer_id: str = None,
        developer_token: str = None,
        use_ga4_fallback: bool = True
    ):
        """
        Initialize Google Ads client.
        
        Args:
            client_config: Client configuration
            customer_id: Google Ads Customer ID (without dashes)
            developer_token: Google Ads API developer token
            use_ga4_fallback: If True, try to get Ads data from GA4 if direct API unavailable
        """
        self.config = client_config
        self.client_name = client_config.name
        self.customer_id = customer_id
        self.developer_token = developer_token
        self.use_ga4_fallback = use_ga4_fallback
        self._settings = get_settings()
        
        # Check if full Ads API is configured
        self.is_configured = bool(customer_id and developer_token)
        
        # GA4 client for fallback (lazy loaded)
        self._ga4_client = None
    
    def _get_ga4_client(self):
        """Lazy load GA4 client for fallback data."""
        if self._ga4_client is None:
            try:
                from src.clients.ga4_client import GA4Client
                self._ga4_client = GA4Client(self.config)
            except Exception:
                pass
        return self._ga4_client
    
    @cached(ttl_hours=24)
    def get_campaign_performance(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get campaign performance data.
        
        Tries direct API first, falls back to GA4 data if available.
        """
        # Try direct Google Ads API
        if self.is_configured:
            result = self._fetch_from_ads_api(start_date, end_date)
            if result.get("available"):
                return result
        
        # Fallback to GA4 data
        if self.use_ga4_fallback:
            return self._fetch_from_ga4(start_date, end_date)
        
        return {
            "available": False,
            "reason": "Google Ads not configured and GA4 fallback disabled"
        }
    
    def _fetch_from_ads_api(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Fetch data directly from Google Ads API.
        
        Note: Full implementation requires google-ads library and OAuth setup.
        This is a simplified placeholder that shows the structure.
        """
        try:
            # This would require the google-ads library and proper auth
            # For now, return unavailable and let GA4 fallback handle it
            
            # Full implementation would be:
            # from google.ads.googleads.client import GoogleAdsClient
            # client = GoogleAdsClient.load_from_storage()
            # ... query campaigns ...
            
            return {
                "available": False,
                "reason": "Direct Google Ads API not implemented - using GA4 fallback"
            }
            
        except Exception as e:
            return {
                "available": False,
                "reason": f"Google Ads API error: {str(e)}"
            }
    
    def _fetch_from_ga4(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Fetch Ads data from GA4 (if accounts are linked).
        
        This provides good campaign-level data without complex Ads API setup.
        """
        ga4 = self._get_ga4_client()
        
        if ga4 is None:
            return {
                "available": False,
                "reason": "GA4 client not available for fallback"
            }
        
        try:
            # Get paid search overview
            paid_overview = ga4.get_paid_search_overview(start_date, end_date)
            
            # Get campaign breakdown
            campaigns_df = ga4.get_campaign_performance(start_date, end_date)
            
            campaigns = []
            if campaigns_df is not None and not campaigns_df.empty:
                for _, row in campaigns_df.iterrows():
                    campaigns.append({
                        "name": row.get("sessionCampaignName", "Unknown"),
                        "sessions": int(row.get("sessions", 0)),
                        "users": int(row.get("totalUsers", 0)),
                        "new_users": int(row.get("newUsers", 0)),
                        "bounce_rate": round(row.get("bounceRate", 0), 2),
                        "engagement_rate": round(row.get("engagementRate", 0), 2),
                    })
            
            return {
                "available": True,
                "source": "ga4",
                "overview": paid_overview,
                "campaigns": campaigns,
                "summary": {
                    "total_sessions": paid_overview.get("sessions", 0),
                    "total_users": paid_overview.get("users", 0),
                    "bounce_rate": paid_overview.get("bounce_rate", 0),
                    "avg_session_duration": paid_overview.get("avg_session_duration", 0),
                    "campaign_count": len(campaigns),
                }
            }
            
        except Exception as e:
            return {
                "available": False,
                "reason": f"Error fetching from GA4: {str(e)}"
            }
    
    def get_ad_grants_status(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Check Ad Grants utilization (for nonprofits).
        
        Google Ad Grants provides $10,000/month = ~$329/day budget.
        This helps track if the nonprofit is utilizing their grant.
        """
        data = self.get_campaign_performance(start_date, end_date)
        
        if not data.get("available"):
            return data
        
        # Ad Grants specifics
        monthly_grant = 10000
        daily_grant = monthly_grant / 30.4
        
        # Calculate date range days
        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days + 1
        
        total_budget_available = daily_grant * days
        
        # Note: Without direct Ads API, we can't get actual spend
        # We can only report on what GA4 shows
        
        return {
            "available": True,
            "grant_info": {
                "monthly_budget": monthly_grant,
                "daily_budget": round(daily_grant, 2),
                "period_days": days,
                "period_budget_available": round(total_budget_available, 2),
            },
            "performance": data.get("summary", {}),
            "campaigns": data.get("campaigns", []),
            "note": "Actual spend data requires direct Google Ads API connection"
        }
    
    def get_all_ads_data(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get all available Google Ads data for quarterly reports.
        """
        print("    💰 Fetching Google Ads data...")
        
        performance = self.get_campaign_performance(start_date, end_date)
        
        if not performance.get("available"):
            return performance
        
        return {
            "available": True,
            "source": performance.get("source", "unknown"),
            "performance": performance,
            "summary": performance.get("summary", {}),
        }


class GoogleAdsClientDisabled:
    """
    Placeholder client when Google Ads is not configured.
    """
    
    def __init__(self, *args, **kwargs):
        self.is_configured = False
    
    def get_campaign_performance(self, *args, **kwargs) -> Dict:
        return {"available": False, "reason": "Google Ads not configured"}
    
    def get_ad_grants_status(self, *args, **kwargs) -> Dict:
        return {"available": False, "reason": "Google Ads not configured"}
    
    def get_all_ads_data(self, *args, **kwargs) -> Dict:
        return {"available": False, "reason": "Google Ads not configured"}


def create_google_ads_client(
    client_config: ClientConfig,
    customer_id: str = None,
    developer_token: str = None,
    use_ga4_fallback: bool = True
) -> GoogleAdsClient:
    """
    Factory function to create appropriate Google Ads client.
    
    Even without direct Ads API credentials, if use_ga4_fallback is True,
    will try to get Ads data from GA4.
    """
    # Always create full client if GA4 fallback is enabled
    if use_ga4_fallback or (customer_id and developer_token):
        return GoogleAdsClient(
            client_config,
            customer_id,
            developer_token,
            use_ga4_fallback
        )
    return GoogleAdsClientDisabled()

