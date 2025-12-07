"""
Nonprofit Analytics Dashboard
=============================
A beautiful Streamlit dashboard for quarterly analytics reporting.

Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json

from config.settings import get_settings, ClientConfig, OUTPUT_DIR
from src.reports.report_generator import ReportGenerator, QuarterlyReport


# =============================================================================
# PAGE CONFIG & STYLING
# =============================================================================

st.set_page_config(
    page_title="Nonprofit Analytics Dashboard",
    page_icon="🐝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for McKinsey-style aesthetics
st.markdown("""
<style>
    /* Main theme */
    :root {
        --primary: #2D5016;
        --secondary: #F4C430;
        --dark: #1F2937;
        --light: #F8FAFC;
    }
    
    /* Headers */
    h1 {
        color: #2D5016 !important;
        font-weight: 700 !important;
        font-family: 'Georgia', serif !important;
    }
    
    h2, h3 {
        color: #1F2937 !important;
        font-weight: 600 !important;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #2D5016 !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 1rem !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1F2937 !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: #F8FAFC !important;
    }
    
    /* Cards/containers */
    .insight-card {
        background: linear-gradient(135deg, #F8FAFC 0%, #E5E7EB 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #2D5016;
    }
    
    .positive {
        border-left-color: #22C55E !important;
    }
    
    .negative {
        border-left-color: #EF4444 !important;
    }
    
    .opportunity {
        border-left-color: #F4C430 !important;
    }
    
    /* Tables */
    .dataframe {
        font-size: 0.9rem !important;
    }
    
    /* Remove streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hero section */
    .hero {
        background: linear-gradient(135deg, #2D5016 0%, #1F4E0F 100%);
        padding: 30px;
        border-radius: 16px;
        color: white;
        margin-bottom: 30px;
    }
    
    .hero h1 {
        color: white !important;
        margin-bottom: 10px;
    }
    
    .hero p {
        color: #D1D5DB;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

if 'report' not in st.session_state:
    st.session_state.report = None
if 'client_name' not in st.session_state:
    st.session_state.client_name = None


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("# 🐝 Analytics Platform")
    st.markdown("---")
    
    # Client selection
    settings = get_settings()
    clients = settings.list_clients()
    
    if not clients:
        st.warning("No clients configured. Add a client YAML file to config/clients/")
        st.stop()
    
    selected_client = st.selectbox(
        "Select Client",
        clients,
        index=0 if clients else None
    )
    
    st.markdown("---")
    st.markdown("### 📅 Report Period")
    
    col1, col2 = st.columns(2)
    with col1:
        quarter = st.selectbox("Quarter", ["Q1", "Q2", "Q3", "Q4"], index=3)
    with col2:
        year = st.number_input("Year", min_value=2020, max_value=2030, value=2024)
    
    comparison = st.radio(
        "Comparison",
        ["Year-over-Year (YoY)", "Quarter-over-Quarter (QoQ)"],
        index=0
    )
    comparison_type = "yoy" if "YoY" in comparison else "qoq"
    
    st.markdown("---")
    
    generate_btn = st.button("🚀 Generate Report", type="primary", use_container_width=True)
    
    if generate_btn:
        with st.spinner("Fetching data from GA4 and Search Console..."):
            try:
                client_config = settings.load_client(selected_client)
                generator = ReportGenerator(client_config)
                report = generator.generate(quarter, year, comparison_type)
                st.session_state.report = report.to_dict()
                st.session_state.client_name = client_config.display_name
                st.success("Report generated!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    # Export buttons
    if st.session_state.report:
        st.markdown("### 📥 Export")
        
        if st.button("📊 Export to Excel", use_container_width=True):
            try:
                client_config = settings.load_client(selected_client)
                from src.reports.excel_exporter import ExcelExporter
                exporter = ExcelExporter(client_config)
                path = exporter.export(st.session_state.report)
                st.success(f"Saved: {path.name}")
            except Exception as e:
                st.error(f"Error: {e}")
        
        if st.button("📽️ Export to PowerPoint", use_container_width=True):
            try:
                client_config = settings.load_client(selected_client)
                from src.reports.powerpoint_exporter import PowerPointExporter
                exporter = PowerPointExporter(client_config)
                path = exporter.export(st.session_state.report)
                st.success(f"Saved: {path.name}")
            except Exception as e:
                st.error(f"Error: {e}")


# =============================================================================
# MAIN CONTENT
# =============================================================================

# Hero Section
st.markdown(f"""
<div class="hero">
    <h1>📊 Quarterly Analytics Report</h1>
    <p>{st.session_state.client_name or "Select a client and generate a report"}</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.report:
    st.info("👈 Select a client, choose the quarter/year, and click 'Generate Report' to get started.")
    
    # Show sample dashboard structure
    st.markdown("### 📋 This dashboard will include:")
    
    cols = st.columns(3)
    with cols[0]:
        st.markdown("""
        **🌐 Traffic Overview**
        - Total, new, returning users
        - Sessions and pageviews
        - Bounce rate trends
        """)
    
    with cols[1]:
        st.markdown("""
        **🔍 Search Performance**
        - Organic clicks & impressions
        - Top keywords
        - CTR & position trends
        """)
    
    with cols[2]:
        st.markdown("""
        **💡 Insights**
        - Auto-generated findings
        - Benchmark comparisons
        - Recommendations
        """)
    
    st.stop()

# Parse report data
report = st.session_state.report
metadata = report.get('metadata', {})
ga4 = report.get('ga4', {})
gsc = report.get('gsc', {})
pagespeed = report.get('pagespeed', {})
hotjar = report.get('hotjar', {})
google_ads = report.get('google_ads', {})
comparison = report.get('comparison', {})
insights = report.get('insights', {})

current_period = metadata.get('current_period', {}).get('label', '')
previous_period = metadata.get('previous_period', {}).get('label', '')

# Show active integrations
integrations = metadata.get('integrations', {})
active_integrations = [k for k, v in integrations.items() if v]
if active_integrations:
    st.markdown(f"**Comparing:** {current_period} vs {previous_period} | **Active integrations:** {', '.join(active_integrations)}")
else:
    st.markdown(f"**Comparing:** {current_period} vs {previous_period}")

# =============================================================================
# TAB LAYOUT
# =============================================================================

# Build tabs dynamically based on available data
tab_names = [
    "📊 Traffic Overview",
    "🔍 Search Performance", 
    "📄 Content",
    "👥 Audience",
]

# Add optional tabs
if pagespeed.get('available'):
    tab_names.append("⚡ PageSpeed")
if hotjar.get('available'):
    tab_names.append("🔥 Hotjar")
if google_ads.get('available'):
    tab_names.append("💰 Google Ads")

tab_names.append("💡 Insights")

tabs = st.tabs(tab_names)
tab_idx = 0

tab_overview = tabs[tab_idx]; tab_idx += 1
tab_search = tabs[tab_idx]; tab_idx += 1
tab_content = tabs[tab_idx]; tab_idx += 1
tab_audience = tabs[tab_idx]; tab_idx += 1

if pagespeed.get('available'):
    tab_pagespeed = tabs[tab_idx]; tab_idx += 1
if hotjar.get('available'):
    tab_hotjar = tabs[tab_idx]; tab_idx += 1
if google_ads.get('available'):
    tab_google_ads = tabs[tab_idx]; tab_idx += 1

tab_insights = tabs[tab_idx]

# -----------------------------------------------------------------------------
# TRAFFIC OVERVIEW TAB
# -----------------------------------------------------------------------------
with tab_overview:
    st.markdown("### Website Traffic Overview")
    
    traffic = ga4.get('traffic_overview', {})
    traffic_comp = comparison.get('traffic_overview', {})
    
    # Metric cards
    cols = st.columns(4)
    
    metrics = [
        ('Total Users', 'total_users', False),
        ('New Users', 'new_users', False),
        ('Sessions', 'sessions', False),
        ('Pageviews', 'pageviews', False),
    ]
    
    for i, (label, key, inverse) in enumerate(metrics):
        with cols[i]:
            value = traffic.get(key, 0)
            change_data = traffic_comp.get(key, {}).get('change', {})
            delta = change_data.get('formatted', 'N/A')
            
            st.metric(
                label=label,
                value=f"{value:,}",
                delta=delta,
                delta_color="inverse" if inverse else "normal"
            )
    
    # Second row
    cols2 = st.columns(4)
    
    metrics2 = [
        ('Bounce Rate', 'bounce_rate', True, '%'),
        ('Avg Session (sec)', 'avg_session_duration', False, ''),
        ('Pages/Session', 'pages_per_session', False, ''),
        ('Engagement Rate', 'engagement_rate', False, '%'),
    ]
    
    for i, (label, key, inverse, suffix) in enumerate(metrics2):
        with cols2[i]:
            value = traffic.get(key, 0)
            change_data = traffic_comp.get(key, {}).get('change', {})
            delta = change_data.get('formatted', 'N/A')
            
            display_val = f"{value:.1f}{suffix}" if suffix else f"{value:.1f}"
            st.metric(
                label=label,
                value=display_val,
                delta=delta,
                delta_color="inverse" if inverse else "normal"
            )
    
    st.markdown("---")
    
    # Monthly trend chart
    st.markdown("### 📈 Monthly Traffic Trend")
    
    monthly = ga4.get('traffic_by_month', [])
    if monthly:
        df_monthly = pd.DataFrame(monthly) if isinstance(monthly, list) else monthly
        
        if not df_monthly.empty and 'yearMonth' in df_monthly.columns:
            fig = px.line(
                df_monthly,
                x='yearMonth',
                y=['totalUsers', 'newUsers', 'returning_users'],
                markers=True,
                labels={'value': 'Users', 'yearMonth': 'Month', 'variable': 'User Type'}
            )
            fig.update_layout(
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                hovermode='x unified'
            )
            # Custom colors
            fig.update_traces(
                line=dict(width=3),
                selector=dict(name='totalUsers')
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Channel breakdown
    st.markdown("### 📡 Traffic by Channel")
    
    channels = ga4.get('traffic_by_channel', [])
    if channels:
        df_channels = pd.DataFrame(channels) if isinstance(channels, list) else channels
        
        if not df_channels.empty and 'sessionDefaultChannelGroup' in df_channels.columns:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                fig = px.pie(
                    df_channels,
                    values='sessions',
                    names='sessionDefaultChannelGroup',
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(
                    df_channels[['sessionDefaultChannelGroup', 'sessions', 'session_share']].rename(
                        columns={
                            'sessionDefaultChannelGroup': 'Channel',
                            'sessions': 'Sessions',
                            'session_share': '% Share'
                        }
                    ),
                    hide_index=True,
                    use_container_width=True
                )


# -----------------------------------------------------------------------------
# SEARCH PERFORMANCE TAB
# -----------------------------------------------------------------------------
with tab_search:
    st.markdown("### Google Search Console Performance")
    
    gsc_overview = gsc.get('overview', {})
    gsc_comp = comparison.get('gsc', {}).get('overview', {})
    
    # Metrics
    cols = st.columns(4)
    
    with cols[0]:
        clicks = gsc_overview.get('total_clicks', 0)
        clicks_change = gsc_comp.get('total_clicks', {}).get('change', {}).get('formatted', 'N/A')
        st.metric("Total Clicks", f"{clicks:,}", clicks_change)
    
    with cols[1]:
        impressions = gsc_overview.get('total_impressions', 0)
        imp_change = gsc_comp.get('total_impressions', {}).get('change', {}).get('formatted', 'N/A')
        st.metric("Total Impressions", f"{impressions:,}", imp_change)
    
    with cols[2]:
        ctr = gsc_overview.get('avg_ctr', 0)
        st.metric("Average CTR", f"{ctr:.2f}%")
    
    with cols[3]:
        position = gsc_overview.get('avg_position', 0)
        st.metric("Average Position", f"{position:.1f}")
    
    st.markdown("---")
    
    # Top keywords
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔑 Top Keywords by Clicks")
        keywords_clicks = gsc.get('top_keywords_clicks', [])
        if keywords_clicks:
            df_kw = pd.DataFrame(keywords_clicks) if isinstance(keywords_clicks, list) else keywords_clicks
            if not df_kw.empty:
                st.dataframe(
                    df_kw.head(15)[['query', 'clicks', 'impressions', 'ctr', 'position']].rename(
                        columns={
                            'query': 'Keyword',
                            'clicks': 'Clicks',
                            'impressions': 'Impressions',
                            'ctr': 'CTR (%)',
                            'position': 'Position'
                        }
                    ),
                    hide_index=True,
                    use_container_width=True
                )
    
    with col2:
        st.markdown("### 📈 Top Keywords by Impressions")
        keywords_imp = gsc.get('top_keywords_impressions', [])
        if keywords_imp:
            df_kw_imp = pd.DataFrame(keywords_imp) if isinstance(keywords_imp, list) else keywords_imp
            if not df_kw_imp.empty:
                st.dataframe(
                    df_kw_imp.head(15)[['query', 'clicks', 'impressions', 'ctr', 'position']].rename(
                        columns={
                            'query': 'Keyword',
                            'clicks': 'Clicks',
                            'impressions': 'Impressions',
                            'ctr': 'CTR (%)',
                            'position': 'Position'
                        }
                    ),
                    hide_index=True,
                    use_container_width=True
                )
    
    # Keyword opportunities
    st.markdown("---")
    st.markdown("### 🎯 Keyword Opportunities")
    st.caption("High impressions, low CTR - optimize these for quick wins")
    
    opportunities = gsc.get('keyword_opportunities', [])
    if opportunities:
        df_opp = pd.DataFrame(opportunities) if isinstance(opportunities, list) else opportunities
        if not df_opp.empty and 'query' in df_opp.columns:
            st.dataframe(
                df_opp.head(10)[['query', 'impressions', 'clicks', 'ctr', 'position']].rename(
                    columns={
                        'query': 'Keyword',
                        'impressions': 'Impressions',
                        'clicks': 'Clicks',
                        'ctr': 'CTR (%)',
                        'position': 'Position'
                    }
                ),
                hide_index=True,
                use_container_width=True
            )


# -----------------------------------------------------------------------------
# CONTENT TAB
# -----------------------------------------------------------------------------
with tab_content:
    st.markdown("### Top Performing Content")
    
    top_pages = ga4.get('top_pages', [])
    if top_pages:
        df_pages = pd.DataFrame(top_pages) if isinstance(top_pages, list) else top_pages
        
        if not df_pages.empty and 'pageTitle' in df_pages.columns:
            st.dataframe(
                df_pages.head(15)[['pageTitle', 'pagePath', 'screenPageViews', 'pct_of_total', 'bounceRate']].rename(
                    columns={
                        'pageTitle': 'Page Title',
                        'pagePath': 'URL',
                        'screenPageViews': 'Views',
                        'pct_of_total': '% of Total',
                        'bounceRate': 'Bounce Rate (%)'
                    }
                ),
                hide_index=True,
                use_container_width=True
            )
    
    st.markdown("---")
    
    # Landing pages
    st.markdown("### 🚪 Top Landing Pages")
    
    landing = ga4.get('landing_pages', [])
    if landing:
        df_landing = pd.DataFrame(landing) if isinstance(landing, list) else landing
        if not df_landing.empty and 'landingPage' in df_landing.columns:
            st.dataframe(
                df_landing.head(10)[['landingPage', 'sessions', 'pct_of_entries', 'bounceRate']].rename(
                    columns={
                        'landingPage': 'Landing Page',
                        'sessions': 'Sessions',
                        'pct_of_entries': '% of Entries',
                        'bounceRate': 'Bounce Rate (%)'
                    }
                ),
                hide_index=True,
                use_container_width=True
            )


# -----------------------------------------------------------------------------
# AUDIENCE TAB
# -----------------------------------------------------------------------------
with tab_audience:
    st.markdown("### Audience Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📱 Device Breakdown")
        devices = ga4.get('device_breakdown', [])
        if devices:
            df_dev = pd.DataFrame(devices) if isinstance(devices, list) else devices
            if not df_dev.empty and 'deviceCategory' in df_dev.columns:
                fig = px.pie(
                    df_dev,
                    values='totalUsers',
                    names='deviceCategory',
                    hole=0.4,
                    color_discrete_sequence=['#2D5016', '#F4C430', '#888888']
                )
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 🌍 Top Countries")
        geo = ga4.get('geography', [])
        if geo:
            df_geo = pd.DataFrame(geo) if isinstance(geo, list) else geo
            if not df_geo.empty and 'country' in df_geo.columns:
                st.dataframe(
                    df_geo.head(10)[['country', 'totalUsers', 'user_share']].rename(
                        columns={
                            'country': 'Country',
                            'totalUsers': 'Users',
                            'user_share': '% Share'
                        }
                    ),
                    hide_index=True,
                    use_container_width=True
                )
    
    # New vs returning
    st.markdown("---")
    st.markdown("### 🔄 New vs Returning Visitors")
    
    nvr = ga4.get('new_vs_returning', {})
    if nvr:
        col1, col2 = st.columns(2)
        
        new_data = nvr.get('new', {})
        ret_data = nvr.get('returning', {})
        
        with col1:
            st.metric(
                "New Visitors",
                f"{new_data.get('users', 0):,}",
                f"{new_data.get('pct_of_total', 0):.1f}% of total"
            )
        
        with col2:
            st.metric(
                "Returning Visitors",
                f"{ret_data.get('users', 0):,}",
                f"{ret_data.get('pct_of_total', 0):.1f}% of total"
            )


# -----------------------------------------------------------------------------
# PAGESPEED TAB (if available)
# -----------------------------------------------------------------------------
if pagespeed.get('available'):
    with tab_pagespeed:
        st.markdown("### ⚡ PageSpeed Insights")
        st.caption("Site performance analysis from Google PageSpeed Insights")
        
        summary = pagespeed.get('summary', {})
        mobile = pagespeed.get('mobile', {})
        desktop = pagespeed.get('desktop', {})
        
        # Check if we have any data to show
        if not summary and not mobile and not desktop:
            st.warning("PageSpeed analysis completed but returned no data. Try again later.")
        else:
            # Score cards - only show metrics we have
            col1, col2 = st.columns(2)
            
            with col1:
                if 'mobile_score' in summary or mobile:
                    mobile_score = summary.get('mobile_score') or mobile.get('score', 0)
                    mobile_status = summary.get('mobile_status', 'unknown')
                    color = "normal" if mobile_status == "good" else "inverse" if mobile_status == "poor" else "off"
                    st.metric(
                        "📱 Mobile Performance",
                        f"{mobile_score}/100",
                        delta=mobile_status.replace('_', ' ').title() if mobile_status != 'unknown' else None,
                        delta_color=color
                    )
                else:
                    st.info("📱 Mobile analysis unavailable")
            
            with col2:
                if 'desktop_score' in summary or desktop:
                    desktop_score = summary.get('desktop_score') or desktop.get('score', 0)
                    desktop_status = summary.get('desktop_status', 'unknown')
                    color = "normal" if desktop_status == "good" else "inverse" if desktop_status == "poor" else "off"
                    st.metric(
                        "🖥️ Desktop Performance",
                        f"{desktop_score}/100",
                        delta=desktop_status.replace('_', ' ').title() if desktop_status != 'unknown' else None,
                        delta_color=color
                    )
                else:
                    st.info("🖥️ Desktop analysis unavailable")
        
        st.markdown("---")
        
        # Core Web Vitals
        st.markdown("### 📊 Core Web Vitals (Mobile)")
        
        if mobile:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                lcp = mobile.get('lcp', 0)
                lcp_status = "Good" if lcp <= 2.5 else "Needs Improvement" if lcp <= 4 else "Poor"
                st.metric("LCP", f"{lcp:.2f}s", delta=lcp_status, 
                         delta_color="normal" if lcp <= 2.5 else "inverse")
                st.caption("Largest Contentful Paint")
            
            with col2:
                cls = mobile.get('cls', 0)
                cls_status = "Good" if cls <= 0.1 else "Needs Improvement" if cls <= 0.25 else "Poor"
                st.metric("CLS", f"{cls:.3f}", delta=cls_status,
                         delta_color="normal" if cls <= 0.1 else "inverse")
                st.caption("Cumulative Layout Shift")
            
            with col3:
                tbt = mobile.get('tbt', 0)
                tbt_status = "Good" if tbt <= 200 else "Needs Improvement" if tbt <= 600 else "Poor"
                st.metric("TBT", f"{tbt:.0f}ms", delta=tbt_status,
                         delta_color="normal" if tbt <= 200 else "inverse")
                st.caption("Total Blocking Time")
            
            with col4:
                tti = mobile.get('tti', 0)
                st.metric("TTI", f"{tti:.2f}s")
                st.caption("Time to Interactive")
        
        # Opportunities
        st.markdown("---")
        st.markdown("### 🎯 Improvement Opportunities")
        
        opportunities = mobile.get('opportunities', []) if mobile else []
        if opportunities:
            for opp in opportunities[:5]:
                savings = opp.get('savings_ms', 0)
                if savings > 0:
                    st.markdown(f"**{opp.get('title', '')}** - Could save {savings/1000:.1f}s")
        else:
            st.info("No major improvement opportunities identified.")


# -----------------------------------------------------------------------------
# HOTJAR TAB (if available)
# -----------------------------------------------------------------------------
if hotjar.get('available'):
    with tab_hotjar:
        st.markdown("### 🔥 Hotjar User Feedback")
        st.caption("User sentiment and feedback from Hotjar")
        
        hj_summary = hotjar.get('summary', {})
        feedback = hotjar.get('feedback', {})
        surveys = hotjar.get('surveys', {})
        
        # Overview metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Feedback",
                hj_summary.get('total_feedback', 0)
            )
        
        with col2:
            st.metric(
                "Survey Responses",
                hj_summary.get('total_survey_responses', 0)
            )
        
        with col3:
            sentiment = hj_summary.get('sentiment_score', 0)
            st.metric(
                "Sentiment Score",
                f"{sentiment:.0f}",
                delta="Positive" if sentiment > 0 else "Negative" if sentiment < 0 else "Neutral",
                delta_color="normal" if sentiment > 0 else "inverse" if sentiment < 0 else "off"
            )
        
        st.markdown("---")
        
        # Sentiment breakdown
        st.markdown("### 😊 Sentiment Breakdown")
        
        sentiment_data = feedback.get('sentiment_pct', {})
        if sentiment_data:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("😊 Happy", f"{sentiment_data.get('happy', 0):.1f}%")
            with col2:
                st.metric("😐 Neutral", f"{sentiment_data.get('neutral', 0):.1f}%")
            with col3:
                st.metric("😞 Sad", f"{sentiment_data.get('sad', 0):.1f}%")
        
        # Recent feedback
        st.markdown("---")
        st.markdown("### 💬 Recent Feedback")
        
        recent = feedback.get('recent_feedback', [])
        if recent:
            for item in recent[:5]:
                emoji = "😊" if item.get('emotion') == 'happy' else "😞" if item.get('emotion') == 'sad' else "😐"
                st.markdown(f"{emoji} *\"{item.get('message', '')}\"*")
                st.caption(f"Page: {item.get('page', 'N/A')}")
        else:
            st.info("No recent feedback available.")


# -----------------------------------------------------------------------------
# GOOGLE ADS TAB (if available)
# -----------------------------------------------------------------------------
if google_ads.get('available'):
    with tab_google_ads:
        st.markdown("### 💰 Google Ads Performance")
        
        source = google_ads.get('source', 'unknown')
        if source == 'ga4':
            st.caption("Data sourced from GA4 (linked Google Ads account)")
        else:
            st.caption("Data from Google Ads API")
        
        ads_summary = google_ads.get('summary', {})
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Sessions", f"{ads_summary.get('total_sessions', 0):,}")
        
        with col2:
            st.metric("Users", f"{ads_summary.get('total_users', 0):,}")
        
        with col3:
            bounce = ads_summary.get('bounce_rate', 0)
            st.metric("Bounce Rate", f"{bounce:.1f}%")
        
        with col4:
            st.metric("Campaigns", ads_summary.get('campaign_count', 0))
        
        st.markdown("---")
        
        # Campaign breakdown
        st.markdown("### 📊 Campaign Performance")
        
        campaigns = google_ads.get('performance', {}).get('campaigns', [])
        if campaigns:
            df_campaigns = pd.DataFrame(campaigns)
            st.dataframe(df_campaigns, hide_index=True, use_container_width=True)
        else:
            st.info("No campaign data available.")
        
        # Ad Grants note for nonprofits
        st.markdown("---")
        st.info("💡 **Nonprofit Tip:** If you have Google Ad Grants ($10,000/month free ads), "
                "make sure you're utilizing your full budget!")


# -----------------------------------------------------------------------------
# INSIGHTS TAB
# -----------------------------------------------------------------------------
with tab_insights:
    st.markdown("### 💡 Analytics Insights")
    
    # Executive summary
    summary = insights.get('executive_summary', '')
    if summary:
        st.info(f"**Executive Summary:** {summary}")
    
    st.markdown("---")
    
    # Insights by category
    insights_list = insights.get('insights', [])
    
    if insights_list:
        # Group insights
        positive = [i for i in insights_list if i.get('type') == 'positive']
        negative = [i for i in insights_list if i.get('type') == 'negative']
        opportunities = [i for i in insights_list if i.get('type') == 'opportunity']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### ✅ Strengths")
            for insight in positive[:3]:
                st.success(insight.get('headline', ''))
        
        with col2:
            st.markdown("#### ⚠️ Challenges")
            for insight in negative[:3]:
                st.error(insight.get('headline', ''))
        
        with col3:
            st.markdown("#### 🎯 Opportunities")
            for insight in opportunities[:3]:
                st.warning(insight.get('headline', ''))
    
    # Recommendations
    st.markdown("---")
    st.markdown("### 📋 Recommendations")
    
    recommendations = insights.get('key_recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"**{i}.** {rec}")
    
    # Benchmarks
    st.markdown("---")
    st.markdown("### 📊 Benchmark Comparison")
    
    benchmarks = report.get('benchmarks', {})
    bench_summary = benchmarks.get('summary', {})
    
    if bench_summary:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Outperforming",
                bench_summary.get('outperforming_count', 0),
                delta="metrics above benchmark"
            )
        
        with col2:
            st.metric(
                "At Benchmark",
                bench_summary.get('at_benchmark_count', 0),
                delta="metrics at standard"
            )
        
        with col3:
            st.metric(
                "Needs Improvement",
                bench_summary.get('underperforming_count', 0),
                delta="metrics below benchmark",
                delta_color="inverse"
            )


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown(
    f"<center><small>Generated by Nonprofit Analytics Platform | "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M')}</small></center>",
    unsafe_allow_html=True
)

