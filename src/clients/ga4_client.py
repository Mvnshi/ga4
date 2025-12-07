"""
Google Analytics 4 Data API Client
===================================
Comprehensive GA4 data extraction for nonprofit analytics.

This client provides access to all key metrics needed for quarterly reports:
- Traffic overview (users, sessions, pageviews)
- User acquisition (channels, sources, campaigns)
- Engagement metrics (bounce rate, session duration, pages per session)
- Content performance (top pages, landing pages)
- Audience insights (new vs returning, device, geography)
- Conversion tracking (events, goals)
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import pandas as pd

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    FilterExpression,
    Filter,
    OrderBy,
    MetricAggregation,
)
from google.oauth2 import service_account

from config.settings import ClientConfig, get_settings
from src.utils.cache import cached
from src.utils.formatting import format_duration


class GA4Client:
    """
    Google Analytics 4 Data API client.
    
    Provides high-level methods for extracting analytics data
    with automatic caching and error handling.
    """
    
    def __init__(self, client_config: ClientConfig):
        """
        Initialize GA4 client.
        
        Args:
            client_config: Client configuration with credentials and property ID
        """
        self.config = client_config
        self.client_name = client_config.name
        self.property_id = f"properties/{client_config.ga4_property_id}"
        
        # Initialize API client
        credentials = service_account.Credentials.from_service_account_file(
            str(client_config.get_credentials_path()),
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        self._client = BetaAnalyticsDataClient(credentials=credentials)
        self._settings = get_settings()
    
    def _run_report(
        self,
        start_date: str,
        end_date: str,
        dimensions: List[str] = None,
        metrics: List[str] = None,
        dimension_filter: FilterExpression = None,
        order_bys: List[OrderBy] = None,
        limit: int = None,
    ) -> pd.DataFrame:
        """
        Run a GA4 report and return as DataFrame.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            dimensions: List of dimension names
            metrics: List of metric names
            dimension_filter: Optional filter expression
            order_bys: Optional ordering
            limit: Row limit
        
        Returns:
            DataFrame with report data
        """
        dimensions = dimensions or []
        metrics = metrics or []
        limit = limit or self._settings.default_row_limit
        
        request = RunReportRequest(
            property=self.property_id,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            limit=limit,
        )
        
        if dimension_filter:
            request.dimension_filter = dimension_filter
        
        if order_bys:
            request.order_bys = order_bys
        
        response = self._client.run_report(request)
        
        # Convert to DataFrame
        data = []
        for row in response.rows:
            row_data = {}
            for i, dim in enumerate(dimensions):
                row_data[dim] = row.dimension_values[i].value
            for i, metric in enumerate(metrics):
                value = row.metric_values[i].value
                try:
                    row_data[metric] = float(value) if '.' in value else int(value)
                except ValueError:
                    row_data[metric] = value
            data.append(row_data)
        
        return pd.DataFrame(data)
    
    # =========================================================================
    # TRAFFIC OVERVIEW
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_traffic_overview(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get comprehensive traffic overview metrics.
        
        Returns:
            Dict with total_users, new_users, returning_users, sessions,
            pageviews, avg_session_duration, bounce_rate, pages_per_session
        """
        df = self._run_report(
            start_date, end_date,
            dimensions=[],
            metrics=[
                'totalUsers',
                'newUsers',
                'activeUsers',
                'sessions',
                'screenPageViews',
                'averageSessionDuration',
                'bounceRate',
                'screenPageViewsPerSession',
                'engagedSessions',
                'engagementRate',
                'userEngagementDuration',
            ]
        )
        
        if df.empty:
            return {}
        
        row = df.iloc[0]
        total_users = int(row.get('totalUsers', 0))
        new_users = int(row.get('newUsers', 0))
        
        return {
            'total_users': total_users,
            'new_users': new_users,
            'returning_users': max(0, total_users - new_users),
            'active_users': int(row.get('activeUsers', 0)),
            'sessions': int(row.get('sessions', 0)),
            'pageviews': int(row.get('screenPageViews', 0)),
            'avg_session_duration': round(row.get('averageSessionDuration', 0), 1),
            'bounce_rate': round(row.get('bounceRate', 0) * 100, 2),
            'pages_per_session': round(row.get('screenPageViewsPerSession', 0), 2),
            'engaged_sessions': int(row.get('engagedSessions', 0)),
            'engagement_rate': round(row.get('engagementRate', 0) * 100, 2),
            'total_engagement_time': round(row.get('userEngagementDuration', 0), 0),
        }
    
    @cached(ttl_hours=24)
    def get_traffic_by_month(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get traffic metrics broken down by month."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['yearMonth'],
            metrics=[
                'totalUsers', 
                'newUsers', 
                'sessions', 
                'screenPageViews',
                'bounceRate', 
                'averageSessionDuration',
                'engagementRate',
            ],
            limit=12
        )
        
        if not df.empty:
            df['returning_users'] = df['totalUsers'] - df['newUsers']
            df['bounceRate'] = (df['bounceRate'] * 100).round(2)
            df['averageSessionDuration'] = df['averageSessionDuration'].round(1)
            df['engagementRate'] = (df['engagementRate'] * 100).round(2)
            df = df.sort_values('yearMonth')
        
        return df
    
    @cached(ttl_hours=24)
    def get_traffic_by_week(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get traffic metrics broken down by week."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['yearWeek'],
            metrics=['totalUsers', 'sessions', 'screenPageViews', 'bounceRate'],
            limit=53
        )
        
        if not df.empty:
            df['bounceRate'] = (df['bounceRate'] * 100).round(2)
            df = df.sort_values('yearWeek')
        
        return df
    
    # =========================================================================
    # USER ACQUISITION
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_traffic_by_channel(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get traffic breakdown by channel grouping."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['sessionDefaultChannelGroup'],
            metrics=[
                'sessions', 
                'totalUsers', 
                'newUsers',
                'bounceRate', 
                'averageSessionDuration',
                'screenPageViewsPerSession',
                'engagementRate',
            ],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='sessions'), 
                desc=True
            )],
            limit=15
        )
        
        if not df.empty:
            total_sessions = df['sessions'].sum()
            df['session_share'] = (df['sessions'] / total_sessions * 100).round(2)
            df['bounceRate'] = (df['bounceRate'] * 100).round(2)
            df['engagementRate'] = (df['engagementRate'] * 100).round(2)
            df['averageSessionDuration'] = df['averageSessionDuration'].round(1)
        
        return df
    
    @cached(ttl_hours=24)
    def get_traffic_by_source_medium(
        self, start_date: str, end_date: str, limit: int = 20
    ) -> pd.DataFrame:
        """Get traffic by source/medium combination."""
        return self._run_report(
            start_date, end_date,
            dimensions=['sessionSourceMedium'],
            metrics=[
                'sessions', 
                'totalUsers',
                'bounceRate', 
                'averageSessionDuration',
                'engagementRate',
            ],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='sessions'), 
                desc=True
            )],
            limit=limit
        )
    
    @cached(ttl_hours=24)
    def get_organic_keywords(
        self, start_date: str, end_date: str, limit: int = 25
    ) -> pd.DataFrame:
        """
        Get organic search keywords (where available).
        Note: Most keywords show as (not set) due to privacy, 
        but this can still provide some insight.
        """
        dimension_filter = FilterExpression(
            filter=Filter(
                field_name="sessionMedium",
                string_filter=Filter.StringFilter(
                    value="organic",
                    match_type=Filter.StringFilter.MatchType.EXACT
                )
            )
        )
        
        return self._run_report(
            start_date, end_date,
            dimensions=['sessionManualTerm'],
            metrics=['sessions', 'totalUsers', 'bounceRate'],
            dimension_filter=dimension_filter,
            limit=limit
        )
    
    # =========================================================================
    # PAID SEARCH / CAMPAIGNS
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_paid_search_overview(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get overall paid search performance."""
        dimension_filter = FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(
                    value="Paid Search",
                    match_type=Filter.StringFilter.MatchType.EXACT
                )
            )
        )
        
        df = self._run_report(
            start_date, end_date,
            dimensions=[],
            metrics=[
                'sessions', 
                'totalUsers', 
                'newUsers',
                'bounceRate',
                'averageSessionDuration',
                'engagementRate',
                'screenPageViews',
            ],
            dimension_filter=dimension_filter
        )
        
        if df.empty:
            return {
                'sessions': 0,
                'users': 0,
                'new_users': 0,
                'bounce_rate': 0,
                'avg_session_duration': 0,
                'engagement_rate': 0,
                'pageviews': 0,
            }
        
        row = df.iloc[0]
        return {
            'sessions': int(row.get('sessions', 0)),
            'users': int(row.get('totalUsers', 0)),
            'new_users': int(row.get('newUsers', 0)),
            'bounce_rate': round(row.get('bounceRate', 0) * 100, 2),
            'avg_session_duration': round(row.get('averageSessionDuration', 0), 1),
            'engagement_rate': round(row.get('engagementRate', 0) * 100, 2),
            'pageviews': int(row.get('screenPageViews', 0)),
        }
    
    @cached(ttl_hours=24)
    def get_campaign_performance(
        self, start_date: str, end_date: str, limit: int = 20
    ) -> pd.DataFrame:
        """Get performance by campaign."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['sessionCampaignName'],
            metrics=[
                'sessions', 
                'totalUsers',
                'newUsers',
                'bounceRate', 
                'averageSessionDuration',
                'engagementRate',
            ],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='sessions'), 
                desc=True
            )],
            limit=limit
        )
        
        if not df.empty:
            # Filter out (not set) if there are other campaigns
            if len(df) > 1:
                df = df[df['sessionCampaignName'] != '(not set)']
            df['bounceRate'] = (df['bounceRate'] * 100).round(2)
            df['engagementRate'] = (df['engagementRate'] * 100).round(2)
        
        return df
    
    # =========================================================================
    # CONTENT PERFORMANCE
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_top_pages(
        self, start_date: str, end_date: str, limit: int = None
    ) -> pd.DataFrame:
        """Get top pages by pageviews with engagement metrics."""
        limit = limit or self._settings.top_pages_limit
        
        df = self._run_report(
            start_date, end_date,
            dimensions=['pagePath', 'pageTitle'],
            metrics=[
                'screenPageViews', 
                'averageSessionDuration',
                'bounceRate',
                'activeUsers',
            ],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='screenPageViews'), 
                desc=True
            )],
            limit=limit
        )
        
        if not df.empty:
            total_pageviews = df['screenPageViews'].sum()
            df['pct_of_total'] = (df['screenPageViews'] / total_pageviews * 100).round(2)
            df['bounceRate'] = (df['bounceRate'] * 100).round(2)
            df['averageSessionDuration'] = df['averageSessionDuration'].round(1)
            df['avg_time_formatted'] = df['averageSessionDuration'].apply(format_duration)
        
        return df
    
    @cached(ttl_hours=24)
    def get_landing_pages(
        self, start_date: str, end_date: str, limit: int = 20
    ) -> pd.DataFrame:
        """Get top landing pages (entry points)."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['landingPage'],
            metrics=[
                'sessions',
                'totalUsers',
                'bounceRate',
                'averageSessionDuration',
                'engagementRate',
            ],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='sessions'), 
                desc=True
            )],
            limit=limit
        )
        
        if not df.empty:
            total_sessions = df['sessions'].sum()
            df['pct_of_entries'] = (df['sessions'] / total_sessions * 100).round(2)
            df['bounceRate'] = (df['bounceRate'] * 100).round(2)
            df['engagementRate'] = (df['engagementRate'] * 100).round(2)
        
        return df
    
    @cached(ttl_hours=24)
    def get_homepage_engagement(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get engagement metrics specifically for homepage."""
        # Build filter for homepage paths
        homepage_paths = self.config.homepage_paths or ["/"]
        
        # For simplicity, use exact match on "/"
        dimension_filter = FilterExpression(
            filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    value="/",
                    match_type=Filter.StringFilter.MatchType.EXACT
                )
            )
        )
        
        df = self._run_report(
            start_date, end_date,
            dimensions=['pagePath'],
            metrics=[
                'screenPageViews',
                'averageSessionDuration',
                'bounceRate',
                'activeUsers',
            ],
            dimension_filter=dimension_filter
        )
        
        # Get total pageviews for percentage
        total_df = self._run_report(
            start_date, end_date,
            dimensions=[],
            metrics=['screenPageViews']
        )
        total_pageviews = total_df.iloc[0]['screenPageViews'] if not total_df.empty else 1
        
        if df.empty:
            return {
                'pageviews': 0,
                'pct_of_total': 0,
                'avg_time': 0,
                'bounce_rate': 0,
                'users': 0,
            }
        
        row = df.iloc[0]
        return {
            'pageviews': int(row.get('screenPageViews', 0)),
            'pct_of_total': round((row.get('screenPageViews', 0) / total_pageviews) * 100, 2),
            'avg_time': round(row.get('averageSessionDuration', 0), 1),
            'bounce_rate': round(row.get('bounceRate', 0) * 100, 2),
            'users': int(row.get('activeUsers', 0)),
        }
    
    # =========================================================================
    # AUDIENCE INSIGHTS
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_device_breakdown(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get user engagement by device category."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['deviceCategory'],
            metrics=[
                'totalUsers',
                'sessions',
                'screenPageViews',
                'averageSessionDuration',
                'bounceRate',
                'engagementRate',
            ]
        )
        
        if not df.empty:
            total_users = df['totalUsers'].sum()
            df['user_share'] = (df['totalUsers'] / total_users * 100).round(2)
            df['bounceRate'] = (df['bounceRate'] * 100).round(2)
            df['engagementRate'] = (df['engagementRate'] * 100).round(2)
        
        return df
    
    @cached(ttl_hours=24)
    def get_geography(self, start_date: str, end_date: str, limit: int = 20) -> pd.DataFrame:
        """Get traffic by country."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['country'],
            metrics=['totalUsers', 'sessions', 'engagementRate'],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='totalUsers'), 
                desc=True
            )],
            limit=limit
        )
        
        if not df.empty:
            total_users = df['totalUsers'].sum()
            df['user_share'] = (df['totalUsers'] / total_users * 100).round(2)
            df['engagementRate'] = (df['engagementRate'] * 100).round(2)
        
        return df
    
    @cached(ttl_hours=24)
    def get_us_states(self, start_date: str, end_date: str, limit: int = 15) -> pd.DataFrame:
        """Get traffic by US state (for US-focused nonprofits)."""
        dimension_filter = FilterExpression(
            filter=Filter(
                field_name="country",
                string_filter=Filter.StringFilter(
                    value="United States",
                    match_type=Filter.StringFilter.MatchType.EXACT
                )
            )
        )
        
        df = self._run_report(
            start_date, end_date,
            dimensions=['region'],
            metrics=['totalUsers', 'sessions', 'engagementRate'],
            dimension_filter=dimension_filter,
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='totalUsers'), 
                desc=True
            )],
            limit=limit
        )
        
        if not df.empty:
            df['engagementRate'] = (df['engagementRate'] * 100).round(2)
        
        return df
    
    @cached(ttl_hours=24)
    def get_new_vs_returning(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get new vs returning user breakdown."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['newVsReturning'],
            metrics=[
                'totalUsers',
                'sessions',
                'bounceRate',
                'averageSessionDuration',
                'screenPageViewsPerSession',
            ]
        )
        
        result = {'new': {}, 'returning': {}}
        
        if not df.empty:
            total_users = df['totalUsers'].sum()
            for _, row in df.iterrows():
                user_type = row['newVsReturning'].lower()
                if user_type in result:
                    result[user_type] = {
                        'users': int(row['totalUsers']),
                        'pct_of_total': round(row['totalUsers'] / total_users * 100, 2),
                        'sessions': int(row['sessions']),
                        'bounce_rate': round(row['bounceRate'] * 100, 2),
                        'avg_session_duration': round(row['averageSessionDuration'], 1),
                        'pages_per_session': round(row['screenPageViewsPerSession'], 2),
                    }
        
        return result
    
    # =========================================================================
    # EVENTS & CONVERSIONS
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_top_events(self, start_date: str, end_date: str, limit: int = 20) -> pd.DataFrame:
        """Get top events by count."""
        df = self._run_report(
            start_date, end_date,
            dimensions=['eventName'],
            metrics=['eventCount', 'totalUsers'],
            order_bys=[OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name='eventCount'), 
                desc=True
            )],
            limit=limit
        )
        
        # Filter out standard GA4 events if desired
        standard_events = ['page_view', 'session_start', 'first_visit', 'user_engagement']
        if not df.empty and len(df) > len(standard_events):
            df['is_custom'] = ~df['eventName'].isin(standard_events)
        
        return df
    
    @cached(ttl_hours=24)
    def get_scroll_depth(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get scroll depth data (if scroll tracking is enabled)."""
        dimension_filter = FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(
                    value="scroll",
                    match_type=Filter.StringFilter.MatchType.EXACT
                )
            )
        )
        
        return self._run_report(
            start_date, end_date,
            dimensions=['percentScrolled'],
            metrics=['eventCount'],
            dimension_filter=dimension_filter
        )
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    def get_all_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get all metrics in a single call for comprehensive reporting.
        
        Returns a dictionary with all data categories.
        """
        return {
            'traffic_overview': self.get_traffic_overview(start_date, end_date),
            'traffic_by_month': self.get_traffic_by_month(start_date, end_date),
            'traffic_by_channel': self.get_traffic_by_channel(start_date, end_date),
            'traffic_by_source': self.get_traffic_by_source_medium(start_date, end_date),
            'top_pages': self.get_top_pages(start_date, end_date),
            'landing_pages': self.get_landing_pages(start_date, end_date),
            'homepage_engagement': self.get_homepage_engagement(start_date, end_date),
            'device_breakdown': self.get_device_breakdown(start_date, end_date),
            'geography': self.get_geography(start_date, end_date),
            'new_vs_returning': self.get_new_vs_returning(start_date, end_date),
            'paid_search': self.get_paid_search_overview(start_date, end_date),
            'campaigns': self.get_campaign_performance(start_date, end_date),
            'top_events': self.get_top_events(start_date, end_date),
        }

