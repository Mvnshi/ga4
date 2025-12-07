"""
Report Generator
================
Orchestrates data collection, analysis, and report generation.

This is the main entry point for generating quarterly reports.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from config.settings import ClientConfig, get_settings, OUTPUT_DIR
from src.clients.ga4_client import GA4Client
from src.clients.gsc_client import SearchConsoleClient
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
    comparison: Dict[str, Any] = field(default_factory=dict)
    insights: Dict[str, Any] = field(default_factory=dict)
    benchmarks: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metadata': self.metadata,
            'ga4': self._serialize_data(self.ga4),
            'gsc': self._serialize_data(self.gsc),
            'comparison': self.comparison,
            'insights': self.insights,
            'benchmarks': self.benchmarks,
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
    
    Coordinates data collection from GA4 and Search Console,
    runs analysis, generates insights, and exports reports.
    """
    
    def __init__(self, client_config: ClientConfig):
        """
        Initialize report generator.
        
        Args:
            client_config: Configuration for the client
        """
        self.config = client_config
        self.settings = get_settings()
        
        # Initialize clients
        self.ga4 = GA4Client(client_config)
        self.gsc = SearchConsoleClient(client_config)
        
        # Initialize analyzers
        self.insights_engine = InsightsEngine()
        self.benchmark_analyzer = BenchmarkAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        
        # Initialize exporters
        self.excel_exporter = ExcelExporter(client_config)
        self.pptx_exporter = PowerPointExporter(client_config)
    
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
        }
        
        # Collect GA4 data
        print("\n📊 Fetching Google Analytics 4 data...")
        report.ga4 = self._collect_ga4_data(periods)
        
        # Collect GSC data
        print("\n🔍 Fetching Google Search Console data...")
        report.gsc = self._collect_gsc_data(periods)
        
        # Calculate comparisons
        print("\n📈 Calculating year-over-year comparisons...")
        report.comparison = self._calculate_comparisons(report, periods)
        
        # Run benchmark analysis
        print("\n📋 Running benchmark analysis...")
        report.benchmarks = self._run_benchmarks(report)
        
        # Generate insights
        print("\n💡 Generating insights and recommendations...")
        report.insights = self._generate_insights(report, periods)
        
        print("\n✅ Report generation complete!")
        
        return report
    
    def _collect_ga4_data(self, periods: ComparisonPeriods) -> Dict[str, Any]:
        """Collect all GA4 data for current and previous periods."""
        current = periods.current
        previous = periods.previous
        
        return {
            # Current period data
            'traffic_overview': self.ga4.get_traffic_overview(
                current.start_date, current.end_date
            ),
            'traffic_by_month': self.ga4.get_traffic_by_month(
                current.start_date, current.end_date
            ),
            'traffic_by_channel': self.ga4.get_traffic_by_channel(
                current.start_date, current.end_date
            ),
            'traffic_by_source': self.ga4.get_traffic_by_source_medium(
                current.start_date, current.end_date
            ),
            'top_pages': self.ga4.get_top_pages(
                current.start_date, current.end_date
            ),
            'landing_pages': self.ga4.get_landing_pages(
                current.start_date, current.end_date
            ),
            'homepage_engagement': self.ga4.get_homepage_engagement(
                current.start_date, current.end_date
            ),
            'device_breakdown': self.ga4.get_device_breakdown(
                current.start_date, current.end_date
            ),
            'geography': self.ga4.get_geography(
                current.start_date, current.end_date
            ),
            'new_vs_returning': self.ga4.get_new_vs_returning(
                current.start_date, current.end_date
            ),
            'paid_search': self.ga4.get_paid_search_overview(
                current.start_date, current.end_date
            ),
            'campaigns': self.ga4.get_campaign_performance(
                current.start_date, current.end_date
            ),
            'top_events': self.ga4.get_top_events(
                current.start_date, current.end_date
            ),
            
            # Previous period for comparison
            '_previous': {
                'traffic_overview': self.ga4.get_traffic_overview(
                    previous.start_date, previous.end_date
                ),
                'traffic_by_month': self.ga4.get_traffic_by_month(
                    previous.start_date, previous.end_date
                ),
            }
        }
    
    def _collect_gsc_data(self, periods: ComparisonPeriods) -> Dict[str, Any]:
        """Collect all Search Console data for current and previous periods."""
        current = periods.current
        previous = periods.previous
        
        return {
            # Current period
            'overview': self.gsc.get_search_overview(
                current.start_date, current.end_date
            ),
            'top_keywords_clicks': self.gsc.get_top_keywords_by_clicks(
                current.start_date, current.end_date
            ),
            'top_keywords_impressions': self.gsc.get_top_keywords_by_impressions(
                current.start_date, current.end_date
            ),
            'top_keywords_ctr': self.gsc.get_top_keywords_by_ctr(
                current.start_date, current.end_date
            ),
            'keyword_opportunities': self.gsc.get_keyword_opportunities(
                current.start_date, current.end_date
            ),
            'branded_vs_nonbranded': self.gsc.get_branded_vs_nonbranded(
                current.start_date, current.end_date
            ),
            'top_pages': self.gsc.get_top_pages(
                current.start_date, current.end_date
            ),
            'daily_performance': self.gsc.get_daily_performance(
                current.start_date, current.end_date
            ),
            'device_breakdown': self.gsc.get_device_breakdown(
                current.start_date, current.end_date
            ),
            'country_breakdown': self.gsc.get_country_breakdown(
                current.start_date, current.end_date
            ),
            
            # Previous period
            '_previous': {
                'overview': self.gsc.get_search_overview(
                    previous.start_date, previous.end_date
                ),
                'top_keywords_clicks': self.gsc.get_top_keywords_by_clicks(
                    previous.start_date, previous.end_date
                ),
            }
        }
    
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
        
        comparisons['traffic_overview'] = traffic_comp
        
        # GSC overview comparison
        curr_gsc = report.gsc.get('overview', {})
        prev_gsc = report.gsc.get('_previous', {}).get('overview', {})
        
        gsc_comp = {}
        for key in curr_gsc:
            curr_val = curr_gsc.get(key, 0)
            prev_val = prev_gsc.get(key, 0)
            
            inverse = key in ['avg_position']
            
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
        
        # Add channel shares if available
        channels = report.ga4.get('traffic_by_channel')
        if channels is not None and not channels.empty:
            for _, row in channels.iterrows():
                channel = row.get('sessionDefaultChannelGroup', '').lower().replace(' ', '_')
                if channel:
                    metrics_to_benchmark[f'{channel}_traffic_share'] = row.get('session_share', 0)
        
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
    
    def _generate_insights(
        self, report: QuarterlyReport, periods: ComparisonPeriods
    ) -> Dict[str, Any]:
        """Generate insights from the collected data."""
        # Prepare data for insights engine
        ga4_current = report.ga4
        ga4_previous = report.ga4.get('_previous', {})
        gsc_current = report.gsc
        gsc_previous = report.gsc.get('_previous', {})
        
        # Run analysis
        insights = self.insights_engine.analyze(
            ga4_current, ga4_previous,
            gsc_current, gsc_previous
        )
        
        return self.insights_engine.to_dict()
    
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
        
        print("\n" + "=" * 60)

