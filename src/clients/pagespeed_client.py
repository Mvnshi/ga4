"""
PageSpeed Insights API Client
==============================
Google PageSpeed Insights for site performance analysis.

This API is FREE and doesn't require authentication for basic use!
Just needs a Google Cloud API key (not service account).

Provides:
- Performance scores (mobile/desktop)
- Core Web Vitals
- Specific recommendations
- Lighthouse audit data
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests
import time

from config.settings import ClientConfig, get_settings
from src.utils.cache import cached


@dataclass
class PerformanceMetrics:
    """Core performance metrics."""
    score: int  # 0-100
    fcp: float  # First Contentful Paint (seconds)
    lcp: float  # Largest Contentful Paint (seconds)
    tbt: float  # Total Blocking Time (ms)
    cls: float  # Cumulative Layout Shift
    si: float   # Speed Index (seconds)
    tti: float  # Time to Interactive (seconds)


@dataclass
class PageSpeedResult:
    """Complete PageSpeed result."""
    url: str
    strategy: str  # "mobile" or "desktop"
    performance_score: int
    metrics: PerformanceMetrics
    opportunities: List[Dict[str, Any]]
    diagnostics: List[Dict[str, Any]]
    passed_audits: int
    failed_audits: int


class PageSpeedClient:
    """
    Google PageSpeed Insights API client.
    
    This is a FREE API with generous rate limits.
    No authentication required for basic usage.
    
    Rate limits:
    - 400 requests per 100 seconds per user
    - 25,000 requests per day
    """
    
    API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    def __init__(self, client_config: ClientConfig, api_key: str = None):
        """
        Initialize PageSpeed client.
        
        Args:
            client_config: Client configuration
            api_key: Optional Google Cloud API key for higher rate limits
        """
        self.config = client_config
        self.client_name = client_config.name
        self.api_key = api_key
        self.site_url = client_config.gsc_site_url.rstrip('/')
        self._settings = get_settings()
    
    def _make_request(
        self,
        url: str,
        strategy: str = "mobile",
        categories: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make a PageSpeed API request.
        
        Args:
            url: URL to analyze
            strategy: "mobile" or "desktop"
            categories: List of categories to analyze
        
        Returns:
            API response or None if failed
        """
        if categories is None:
            categories = ["performance"]
        
        params = {
            "url": url,
            "strategy": strategy,
            "category": categories,
        }
        
        if self.api_key:
            params["key"] = self.api_key
        
        try:
            response = requests.get(
                self.API_URL,
                params=params,
                timeout=60  # PageSpeed can be slow
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limited - wait and retry once
                time.sleep(2)
                response = requests.get(self.API_URL, params=params, timeout=60)
                if response.status_code == 200:
                    return response.json()
            
            return None
            
        except requests.RequestException as e:
            print(f"    ⚠️ PageSpeed request failed: {e}")
            return None
    
    def _parse_result(self, data: Dict[str, Any], strategy: str) -> Optional[PageSpeedResult]:
        """Parse API response into structured result."""
        try:
            lighthouse = data.get("lighthouseResult", {})
            categories = lighthouse.get("categories", {})
            audits = lighthouse.get("audits", {})
            
            # Performance score
            perf_category = categories.get("performance", {})
            perf_score = int((perf_category.get("score", 0) or 0) * 100)
            
            # Core Web Vitals
            def get_metric(audit_id: str, field: str = "numericValue") -> float:
                audit = audits.get(audit_id, {})
                value = audit.get(field, 0) or 0
                return value
            
            metrics = PerformanceMetrics(
                score=perf_score,
                fcp=get_metric("first-contentful-paint") / 1000,  # Convert to seconds
                lcp=get_metric("largest-contentful-paint") / 1000,
                tbt=get_metric("total-blocking-time"),  # Already in ms
                cls=get_metric("cumulative-layout-shift", "numericValue"),
                si=get_metric("speed-index") / 1000,
                tti=get_metric("interactive") / 1000,
            )
            
            # Opportunities (things to fix)
            opportunities = []
            for audit_id, audit in audits.items():
                if audit.get("details", {}).get("type") == "opportunity":
                    if audit.get("score") is not None and audit.get("score", 1) < 1:
                        savings = audit.get("details", {}).get("overallSavingsMs", 0)
                        opportunities.append({
                            "id": audit_id,
                            "title": audit.get("title", ""),
                            "description": audit.get("description", ""),
                            "savings_ms": savings,
                            "score": audit.get("score", 0),
                        })
            
            # Sort by potential savings
            opportunities.sort(key=lambda x: x.get("savings_ms", 0), reverse=True)
            
            # Diagnostics
            diagnostics = []
            diagnostic_ids = [
                "dom-size", "uses-responsive-images", "offscreen-images",
                "render-blocking-resources", "uses-optimized-images",
                "modern-image-formats", "uses-text-compression",
                "uses-rel-preconnect", "server-response-time"
            ]
            for audit_id in diagnostic_ids:
                audit = audits.get(audit_id, {})
                if audit:
                    diagnostics.append({
                        "id": audit_id,
                        "title": audit.get("title", ""),
                        "displayValue": audit.get("displayValue", ""),
                        "score": audit.get("score"),
                    })
            
            # Count passed/failed
            passed = sum(1 for a in audits.values() if a.get("score") == 1)
            failed = sum(1 for a in audits.values() if a.get("score") is not None and a.get("score") < 1)
            
            return PageSpeedResult(
                url=data.get("id", ""),
                strategy=strategy,
                performance_score=perf_score,
                metrics=metrics,
                opportunities=opportunities[:10],
                diagnostics=diagnostics,
                passed_audits=passed,
                failed_audits=failed,
            )
            
        except Exception as e:
            print(f"    ⚠️ Error parsing PageSpeed result: {e}")
            return None
    
    @cached(ttl_hours=24)
    def analyze_url(
        self,
        url: str = None,
        strategy: str = "mobile"
    ) -> Optional[PageSpeedResult]:
        """
        Analyze a single URL.
        
        Args:
            url: URL to analyze (defaults to site homepage)
            strategy: "mobile" or "desktop"
        
        Returns:
            PageSpeedResult or None
        """
        url = url or self.site_url
        
        data = self._make_request(url, strategy)
        if data:
            return self._parse_result(data, strategy)
        return None
    
    def get_performance_overview(self) -> Dict[str, Any]:
        """
        Get performance overview for both mobile and desktop.
        
        Returns:
            Dict with mobile and desktop results
        """
        print("    📱 Analyzing mobile performance...")
        mobile = self.analyze_url(strategy="mobile")
        
        print("    🖥️  Analyzing desktop performance...")
        desktop = self.analyze_url(strategy="desktop")
        
        result = {
            "available": mobile is not None or desktop is not None,
            "mobile": None,
            "desktop": None,
            "summary": {},
        }
        
        if mobile:
            result["mobile"] = {
                "score": mobile.performance_score,
                "fcp": round(mobile.metrics.fcp, 2),
                "lcp": round(mobile.metrics.lcp, 2),
                "tbt": round(mobile.metrics.tbt, 0),
                "cls": round(mobile.metrics.cls, 3),
                "tti": round(mobile.metrics.tti, 2),
                "opportunities": mobile.opportunities,
            }
        
        if desktop:
            result["desktop"] = {
                "score": desktop.performance_score,
                "fcp": round(desktop.metrics.fcp, 2),
                "lcp": round(desktop.metrics.lcp, 2),
                "tbt": round(desktop.metrics.tbt, 0),
                "cls": round(desktop.metrics.cls, 3),
                "tti": round(desktop.metrics.tti, 2),
                "opportunities": desktop.opportunities,
            }
        
        # Summary with status indicators - works with partial data
        if mobile or desktop:
            summary = {}
            
            if mobile:
                summary["mobile_score"] = mobile.performance_score
                summary["mobile_status"] = self._score_status(mobile.performance_score)
                summary["lcp_status"] = self._lcp_status(mobile.metrics.lcp)
                summary["cls_status"] = self._cls_status(mobile.metrics.cls)
                summary["top_opportunity"] = mobile.opportunities[0]["title"] if mobile.opportunities else None
            
            if desktop:
                summary["desktop_score"] = desktop.performance_score
                summary["desktop_status"] = self._score_status(desktop.performance_score)
                # If mobile didn't provide these, use desktop values
                if "lcp_status" not in summary:
                    summary["lcp_status"] = self._lcp_status(desktop.metrics.lcp)
                if "cls_status" not in summary:
                    summary["cls_status"] = self._cls_status(desktop.metrics.cls)
                if "top_opportunity" not in summary:
                    summary["top_opportunity"] = desktop.opportunities[0]["title"] if desktop.opportunities else None
            
            result["summary"] = summary
        
        return result
    
    def _score_status(self, score: int) -> str:
        """Get status label for performance score."""
        if score >= 90:
            return "good"
        elif score >= 50:
            return "needs_improvement"
        return "poor"
    
    def _lcp_status(self, lcp: float) -> str:
        """Get status for LCP (Largest Contentful Paint)."""
        if lcp <= 2.5:
            return "good"
        elif lcp <= 4.0:
            return "needs_improvement"
        return "poor"
    
    def _cls_status(self, cls: float) -> str:
        """Get status for CLS (Cumulative Layout Shift)."""
        if cls <= 0.1:
            return "good"
        elif cls <= 0.25:
            return "needs_improvement"
        return "poor"
    
    def analyze_key_pages(self, pages: List[str] = None) -> Dict[str, Dict]:
        """
        Analyze multiple key pages.
        
        Args:
            pages: List of page paths to analyze (e.g., ["/", "/donate", "/about"])
        
        Returns:
            Dict mapping page path to results
        """
        if pages is None:
            pages = ["/"]  # Just homepage by default
        
        results = {}
        for page in pages:
            url = f"{self.site_url}{page}"
            print(f"    Analyzing: {url}")
            result = self.analyze_url(url, "mobile")
            if result:
                results[page] = {
                    "score": result.performance_score,
                    "lcp": round(result.metrics.lcp, 2),
                    "cls": round(result.metrics.cls, 3),
                }
        
        return results

