"""
Google Search Console API Client
=================================
Comprehensive search performance data extraction.

This client provides access to all key SEO metrics:
- Search queries (keywords) with clicks, impressions, CTR, position
- Page performance in search results
- Device breakdown for search
- Country breakdown for search
- Search appearance data (rich results, etc.)
"""

from typing import Optional, Dict, List, Any
import pandas as pd

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config.settings import ClientConfig, get_settings
from src.utils.cache import cached


class SearchConsoleClient:
    """
    Google Search Console API client.
    
    Provides high-level methods for extracting search performance data
    with automatic caching and error handling.
    """
    
    def __init__(self, client_config: ClientConfig):
        """
        Initialize Search Console client.
        
        Args:
            client_config: Client configuration with credentials and site URL
        """
        self.config = client_config
        self.client_name = client_config.name
        self.site_url = client_config.gsc_site_url
        
        # Initialize API client
        credentials = service_account.Credentials.from_service_account_file(
            str(client_config.get_credentials_path()),
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        self._service = build('searchconsole', 'v1', credentials=credentials)
        self._settings = get_settings()
    
    def _run_query(
        self,
        start_date: str,
        end_date: str,
        dimensions: List[str] = None,
        row_limit: int = None,
        dimension_filter: Dict = None,
        data_state: str = 'final',
    ) -> pd.DataFrame:
        """
        Run a Search Console query and return as DataFrame.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            dimensions: List of dimensions (query, page, country, device, date)
            row_limit: Max rows to return
            dimension_filter: Optional filter configuration
            data_state: 'final' or 'all' (includes fresh data)
        
        Returns:
            DataFrame with search analytics data
        """
        dimensions = dimensions or ['query']
        row_limit = row_limit or self._settings.default_row_limit
        
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': row_limit,
            'dataState': data_state,
        }
        
        if dimension_filter:
            request_body['dimensionFilterGroups'] = [dimension_filter]
        
        response = self._service.searchanalytics().query(
            siteUrl=self.site_url,
            body=request_body
        ).execute()
        
        rows = response.get('rows', [])
        
        if not rows:
            return pd.DataFrame()
        
        data = []
        for row in rows:
            row_data = {}
            for i, dim in enumerate(dimensions):
                row_data[dim] = row['keys'][i]
            row_data['clicks'] = row['clicks']
            row_data['impressions'] = row['impressions']
            row_data['ctr'] = round(row['ctr'] * 100, 2)  # Convert to percentage
            row_data['position'] = round(row['position'], 1)
            data.append(row_data)
        
        return pd.DataFrame(data)
    
    # =========================================================================
    # KEYWORD ANALYSIS
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_top_keywords_by_clicks(
        self, start_date: str, end_date: str, limit: int = None
    ) -> pd.DataFrame:
        """Get top keywords sorted by clicks."""
        limit = limit or self._settings.top_keywords_limit
        df = self._run_query(start_date, end_date, ['query'], row_limit=limit)
        if not df.empty:
            df = df.sort_values('clicks', ascending=False).head(limit)
        return df
    
    @cached(ttl_hours=24)
    def get_top_keywords_by_impressions(
        self, start_date: str, end_date: str, limit: int = None
    ) -> pd.DataFrame:
        """Get top keywords sorted by impressions."""
        limit = limit or self._settings.top_keywords_limit
        df = self._run_query(start_date, end_date, ['query'], row_limit=limit)
        if not df.empty:
            df = df.sort_values('impressions', ascending=False).head(limit)
        return df
    
    @cached(ttl_hours=24)
    def get_top_keywords_by_ctr(
        self, start_date: str, end_date: str, limit: int = 25, min_impressions: int = 100
    ) -> pd.DataFrame:
        """
        Get top keywords by CTR (with minimum impressions filter).
        
        Args:
            min_impressions: Minimum impressions to filter noise
        """
        df = self._run_query(start_date, end_date, ['query'], row_limit=500)
        if not df.empty:
            df = df[df['impressions'] >= min_impressions]
            df = df.sort_values('ctr', ascending=False).head(limit)
        return df
    
    @cached(ttl_hours=24)
    def get_keyword_opportunities(
        self, start_date: str, end_date: str, limit: int = 25
    ) -> pd.DataFrame:
        """
        Find keyword opportunities - high impressions but low CTR.
        These are keywords where you're showing but not getting clicks.
        Good candidates for optimization.
        """
        df = self._run_query(start_date, end_date, ['query'], row_limit=500)
        if not df.empty:
            # High impressions, low CTR, position between 5-20 (page 1-2)
            df = df[
                (df['impressions'] >= 50) & 
                (df['ctr'] < 3.0) & 
                (df['position'] >= 5) & 
                (df['position'] <= 20)
            ]
            # Score by impression potential
            df['opportunity_score'] = df['impressions'] * (10 - df['position']) / 10
            df = df.sort_values('opportunity_score', ascending=False).head(limit)
        return df
    
    @cached(ttl_hours=24)
    def get_branded_vs_nonbranded(
        self, start_date: str, end_date: str, brand_terms: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze branded vs non-branded search performance.
        
        Args:
            brand_terms: List of brand-related terms to filter.
                         Defaults to common variations.
        """
        if brand_terms is None:
            # Extract likely brand terms from site URL
            brand_terms = ['bee conservancy', 'thebeeconservancy', 'bee', 'conservancy']
        
        df = self._run_query(start_date, end_date, ['query'], row_limit=1000)
        
        if df.empty:
            return {'branded': {}, 'non_branded': {}}
        
        # Identify branded queries
        brand_pattern = '|'.join(brand_terms)
        df['is_branded'] = df['query'].str.lower().str.contains(brand_pattern, na=False)
        
        branded = df[df['is_branded']]
        non_branded = df[~df['is_branded']]
        
        return {
            'branded': {
                'queries': len(branded),
                'clicks': int(branded['clicks'].sum()),
                'impressions': int(branded['impressions'].sum()),
                'avg_ctr': round(branded['ctr'].mean(), 2) if not branded.empty else 0,
                'avg_position': round(branded['position'].mean(), 1) if not branded.empty else 0,
            },
            'non_branded': {
                'queries': len(non_branded),
                'clicks': int(non_branded['clicks'].sum()),
                'impressions': int(non_branded['impressions'].sum()),
                'avg_ctr': round(non_branded['ctr'].mean(), 2) if not non_branded.empty else 0,
                'avg_position': round(non_branded['position'].mean(), 1) if not non_branded.empty else 0,
            }
        }
    
    # =========================================================================
    # PAGE PERFORMANCE
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_top_pages(
        self, start_date: str, end_date: str, limit: int = None
    ) -> pd.DataFrame:
        """Get top pages by clicks in search results."""
        limit = limit or self._settings.top_pages_limit
        df = self._run_query(start_date, end_date, ['page'], row_limit=limit)
        if not df.empty:
            total_clicks = df['clicks'].sum()
            df['click_share'] = (df['clicks'] / total_clicks * 100).round(2)
            df = df.sort_values('clicks', ascending=False).head(limit)
        return df
    
    @cached(ttl_hours=24)
    def get_page_query_analysis(
        self, start_date: str, end_date: str, page_url: str
    ) -> pd.DataFrame:
        """Get all queries driving traffic to a specific page."""
        dimension_filter = {
            'filters': [{
                'dimension': 'page',
                'expression': page_url
            }]
        }
        return self._run_query(
            start_date, end_date, 
            ['query'], 
            row_limit=100,
            dimension_filter=dimension_filter
        )
    
    # =========================================================================
    # SEARCH TRENDS
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_daily_performance(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get daily search performance trends."""
        df = self._run_query(start_date, end_date, ['date'], row_limit=500)
        if not df.empty:
            df = df.sort_values('date')
        return df
    
    @cached(ttl_hours=24)
    def get_weekly_performance(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get weekly aggregated search performance."""
        df = self.get_daily_performance(start_date, end_date)
        
        if df.empty:
            return df
        
        df['date'] = pd.to_datetime(df['date'])
        df['week'] = df['date'].dt.isocalendar().week
        df['year'] = df['date'].dt.year
        
        weekly = df.groupby(['year', 'week']).agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        weekly['ctr'] = weekly['ctr'].round(2)
        weekly['position'] = weekly['position'].round(1)
        
        return weekly
    
    # =========================================================================
    # DEVICE & COUNTRY BREAKDOWN
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_device_breakdown(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get search performance by device type."""
        df = self._run_query(start_date, end_date, ['device'], row_limit=10)
        if not df.empty:
            total_clicks = df['clicks'].sum()
            df['click_share'] = (df['clicks'] / total_clicks * 100).round(2)
        return df
    
    @cached(ttl_hours=24)
    def get_country_breakdown(
        self, start_date: str, end_date: str, limit: int = 20
    ) -> pd.DataFrame:
        """Get search performance by country."""
        df = self._run_query(start_date, end_date, ['country'], row_limit=limit)
        if not df.empty:
            total_clicks = df['clicks'].sum()
            df['click_share'] = (df['clicks'] / total_clicks * 100).round(2)
            df = df.sort_values('clicks', ascending=False)
        return df
    
    # =========================================================================
    # SEARCH APPEARANCE
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_search_appearance(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get performance by search appearance type.
        Shows rich results, featured snippets, etc.
        """
        df = self._run_query(start_date, end_date, ['searchAppearance'], row_limit=50)
        return df
    
    # =========================================================================
    # SUMMARY METRICS
    # =========================================================================
    
    @cached(ttl_hours=24)
    def get_search_overview(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get overall search performance summary."""
        df = self._run_query(start_date, end_date, dimensions=[], row_limit=1)
        
        if df.empty:
            return {
                'total_clicks': 0,
                'total_impressions': 0,
                'avg_ctr': 0,
                'avg_position': 0,
            }
        
        # Need to query without dimensions for totals
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dataState': 'final',
        }
        
        response = self._service.searchanalytics().query(
            siteUrl=self.site_url,
            body=request_body
        ).execute()
        
        rows = response.get('rows', [])
        if rows:
            row = rows[0]
            return {
                'total_clicks': row['clicks'],
                'total_impressions': row['impressions'],
                'avg_ctr': round(row['ctr'] * 100, 2),
                'avg_position': round(row['position'], 1),
            }
        
        return {
            'total_clicks': 0,
            'total_impressions': 0,
            'avg_ctr': 0,
            'avg_position': 0,
        }
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    def get_all_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get all search console metrics in a single call.
        
        Returns a dictionary with all data categories.
        """
        return {
            'overview': self.get_search_overview(start_date, end_date),
            'top_keywords_clicks': self.get_top_keywords_by_clicks(start_date, end_date),
            'top_keywords_impressions': self.get_top_keywords_by_impressions(start_date, end_date),
            'top_keywords_ctr': self.get_top_keywords_by_ctr(start_date, end_date),
            'keyword_opportunities': self.get_keyword_opportunities(start_date, end_date),
            'branded_vs_nonbranded': self.get_branded_vs_nonbranded(start_date, end_date),
            'top_pages': self.get_top_pages(start_date, end_date),
            'daily_performance': self.get_daily_performance(start_date, end_date),
            'device_breakdown': self.get_device_breakdown(start_date, end_date),
            'country_breakdown': self.get_country_breakdown(start_date, end_date),
            'search_appearance': self.get_search_appearance(start_date, end_date),
        }

