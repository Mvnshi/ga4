"""
Report Generator
================
Orchestrates data collection, analysis, and report generation.

This is the main entry point for generating quarterly reports.
Handles multiple data sources with graceful fallbacks.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import traceback

from config.settings import ClientConfig, get_settings, OUTPUT_DIR
from src.clients.ga4_client import GA4Client
from src.clients.gsc_client import SearchConsoleClient
from src.clients.pagespeed_client import PageSpeedClient
from src.clients.hotjar_client import create_hotjar_client
from src.clients.google_ads_client import create_google_ads_client
from src.analysis.insights_engine import InsightsEngine
from src.analysis.benchmarks import BenchmarkAnalyzer
from src.analysis.trends import TrendAnalyzer
from src.utils.dates import get_comparison_periods, ComparisonPeriods
from src.utils.formatting import calculate_change
from src.reports.excel_exporter import ExcelExporter
from src.reports.powerpoint_exporter import PowerPointExporter


@dataclass
class QuarterlyReport:
    """Complete quarterly report data structure."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    ga4: Dict[str, Any] = field(default_factory=dict)
    gsc: Dict[str, Any] = field(default_factory=dict)
    pagespeed: Dict[str, Any] = field(default_factory=dict)
    hotjar: Dict[str, Any] = field(default_factory=dict)
    google_ads: Dict[str, Any] = field(default_factory=dict)
    comparison: Dict[str, Any] = field(default_factory=dict)
    insights: Dict[str, Any] = field(default_factory=dict)
    benchmarks: Dict[str, Any] = field(default_factory=dict)
    errors: list = field(default_factory=list)  # Track any errors for transparency
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metadata': self.metadata,
            'ga4': self._serialize_data(self.ga4),
            'gsc': self._serialize_data(self.gsc),
            'pagespeed': self.pagespeed,
            'hotjar': self.hotjar,
            'google_ads': self.google_ads,
            'comparison': self.comparison,
            'insights': self.insights,
            'benchmarks': self.benchmarks,
            'errors': self.errors,
        }
    
    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize data for JSON export, converting DataFrames."""
        import pandas as pd
        
        result = {}
        for key, value in data.items():
            if isinstance(value, pd.DataFrame):
                result[key] = value.to_dict(orient='records')
            elif isinstance(value, dict):
                result[key] = self._serialize_data(value)
            else:
                result[key] = value
        return result
    
    def save_json(self, filename: str = None) -> Path:
        """Save report as JSON file."""
        if filename is None:
            period = self.metadata.get('current_period', {}).get('label', 'report')
            client = self.metadata.get('client_name', 'client')
            filename = f"{client}_report_{period.replace(' ', '_')}.json"
        
        output_path = OUTPUT_DIR / filename
        
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        
        return output_path


class ReportGenerator:
    """
    Main orchestrator for quarterly report generation.
    
    Coordinates data collection from multiple sources:
    - GA4 (required)
    - Search Console (required)
    - PageSpeed Insights (optional, enabled by default)
    - Hotjar (optional)
    - Google Ads (optional)
    
    Handles errors gracefully - if one source fails, others continue.
    """
    
    def __init__(self, client_config: ClientConfig):
        """
        Initialize report generator.
        
        Args:
            client_config: Configuration for the client
        """
        self.config = client_config
        self.settings = get_settings()
        self.errors = []
        
        # Initialize required clients
        self.ga4 = self._safe_init(
            lambda: GA4Client(client_config),
            "GA4 Client"
        )
        self.gsc = self._safe_init(
            lambda: SearchConsoleClient(client_config),
            "Search Console Client"
        )
        
        # Initialize optional clients based on config
        self.pagespeed = None
        self.hotjar = None
        self.google_ads = None
        
        if client_config.has_pagespeed():
            self.pagespeed = self._safe_init(
                lambda: PageSpeedClient(
                    client_config,
                    api_key=client_config.integrations.pagespeed_api_key
                ),
                "PageSpeed Client"
            )
        
        if client_config.has_hotjar():
            self.hotjar = self._safe_init(
                lambda: create_hotjar_client(
                    client_config,
                    site_id=client_config.integrations.hotjar_site_id,
                    api_token=client_config.integrations.hotjar_api_token
                ),
                "Hotjar Client"
            )
        
        # Google Ads - try to initialize if enabled or if GA4 fallback is enabled
        if (client_config.has_google_ads() or 
            client_config.integrations.google_ads_use_ga4_fallback):
            self.google_ads = self._safe_init(
                lambda: create_google_ads_client(
                    client_config,
                    customer_id=client_config.integrations.google_ads_customer_id,
                    developer_token=client_config.integrations.google_ads_developer_token,
                    use_ga4_fallback=client_config.integrations.google_ads_use_ga4_fallback
                ),
                "Google Ads Client"
            )
        
        # Initialize analyzers
        self.insights_engine = InsightsEngine()
        self.benchmark_analyzer = BenchmarkAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        
        # Initialize exporters
        self.excel_exporter = ExcelExporter(client_config)
        self.pptx_exporter = PowerPointExporter(client_config)
    
    def _safe_init(self, init_func, name: str):
        """Safely initialize a client, catching errors."""
        try:
            return init_func()
        except Exception as e:
            error_msg = f"{name} initialization failed: {str(e)}"
            self.errors.append(error_msg)
            print(f"    ⚠️ {error_msg}")
            return None
    
    def _safe_fetch(self, fetch_func, name: str, default=None):
        """Safely fetch data, catching errors and returning default on failure."""
        try:
            return fetch_func()
        except Exception as e:
            error_msg = f"{name} failed: {str(e)}"
            self.errors.append(error_msg)
            print(f"    ⚠️ {error_msg}")
            return default if default is not None else {}
    
    def generate(
        self,
        quarter: str,
        year: int,
        comparison_type: str = "yoy"
    ) -> QuarterlyReport:
        """
        Generate a complete quarterly report.
        
        Args:
            quarter: Q1, Q2, Q3, or Q4
            year: The year to report on
            comparison_type: "yoy" (year-over-year) or "qoq" (quarter-over-quarter)
        
        Returns:
            QuarterlyReport object with all data
        """
        print(f"\n🚀 Generating {quarter} {year} report for {self.config.display_name}")
        print("=" * 60)
        
        # Reset errors for this run
        self.errors = []
        
        # Get comparison periods
        periods = get_comparison_periods(quarter, year, comparison_type)
        
        # Create report
        report = QuarterlyReport()
        
        # Metadata
        report.metadata = {
            'client_name': self.config.name,
            'client_display_name': self.config.display_name,
            'generated_at': datetime.now().isoformat(),
            'current_period': {
                'label': periods.current.label,
                'start': periods.current.start_date,
                'end': periods.current.end_date,
            },
            'previous_period': {
                'label': periods.previous.label,
                'start': periods.previous.start_date,
                'end': periods.previous.end_date,
            },
            'comparison_type': comparison_type,
            'integrations': {
                'pagespeed': self.pagespeed is not None,
                'hotjar': self.hotjar is not None and self.hotjar.is_configured,
                'google_ads': self.google_ads is not None,
            }
        }
        
        # Collect data from each source
        print("\n📊 Fetching Google Analytics 4 data...")
        report.ga4 = self._collect_ga4_data(periods)
        
        print("\n🔍 Fetching Google Search Console data...")
        report.gsc = self._collect_gsc_data(periods)
        
        # Optional integrations
        if self.pagespeed:
            print("\n⚡ Fetching PageSpeed Insights data...")
            report.pagespeed = self._collect_pagespeed_data()
        else:
            report.pagespeed = {"available": False, "reason": "PageSpeed not enabled"}
        
        if self.hotjar and self.hotjar.is_configured:
            print("\n🔥 Fetching Hotjar data...")
            report.hotjar = self._collect_hotjar_data(periods)
        else:
            report.hotjar = {"available": False, "reason": "Hotjar not configured"}
        
        if self.google_ads:
            print("\n💰 Fetching Google Ads data...")
            report.google_ads = self._collect_google_ads_data(periods)
        else:
            report.google_ads = {"available": False, "reason": "Google Ads not configured"}
        
        # Calculate comparisons
        print("\n📈 Calculating year-over-year comparisons...")
        report.comparison = self._calculate_comparisons(report, periods)
        
        # Run benchmark analysis
        print("\n📋 Running benchmark analysis...")
        report.benchmarks = self._run_benchmarks(report)
        
        # Generate insights
        print("\n💡 Generating insights and recommendations...")
        report.insights = self._generate_insights(report, periods)
        
        # Attach any errors that occurred
        report.errors = self.errors
        
        if self.errors:
            print(f"\n⚠️ Completed with {len(self.errors)} warnings (report still generated)")
        else:
            print("\n✅ Report generation complete!")
        
        return report
    
    def _collect_ga4_data(self, periods: ComparisonPeriods) -> Dict[str, Any]:
        """Collect all GA4 data for current and previous periods."""
        if self.ga4 is None:
            return {"error": "GA4 client not initialized"}
        
        current = periods.current
        previous = periods.previous
        
        return {
            # Current period data
            'traffic_overview': self._safe_fetch(
                lambda: self.ga4.get_traffic_overview(current.start_date, current.end_date),
                "GA4 traffic overview", {}
            ),
            'traffic_by_month': self._safe_fetch(
                lambda: self.ga4.get_traffic_by_month(current.start_date, current.end_date),
                "GA4 monthly traffic"
            ),
            'traffic_by_channel': self._safe_fetch(
                lambda: self.ga4.get_traffic_by_channel(current.start_date, current.end_date),
                "GA4 channel breakdown"
            ),
            'traffic_by_source': self._safe_fetch(
                lambda: self.ga4.get_traffic_by_source_medium(current.start_date, current.end_date),
                "GA4 source/medium"
            ),
            'top_pages': self._safe_fetch(
                lambda: self.ga4.get_top_pages(current.start_date, current.end_date),
                "GA4 top pages"
            ),
            'landing_pages': self._safe_fetch(
                lambda: self.ga4.get_landing_pages(current.start_date, current.end_date),
                "GA4 landing pages"
            ),
            'homepage_engagement': self._safe_fetch(
                lambda: self.ga4.get_homepage_engagement(current.start_date, current.end_date),
                "GA4 homepage engagement", {}
            ),
            'device_breakdown': self._safe_fetch(
                lambda: self.ga4.get_device_breakdown(current.start_date, current.end_date),
                "GA4 device breakdown"
            ),
            'geography': self._safe_fetch(
                lambda: self.ga4.get_geography(current.start_date, current.end_date),
                "GA4 geography"
            ),
            'new_vs_returning': self._safe_fetch(
                lambda: self.ga4.get_new_vs_returning(current.start_date, current.end_date),
                "GA4 new vs returning", {}
            ),
            'paid_search': self._safe_fetch(
                lambda: self.ga4.get_paid_search_overview(current.start_date, current.end_date),
                "GA4 paid search", {}
            ),
            'campaigns': self._safe_fetch(
                lambda: self.ga4.get_campaign_performance(current.start_date, current.end_date),
                "GA4 campaigns"
            ),
            'top_events': self._safe_fetch(
                lambda: self.ga4.get_top_events(current.start_date, current.end_date),
                "GA4 events"
            ),
            
            # Previous period for comparison
            '_previous': {
                'traffic_overview': self._safe_fetch(
                    lambda: self.ga4.get_traffic_overview(previous.start_date, previous.end_date),
                    "GA4 previous traffic overview", {}
                ),
                'traffic_by_month': self._safe_fetch(
                    lambda: self.ga4.get_traffic_by_month(previous.start_date, previous.end_date),
                    "GA4 previous monthly traffic"
                ),
            }
        }
    
    def _collect_gsc_data(self, periods: ComparisonPeriods) -> Dict[str, Any]:
        """Collect all Search Console data for current and previous periods."""
        if self.gsc is None:
            return {"error": "Search Console client not initialized"}
        
        current = periods.current
        previous = periods.previous
        
        return {
            # Current period
            'overview': self._safe_fetch(
                lambda: self.gsc.get_search_overview(current.start_date, current.end_date),
                "GSC overview", {}
            ),
            'top_keywords_clicks': self._safe_fetch(
                lambda: self.gsc.get_top_keywords_by_clicks(current.start_date, current.end_date),
                "GSC top keywords (clicks)"
            ),
            'top_keywords_impressions': self._safe_fetch(
                lambda: self.gsc.get_top_keywords_by_impressions(current.start_date, current.end_date),
                "GSC top keywords (impressions)"
            ),
            'top_keywords_ctr': self._safe_fetch(
                lambda: self.gsc.get_top_keywords_by_ctr(current.start_date, current.end_date),
                "GSC top keywords (CTR)"
            ),
            'keyword_opportunities': self._safe_fetch(
                lambda: self.gsc.get_keyword_opportunities(current.start_date, current.end_date),
                "GSC keyword opportunities"
            ),
            'branded_vs_nonbranded': self._safe_fetch(
                lambda: self.gsc.get_branded_vs_nonbranded(current.start_date, current.end_date),
                "GSC branded vs non-branded", {}
            ),
            'top_pages': self._safe_fetch(
                lambda: self.gsc.get_top_pages(current.start_date, current.end_date),
                "GSC top pages"
            ),
            'daily_performance': self._safe_fetch(
                lambda: self.gsc.get_daily_performance(current.start_date, current.end_date),
                "GSC daily performance"
            ),
            'device_breakdown': self._safe_fetch(
                lambda: self.gsc.get_device_breakdown(current.start_date, current.end_date),
                "GSC device breakdown"
            ),
            'country_breakdown': self._safe_fetch(
                lambda: self.gsc.get_country_breakdown(current.start_date, current.end_date),
                "GSC country breakdown"
            ),
            
            # Previous period
            '_previous': {
                'overview': self._safe_fetch(
                    lambda: self.gsc.get_search_overview(previous.start_date, previous.end_date),
                    "GSC previous overview", {}
                ),
                'top_keywords_clicks': self._safe_fetch(
                    lambda: self.gsc.get_top_keywords_by_clicks(previous.start_date, previous.end_date),
                    "GSC previous keywords"
                ),
            }
        }
    
    def _collect_pagespeed_data(self) -> Dict[str, Any]:
        """Collect PageSpeed Insights data."""
        if self.pagespeed is None:
            return {"available": False, "reason": "PageSpeed client not initialized"}
        
        try:
            data = self.pagespeed.get_performance_overview()
            # Only mark as available if we actually got some data
            has_data = data.get("mobile") is not None or data.get("desktop") is not None
            data["available"] = has_data
            if not has_data:
                data["reason"] = "PageSpeed analysis returned no data"
            return data
        except Exception as e:
            self.errors.append(f"PageSpeed fetch failed: {str(e)}")
            return {"available": False, "reason": str(e)}
    
    def _collect_hotjar_data(self, periods: ComparisonPeriods) -> Dict[str, Any]:
        """Collect Hotjar data."""
        if self.hotjar is None or not self.hotjar.is_configured:
            return {"available": False, "reason": "Hotjar not configured"}
        
        try:
            current = periods.current
            return self.hotjar.get_all_insights(current.start_date, current.end_date)
        except Exception as e:
            self.errors.append(f"Hotjar fetch failed: {str(e)}")
            return {"available": False, "reason": str(e)}
    
    def _collect_google_ads_data(self, periods: ComparisonPeriods) -> Dict[str, Any]:
        """Collect Google Ads data."""
        if self.google_ads is None:
            return {"available": False, "reason": "Google Ads not configured"}
        
        try:
            current = periods.current
            return self.google_ads.get_all_ads_data(current.start_date, current.end_date)
        except Exception as e:
            self.errors.append(f"Google Ads fetch failed: {str(e)}")
            return {"available": False, "reason": str(e)}
    
    def _calculate_comparisons(
        self, report: QuarterlyReport, periods: ComparisonPeriods
    ) -> Dict[str, Any]:
        """Calculate comparisons between periods."""
        comparisons = {}
        
        # GA4 traffic overview comparison
        curr_traffic = report.ga4.get('traffic_overview', {})
        prev_traffic = report.ga4.get('_previous', {}).get('traffic_overview', {})
        
        traffic_comp = {}
        for key in curr_traffic:
            curr_val = curr_traffic.get(key, 0)
            prev_val = prev_traffic.get(key, 0)
            
            # Determine if lower is better
            inverse = key in ['bounce_rate']
            
            try:
                change = calculate_change(
                    curr_val, prev_val,
                    significant_threshold=self.settings.significant_change_threshold,
                    anomaly_threshold=self.settings.anomaly_threshold,
                    inverse=inverse
                )
                
                traffic_comp[key] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': {
                        'pct': change.change_pct,
                        'abs': change.change_abs,
                        'direction': change.direction,
                        'formatted': change.formatted_change,
                        'significant': change.is_significant,
                        'anomaly': change.is_anomaly,
                    }
                }
            except Exception:
                traffic_comp[key] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': {'formatted': 'N/A'}
                }
        
        comparisons['traffic_overview'] = traffic_comp
        
        # GSC overview comparison
        curr_gsc = report.gsc.get('overview', {})
        prev_gsc = report.gsc.get('_previous', {}).get('overview', {})
        
        gsc_comp = {}
        for key in curr_gsc:
            curr_val = curr_gsc.get(key, 0)
            prev_val = prev_gsc.get(key, 0)
            
            inverse = key in ['avg_position']
            
            try:
                change = calculate_change(curr_val, prev_val, inverse=inverse)
                
                gsc_comp[key] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': {
                        'pct': change.change_pct,
                        'direction': change.direction,
                        'formatted': change.formatted_change,
                    }
                }
            except Exception:
                gsc_comp[key] = {
                    'current': curr_val,
                    'previous': prev_val,
                    'change': {'formatted': 'N/A'}
                }
        
        comparisons['gsc'] = {'overview': gsc_comp}
        
        return comparisons
    
    def _run_benchmarks(self, report: QuarterlyReport) -> Dict[str, Any]:
        """Run benchmark analysis on current metrics."""
        traffic = report.ga4.get('traffic_overview', {})
        
        metrics_to_benchmark = {
            'bounce_rate': traffic.get('bounce_rate', 0),
            'avg_session_duration': traffic.get('avg_session_duration', 0),
            'pages_per_session': traffic.get('pages_per_session', 0),
            'engagement_rate': traffic.get('engagement_rate', 0),
        }
        
        # Add PageSpeed scores if available
        pagespeed = report.pagespeed
        if pagespeed.get('available'):
            mobile = pagespeed.get('mobile', {})
            desktop = pagespeed.get('desktop', {})
            if mobile:
                metrics_to_benchmark['mobile_performance_score'] = mobile.get('score', 0)
            if desktop:
                metrics_to_benchmark['desktop_performance_score'] = desktop.get('score', 0)
        
        # Add channel shares if available
        channels = report.ga4.get('traffic_by_channel')
        if channels is not None:
            try:
                if hasattr(channels, 'empty') and not channels.empty:
                    for _, row in channels.iterrows():
                        channel = row.get('sessionDefaultChannelGroup', '').lower().replace(' ', '_')
                        if channel:
                            metrics_to_benchmark[f'{channel}_traffic_share'] = row.get('session_share', 0)
            except Exception:
                pass  # Skip if channel data is malformed
        
        try:
            comparisons = self.benchmark_analyzer.analyze_all(metrics_to_benchmark)
            summary = self.benchmark_analyzer.get_benchmark_summary(comparisons)
            
            return {
                'comparisons': {k: {
                    'value': v.current_value,
                    'benchmark': v.benchmark_value,
                    'performance': v.performance,
                    'interpretation': v.interpretation,
                } for k, v in comparisons.items()},
                'summary': summary,
            }
        except Exception as e:
            self.errors.append(f"Benchmark analysis failed: {str(e)}")
            return {'comparisons': {}, 'summary': {}}
    
    def _generate_insights(
        self, report: QuarterlyReport, periods: ComparisonPeriods
    ) -> Dict[str, Any]:
        """Generate insights from the collected data."""
        try:
            # Prepare data for insights engine
            ga4_current = report.ga4
            ga4_previous = report.ga4.get('_previous', {})
            gsc_current = report.gsc
            gsc_previous = report.gsc.get('_previous', {})
            
            # Run analysis
            self.insights_engine.analyze(
                ga4_current, ga4_previous,
                gsc_current, gsc_previous
            )
            
            insights_dict = self.insights_engine.to_dict()
            
            # Add PageSpeed insights if available
            if report.pagespeed.get('available'):
                self._add_pagespeed_insights(insights_dict, report.pagespeed)
            
            # Add Hotjar insights if available
            if report.hotjar.get('available'):
                self._add_hotjar_insights(insights_dict, report.hotjar)
            
            return insights_dict
            
        except Exception as e:
            self.errors.append(f"Insights generation failed: {str(e)}")
            return {'executive_summary': 'Insights generation encountered an error.', 'insights': [], 'key_recommendations': []}
    
    def _add_pagespeed_insights(self, insights_dict: Dict, pagespeed_data: Dict):
        """Add PageSpeed-specific insights."""
        summary = pagespeed_data.get('summary', {})
        mobile_score = summary.get('mobile_score', 0)
        
        if mobile_score < 50:
            insights_dict['insights'].append({
                'category': 'performance',
                'type': 'negative',
                'priority': 2,
                'headline': f"Mobile performance score is poor ({mobile_score}/100)",
                'recommendation': "Prioritize mobile performance: optimize images, reduce JavaScript, enable caching.",
            })
        elif mobile_score < 90:
            insights_dict['insights'].append({
                'category': 'performance',
                'type': 'opportunity',
                'priority': 3,
                'headline': f"Mobile performance has room for improvement ({mobile_score}/100)",
                'recommendation': "Review PageSpeed recommendations to improve Core Web Vitals.",
            })
    
    def _add_hotjar_insights(self, insights_dict: Dict, hotjar_data: Dict):
        """Add Hotjar-specific insights."""
        feedback_data = hotjar_data.get('feedback', {})
        nps = feedback_data.get('nps_estimate', 0)
        
        if nps > 50:
            insights_dict['insights'].append({
                'category': 'engagement',
                'type': 'positive',
                'priority': 3,
                'headline': f"User sentiment is positive (NPS estimate: {nps})",
                'recommendation': None,
            })
        elif nps < 0:
            insights_dict['insights'].append({
                'category': 'engagement',
                'type': 'negative',
                'priority': 2,
                'headline': f"User sentiment needs attention (NPS estimate: {nps})",
                'recommendation': "Review recent user feedback to identify pain points.",
            })
    
    def export_excel(self, report: QuarterlyReport, filename: str = None) -> Path:
        """Export report to Excel."""
        print("\n📊 Exporting to Excel...")
        path = self.excel_exporter.export(report.to_dict(), filename)
        print(f"   ✅ Saved to: {path}")
        return path
    
    def export_powerpoint(self, report: QuarterlyReport, filename: str = None) -> Path:
        """Export report to PowerPoint."""
        print("\n📽️  Exporting to PowerPoint...")
        path = self.pptx_exporter.export(report.to_dict(), filename)
        print(f"   ✅ Saved to: {path}")
        return path
    
    def export_all(self, report: QuarterlyReport) -> Dict[str, Path]:
        """Export report to all formats."""
        return {
            'excel': self.export_excel(report),
            'powerpoint': self.export_powerpoint(report),
            'json': report.save_json(),
        }
    
    def print_summary(self, report: QuarterlyReport):
        """Print a summary of the report to console."""
        print("\n" + "=" * 60)
        print(f"📊 REPORT SUMMARY: {report.metadata.get('current_period', {}).get('label', '')}")
        print("=" * 60)
        
        # Traffic overview
        traffic = report.ga4.get('traffic_overview', {})
        comparison = report.comparison.get('traffic_overview', {})
        
        print("\n🌐 WEBSITE TRAFFIC")
        print("-" * 40)
        
        for key, label in [
            ('total_users', 'Total Users'),
            ('new_users', 'New Users'),
            ('sessions', 'Sessions'),
            ('pageviews', 'Pageviews'),
        ]:
            value = traffic.get(key, 0)
            change = comparison.get(key, {}).get('change', {})
            change_str = change.get('formatted', 'N/A')
            direction = change.get('direction', 'neutral')
            
            arrow = "↑" if direction == 'up' else "↓" if direction == 'down' else "→"
            print(f"  {label}: {value:,} ({arrow} {change_str})")
        
        # Search performance
        gsc = report.gsc.get('overview', {})
        print("\n🔍 SEARCH PERFORMANCE")
        print("-" * 40)
        print(f"  Total Clicks: {gsc.get('total_clicks', 0):,}")
        print(f"  Impressions: {gsc.get('total_impressions', 0):,}")
        print(f"  Avg CTR: {gsc.get('avg_ctr', 0):.2f}%")
        print(f"  Avg Position: {gsc.get('avg_position', 0):.1f}")
        
        # PageSpeed
        if report.pagespeed.get('available'):
            summary = report.pagespeed.get('summary', {})
            print("\n⚡ SITE PERFORMANCE")
            print("-" * 40)
            print(f"  Mobile Score: {summary.get('mobile_score', 'N/A')}/100")
            print(f"  Desktop Score: {summary.get('desktop_score', 'N/A')}/100")
        
        # Hotjar
        if report.hotjar.get('available'):
            hj_summary = report.hotjar.get('summary', {})
            print("\n🔥 USER FEEDBACK (Hotjar)")
            print("-" * 40)
            print(f"  Feedback Responses: {hj_summary.get('total_feedback', 0)}")
            print(f"  Sentiment Score: {hj_summary.get('sentiment_score', 0)}")
        
        # Key insights
        insights = report.insights.get('insights', [])
        if insights:
            print("\n💡 KEY INSIGHTS")
            print("-" * 40)
            for insight in insights[:3]:
                emoji = "✓" if insight.get('type') == 'positive' else "⚠" if insight.get('type') == 'negative' else "→"
                print(f"  {emoji} {insight.get('headline', '')}")
        
        # Executive summary
        summary = report.insights.get('executive_summary', '')
        if summary:
            print("\n📝 EXECUTIVE SUMMARY")
            print("-" * 40)
            print(f"  {summary}")
        
        # Errors/warnings
        if report.errors:
            print("\n⚠️ WARNINGS")
            print("-" * 40)
            for error in report.errors[:5]:
                print(f"  • {error}")
        
        print("\n" + "=" * 60)
