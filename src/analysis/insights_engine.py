"""
Insights Engine
===============
Automatic generation of actionable insights from analytics data.

This is what separates a data dump from a McKinsey-grade report.
Provides executive summary, key findings, and recommendations.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import pandas as pd

from src.utils.formatting import calculate_change, ChangeMetric
from config.settings import get_settings


@dataclass
class Insight:
    """A single insight/finding."""
    category: str           # traffic, engagement, search, content, acquisition
    type: str               # positive, negative, neutral, opportunity
    priority: int           # 1 (critical) to 5 (informational)
    headline: str           # Short summary
    detail: str             # Full explanation
    metric_name: str        # Related metric
    metric_value: Any       # Current value
    metric_change: Optional[ChangeMetric] = None
    recommendation: Optional[str] = None
    data_points: Dict = field(default_factory=dict)


class InsightsEngine:
    """
    Generates actionable insights from analytics data.
    
    Analyzes patterns, identifies opportunities, and creates
    executive-ready summaries.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.insights: List[Insight] = []
        self.benchmarks = self.settings.benchmarks
    
    def analyze(
        self,
        ga4_current: Dict[str, Any],
        ga4_previous: Dict[str, Any],
        gsc_current: Dict[str, Any],
        gsc_previous: Dict[str, Any],
    ) -> List[Insight]:
        """
        Run full analysis and generate insights.
        
        Args:
            ga4_current: Current period GA4 data
            ga4_previous: Previous period GA4 data
            gsc_current: Current period GSC data
            gsc_previous: Previous period GSC data
        
        Returns:
            List of Insight objects sorted by priority
        """
        self.insights = []
        
        # Run all analysis modules
        self._analyze_traffic(ga4_current, ga4_previous)
        self._analyze_engagement(ga4_current, ga4_previous)
        self._analyze_acquisition(ga4_current, ga4_previous)
        self._analyze_content(ga4_current, ga4_previous)
        self._analyze_search(gsc_current, gsc_previous)
        self._analyze_opportunities(ga4_current, gsc_current)
        
        # Sort by priority
        self.insights.sort(key=lambda x: x.priority)
        
        return self.insights
    
    def _analyze_traffic(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ) -> None:
        """Analyze traffic patterns and changes."""
        curr_overview = current.get('traffic_overview', {})
        prev_overview = previous.get('traffic_overview', {})
        
        if not curr_overview:
            return
        
        # Total users change
        users_change = calculate_change(
            curr_overview.get('total_users', 0),
            prev_overview.get('total_users', 0),
            significant_threshold=self.settings.significant_change_threshold,
            anomaly_threshold=self.settings.anomaly_threshold
        )
        
        if users_change.is_significant:
            direction = "increased" if users_change.direction == "up" else "decreased"
            insight_type = "positive" if users_change.direction == "up" else "negative"
            
            self.insights.append(Insight(
                category="traffic",
                type=insight_type,
                priority=2 if users_change.is_anomaly else 3,
                headline=f"Website traffic {direction} by {abs(users_change.change_pct):.1f}% YoY",
                detail=f"Total visitors went from {users_change.formatted_previous} to {users_change.formatted_current}. "
                       f"This represents a {abs(users_change.change_abs):,.0f} user difference.",
                metric_name="total_users",
                metric_value=curr_overview.get('total_users', 0),
                metric_change=users_change,
                recommendation=self._get_traffic_recommendation(users_change)
            ))
        
        # New vs returning analysis
        new_users = curr_overview.get('new_users', 0)
        total_users = curr_overview.get('total_users', 1)
        new_user_pct = (new_users / total_users) * 100 if total_users else 0
        
        if new_user_pct > 80:
            self.insights.append(Insight(
                category="traffic",
                type="opportunity",
                priority=3,
                headline=f"{new_user_pct:.0f}% of visitors are new users",
                detail="High new user percentage indicates strong awareness-building but potential "
                       "opportunity to improve retention and return visits.",
                metric_name="new_user_percentage",
                metric_value=new_user_pct,
                recommendation="Consider implementing email newsletter signup, retargeting campaigns, "
                              "or engaging content series to bring visitors back."
            ))
        elif new_user_pct < 50:
            self.insights.append(Insight(
                category="traffic",
                type="positive",
                priority=4,
                headline="Strong returning visitor base",
                detail=f"Only {new_user_pct:.0f}% of visitors are new, indicating high engagement "
                       f"and loyalty from existing audience.",
                metric_name="new_user_percentage",
                metric_value=new_user_pct,
                recommendation="Focus on expanding reach to new audiences while maintaining "
                              "engagement with loyal visitors."
            ))
    
    def _analyze_engagement(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ) -> None:
        """Analyze user engagement patterns."""
        curr_overview = current.get('traffic_overview', {})
        prev_overview = previous.get('traffic_overview', {})
        
        if not curr_overview:
            return
        
        # Bounce rate analysis
        bounce_rate = curr_overview.get('bounce_rate', 0)
        prev_bounce = prev_overview.get('bounce_rate', 0)
        benchmark_bounce = self.benchmarks.get('bounce_rate', 55)
        
        bounce_change = calculate_change(
            bounce_rate, prev_bounce,
            inverse=True  # Lower is better
        )
        
        if bounce_rate > benchmark_bounce + 10:
            self.insights.append(Insight(
                category="engagement",
                type="negative",
                priority=2,
                headline=f"Bounce rate ({bounce_rate:.1f}%) significantly above nonprofit average",
                detail=f"The current bounce rate is {bounce_rate - benchmark_bounce:.1f}% higher than "
                       f"the typical nonprofit benchmark of {benchmark_bounce}%. This may indicate "
                       f"content mismatch or poor user experience.",
                metric_name="bounce_rate",
                metric_value=bounce_rate,
                metric_change=bounce_change,
                recommendation="Review top landing pages for relevance, improve page load speed, "
                              "and ensure clear calls-to-action above the fold."
            ))
        elif bounce_rate < benchmark_bounce - 10:
            self.insights.append(Insight(
                category="engagement",
                type="positive",
                priority=4,
                headline=f"Excellent bounce rate at {bounce_rate:.1f}%",
                detail=f"Bounce rate is {benchmark_bounce - bounce_rate:.1f}% better than the "
                       f"nonprofit average of {benchmark_bounce}%. Visitors are engaging with content.",
                metric_name="bounce_rate",
                metric_value=bounce_rate,
                metric_change=bounce_change,
            ))
        
        # Session duration analysis
        avg_duration = curr_overview.get('avg_session_duration', 0)
        benchmark_duration = self.benchmarks.get('avg_session_duration', 120)
        
        if avg_duration > benchmark_duration * 1.5:
            self.insights.append(Insight(
                category="engagement",
                type="positive",
                priority=3,
                headline=f"Above-average session duration ({avg_duration/60:.1f} min)",
                detail="Visitors are spending significantly more time on the site than typical, "
                       "indicating high-quality, engaging content.",
                metric_name="avg_session_duration",
                metric_value=avg_duration,
                recommendation="Identify top-performing content and apply similar patterns "
                              "to underperforming pages."
            ))
        elif avg_duration < benchmark_duration * 0.5:
            self.insights.append(Insight(
                category="engagement",
                type="negative",
                priority=2,
                headline=f"Low session duration ({avg_duration/60:.1f} min)",
                detail=f"Average session duration of {avg_duration:.0f} seconds is below the "
                       f"benchmark of {benchmark_duration} seconds. Visitors may not be finding "
                       f"what they need.",
                metric_name="avg_session_duration",
                metric_value=avg_duration,
                recommendation="Improve content depth, add internal linking, and create "
                              "clear pathways to keep visitors engaged."
            ))
    
    def _analyze_acquisition(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ) -> None:
        """Analyze traffic acquisition channels."""
        channels = current.get('traffic_by_channel', pd.DataFrame())
        
        if channels.empty:
            return
        
        total_sessions = channels['sessions'].sum()
        
        # Organic search analysis
        organic = channels[channels['sessionDefaultChannelGroup'].str.lower() == 'organic search']
        if not organic.empty:
            organic_share = organic['session_share'].values[0]
            benchmark_organic = self.benchmarks.get('organic_traffic_share', 40)
            
            if organic_share > benchmark_organic + 15:
                self.insights.append(Insight(
                    category="acquisition",
                    type="positive",
                    priority=3,
                    headline=f"Strong organic search presence ({organic_share:.1f}% of traffic)",
                    detail="Organic search is driving a significant portion of traffic, "
                           "indicating good SEO performance and content visibility.",
                    metric_name="organic_share",
                    metric_value=organic_share,
                ))
            elif organic_share < benchmark_organic - 15:
                self.insights.append(Insight(
                    category="acquisition",
                    type="opportunity",
                    priority=2,
                    headline=f"Organic search opportunity ({organic_share:.1f}% of traffic)",
                    detail=f"Organic search accounts for only {organic_share:.1f}% of traffic, "
                           f"below the nonprofit average of {benchmark_organic}%. "
                           f"SEO improvements could significantly increase reach.",
                    metric_name="organic_share",
                    metric_value=organic_share,
                    recommendation="Invest in content marketing, keyword optimization, and "
                                  "technical SEO to improve organic visibility."
                ))
        
        # Direct traffic analysis
        direct = channels[channels['sessionDefaultChannelGroup'].str.lower() == 'direct']
        if not direct.empty:
            direct_share = direct['session_share'].values[0]
            if direct_share > 40:
                self.insights.append(Insight(
                    category="acquisition",
                    type="neutral",
                    priority=4,
                    headline=f"High direct traffic ({direct_share:.1f}%)",
                    detail="High direct traffic often indicates strong brand recognition, "
                           "but may also include untracked referrals or dark social shares.",
                    metric_name="direct_share",
                    metric_value=direct_share,
                    recommendation="Ensure proper UTM tagging on all campaigns and consider "
                                  "implementing link tracking for better attribution."
                ))
    
    def _analyze_content(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ) -> None:
        """Analyze content performance."""
        top_pages = current.get('top_pages', pd.DataFrame())
        
        if top_pages.empty:
            return
        
        # Homepage dependency check
        homepage_data = top_pages[top_pages['pagePath'] == '/']
        if not homepage_data.empty:
            homepage_share = homepage_data['pct_of_total'].values[0]
            if homepage_share > 50:
                self.insights.append(Insight(
                    category="content",
                    type="opportunity",
                    priority=3,
                    headline=f"High homepage concentration ({homepage_share:.1f}% of pageviews)",
                    detail="More than half of all pageviews go to the homepage. This may indicate "
                           "weak internal linking or underperforming deeper content.",
                    metric_name="homepage_share",
                    metric_value=homepage_share,
                    recommendation="Strengthen calls-to-action on homepage, improve internal linking, "
                                  "and promote specific content/programs more prominently."
                ))
        
        # Content depth analysis
        if len(top_pages) >= 3:
            top_3_share = top_pages.head(3)['pct_of_total'].sum()
            if top_3_share > 70:
                self.insights.append(Insight(
                    category="content",
                    type="opportunity",
                    priority=3,
                    headline=f"Traffic concentrated in top 3 pages ({top_3_share:.1f}%)",
                    detail="The majority of traffic goes to just 3 pages. There may be an "
                           "opportunity to promote other valuable content.",
                    metric_name="top_3_concentration",
                    metric_value=top_3_share,
                    recommendation="Review analytics for underperforming pages with high-value content. "
                                  "Consider refreshing or repromoting them."
                ))
    
    def _analyze_search(
        self, current: Dict[str, Any], previous: Dict[str, Any]
    ) -> None:
        """Analyze search console data."""
        overview = current.get('overview', {})
        prev_overview = previous.get('overview', {})
        
        if not overview:
            return
        
        # Click trend
        clicks_change = calculate_change(
            overview.get('total_clicks', 0),
            prev_overview.get('total_clicks', 0),
            significant_threshold=10
        )
        
        if clicks_change.is_significant:
            direction = "increased" if clicks_change.direction == "up" else "decreased"
            insight_type = "positive" if clicks_change.direction == "up" else "negative"
            
            self.insights.append(Insight(
                category="search",
                type=insight_type,
                priority=2,
                headline=f"Search clicks {direction} {abs(clicks_change.change_pct):.1f}% YoY",
                detail=f"Total search clicks went from {clicks_change.formatted_previous} to "
                       f"{clicks_change.formatted_current}. This reflects changes in search visibility.",
                metric_name="total_clicks",
                metric_value=overview.get('total_clicks', 0),
                metric_change=clicks_change,
            ))
        
        # Position trend
        position_change = calculate_change(
            overview.get('avg_position', 0),
            prev_overview.get('avg_position', 0),
            inverse=True  # Lower position is better
        )
        
        avg_position = overview.get('avg_position', 0)
        if avg_position > 20:
            self.insights.append(Insight(
                category="search",
                type="opportunity",
                priority=2,
                headline=f"Average search position needs improvement ({avg_position:.1f})",
                detail="Average position is beyond page 2 of search results. Most clicks "
                       "happen on page 1 (positions 1-10).",
                metric_name="avg_position",
                metric_value=avg_position,
                recommendation="Focus on improving rankings for high-impression keywords. "
                              "Consider content optimization and link building."
            ))
        elif avg_position <= 10:
            self.insights.append(Insight(
                category="search",
                type="positive",
                priority=3,
                headline=f"Strong search visibility (avg position: {avg_position:.1f})",
                detail="Average position is on page 1 of search results, where most clicks occur.",
                metric_name="avg_position",
                metric_value=avg_position,
            ))
        
        # Keyword opportunities
        opportunities = current.get('keyword_opportunities', pd.DataFrame())
        if not opportunities.empty and len(opportunities) >= 5:
            total_impressions = opportunities['impressions'].sum()
            self.insights.append(Insight(
                category="search",
                type="opportunity",
                priority=2,
                headline=f"Found {len(opportunities)} keyword opportunities",
                detail=f"Identified keywords with high impressions but low CTR that could "
                       f"drive additional traffic with optimization. Combined monthly impressions: "
                       f"{total_impressions:,}.",
                metric_name="keyword_opportunities",
                metric_value=len(opportunities),
                recommendation="Review these keywords and optimize title tags, meta descriptions, "
                              "and content to improve click-through rates."
            ))
    
    def _analyze_opportunities(
        self, ga4_data: Dict[str, Any], gsc_data: Dict[str, Any]
    ) -> None:
        """Cross-analyze data to find optimization opportunities."""
        # Mobile experience check
        device_data = ga4_data.get('device_breakdown', pd.DataFrame())
        
        if not device_data.empty:
            mobile = device_data[device_data['deviceCategory'].str.lower() == 'mobile']
            desktop = device_data[device_data['deviceCategory'].str.lower() == 'desktop']
            
            if not mobile.empty and not desktop.empty:
                mobile_bounce = mobile['bounceRate'].values[0]
                desktop_bounce = desktop['bounceRate'].values[0]
                mobile_share = mobile['user_share'].values[0]
                
                if mobile_share > 50 and mobile_bounce > desktop_bounce + 10:
                    self.insights.append(Insight(
                        category="opportunity",
                        type="negative",
                        priority=1,
                        headline="Mobile experience needs attention",
                        detail=f"Mobile makes up {mobile_share:.0f}% of traffic but has a "
                               f"bounce rate {mobile_bounce - desktop_bounce:.1f}% higher than desktop. "
                               f"Mobile: {mobile_bounce:.1f}%, Desktop: {desktop_bounce:.1f}%.",
                        metric_name="mobile_bounce_rate",
                        metric_value=mobile_bounce,
                        recommendation="Prioritize mobile experience improvements: faster load times, "
                                      "responsive design, touch-friendly navigation, and readable text."
                    ))
    
    def _get_traffic_recommendation(self, change: ChangeMetric) -> str:
        """Generate traffic-specific recommendation based on change."""
        if change.direction == "down":
            if change.is_anomaly:
                return ("Urgent: Investigate significant traffic decline. Check for technical issues, "
                        "algorithm updates, or seasonal factors. Review acquisition channels to identify source.")
            return ("Monitor traffic trends and review marketing channel performance. "
                    "Consider increasing promotion or content freshness.")
        else:
            return ("Maintain momentum by analyzing what's working. Document successful strategies "
                    "and apply learnings to underperforming areas.")
    
    def get_executive_summary(self) -> str:
        """Generate a brief executive summary from insights."""
        if not self.insights:
            return "Insufficient data to generate executive summary."
        
        critical = [i for i in self.insights if i.priority <= 2]
        positive = [i for i in self.insights if i.type == "positive"]
        opportunities = [i for i in self.insights if i.type == "opportunity"]
        
        summary_parts = []
        
        # Lead with key metrics
        traffic_insight = next((i for i in self.insights if i.metric_name == "total_users"), None)
        if traffic_insight and traffic_insight.metric_change:
            change = traffic_insight.metric_change
            direction = "grew" if change.direction == "up" else "declined"
            summary_parts.append(
                f"Website traffic {direction} by {abs(change.change_pct):.1f}% year-over-year, "
                f"with {traffic_insight.metric_value:,} total visitors this quarter."
            )
        
        # Highlight wins
        if positive:
            win = positive[0]
            summary_parts.append(f"Key strength: {win.headline}.")
        
        # Note opportunities
        if opportunities:
            opp = opportunities[0]
            summary_parts.append(f"Primary opportunity: {opp.headline}.")
        
        # Critical issues
        if critical:
            crit = critical[0]
            summary_parts.append(f"Requires attention: {crit.headline}.")
        
        return " ".join(summary_parts)
    
    def get_key_recommendations(self, limit: int = 5) -> List[str]:
        """Get top actionable recommendations."""
        recommendations = []
        
        for insight in self.insights:
            if insight.recommendation and len(recommendations) < limit:
                recommendations.append(insight.recommendation)
        
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert insights to dictionary for serialization."""
        return {
            'executive_summary': self.get_executive_summary(),
            'key_recommendations': self.get_key_recommendations(),
            'insights': [
                {
                    'category': i.category,
                    'type': i.type,
                    'priority': i.priority,
                    'headline': i.headline,
                    'detail': i.detail,
                    'metric_name': i.metric_name,
                    'metric_value': i.metric_value,
                    'recommendation': i.recommendation,
                }
                for i in self.insights
            ],
            'insights_by_category': self._group_by_category(),
        }
    
    def _group_by_category(self) -> Dict[str, List[Dict]]:
        """Group insights by category."""
        grouped = {}
        for insight in self.insights:
            if insight.category not in grouped:
                grouped[insight.category] = []
            grouped[insight.category].append({
                'headline': insight.headline,
                'type': insight.type,
                'priority': insight.priority,
            })
        return grouped

