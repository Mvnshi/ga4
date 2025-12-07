# 🐝 Nonprofit Analytics Platform

A professional-grade analytics reporting tool designed for consultants serving nonprofit organizations. Automatically pulls data from Google Analytics 4 and Google Search Console, generates insights, and produces executive-ready reports.

## ✨ Features

### Data Collection
- **Google Analytics 4 Integration**
  - Traffic overview (users, sessions, pageviews)
  - User acquisition channels
  - Engagement metrics (bounce rate, session duration)
  - Top content performance
  - Device and geographic breakdowns
  - Campaign performance
  - Paid search metrics

- **Google Search Console Integration**
  - Search clicks and impressions
  - Top keywords by clicks, impressions, and CTR
  - Keyword opportunity finder
  - Branded vs non-branded analysis
  - Search appearance data
  - Device and country breakdowns

### Analysis & Insights
- **Automatic Insight Generation**: AI-powered analysis that identifies strengths, challenges, and opportunities
- **Benchmark Comparisons**: Compare against nonprofit industry benchmarks
- **Trend Analysis**: Detect significant changes and anomalies
- **YoY/QoQ Comparisons**: Compare current quarter to previous periods

### Export Formats
- **Excel Reports**: Multi-sheet workbooks with professional formatting
- **PowerPoint Presentations**: McKinsey-style slide decks ready for clients
- **JSON Data**: Raw data for custom processing
- **Interactive Dashboard**: Streamlit web dashboard

### Multi-Client Support
- Configure multiple clients with YAML files
- Separate credentials and branding per client
- Cached API responses to minimize redundant calls

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud project with enabled APIs
- Service account with access to GA4 and Search Console

### Installation

```bash
# Clone or navigate to the project
cd C:\Users\pl0g\Desktop\ga4

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Setup Google APIs

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing

2. **Enable APIs**
   - Enable "Google Analytics Data API"
   - Enable "Google Search Console API"

3. **Create Service Account**
   - Go to IAM & Admin → Service Accounts
   - Create new service account
   - Download JSON key file
   - Save to `credentials/` folder

4. **Grant Access**
   - **GA4**: Admin → Property Access Management → Add the service account email with Viewer role
   - **Search Console**: Settings → Users → Add the service account email

### Configure Your First Client

```bash
# Interactive setup
python main.py setup my_nonprofit

# Or manually create config/clients/my_nonprofit.yaml
```

Example client configuration:

```yaml
name: "bee_conservancy"
display_name: "The Bee Conservancy"
ga4_property_id: "123456789"
gsc_site_url: "https://thebeeconservancy.org/"
credentials_file: "bee_conservancy_credentials.json"

primary_color: "#F4C430"
secondary_color: "#2D5016"
timezone: "America/New_York"

homepage_paths:
  - "/"
  - "/home"

exclude_paths:
  - "/admin"
  - "/wp-admin"
```

---

## 📊 Usage

### Command Line Interface

```bash
# Generate Q4 2024 report
python main.py generate Q4 2024 --client bee_conservancy

# Generate with specific export format
python main.py generate Q4 2024 -c bee_conservancy --export excel

# Generate with quarter-over-quarter comparison
python main.py generate Q1 2025 -c bee_conservancy --comparison qoq

# Export all formats
python main.py generate Q4 2024 -c bee_conservancy --export all

# List configured clients
python main.py list-clients

# Test API connections
python main.py test-connection --client bee_conservancy

# Clear cached data
python main.py clear-cache
```

### Interactive Dashboard

```bash
streamlit run dashboard.py
```

The dashboard provides:
- Interactive report generation
- Visual charts and graphs
- Real-time data exploration
- One-click export to Excel/PowerPoint

---

## 📁 Project Structure

```
ga4/
├── main.py                 # CLI entry point
├── dashboard.py            # Streamlit dashboard
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── config/
│   ├── __init__.py
│   ├── settings.py        # Global settings
│   └── clients/           # Client configurations
│       └── example_client.yaml
│
├── credentials/           # Service account JSON files
│   └── .gitkeep
│
├── src/
│   ├── __init__.py
│   │
│   ├── clients/           # API clients
│   │   ├── ga4_client.py      # Google Analytics 4
│   │   └── gsc_client.py      # Search Console
│   │
│   ├── analysis/          # Analysis engines
│   │   ├── insights_engine.py  # Auto-insights
│   │   ├── benchmarks.py       # Industry benchmarks
│   │   └── trends.py           # Trend detection
│   │
│   ├── reports/           # Report generators
│   │   ├── report_generator.py # Main orchestrator
│   │   ├── excel_exporter.py   # Excel output
│   │   └── powerpoint_exporter.py # PPTX output
│   │
│   └── utils/             # Utilities
│       ├── dates.py           # Date handling
│       ├── formatting.py      # Number formatting
│       └── cache.py           # API caching
│
└── output/                # Generated reports
    └── .gitkeep
```

---

## 📈 Report Contents

### Traffic Overview
- Total users, new users, returning users
- Sessions and pageviews
- Bounce rate and engagement rate
- Average session duration
- Pages per session

### Search Performance
- Total clicks and impressions
- Average CTR and position
- Top keywords by clicks
- Top keywords by impressions
- High-potential keyword opportunities
- Branded vs non-branded breakdown

### Content Performance
- Top pages by pageviews
- Landing page analysis
- Homepage engagement metrics
- Content engagement (time on page, bounce rate)

### Audience Insights
- Device breakdown (mobile, desktop, tablet)
- Geographic distribution
- New vs returning visitors
- User engagement patterns

### Acquisition Channels
- Traffic by channel (organic, direct, referral, social, paid)
- Source/medium breakdown
- Paid search performance
- Campaign performance

### Auto-Generated Insights
- Strengths (positive findings)
- Challenges (areas needing attention)
- Opportunities (quick wins)
- Executive summary
- Actionable recommendations

---

## 🎨 Customization

### Branding
Each client can have custom branding in their YAML config:

```yaml
primary_color: "#2D5016"    # Used in headers, charts
secondary_color: "#F4C430"  # Accent color
logo_path: "path/to/logo.png"  # Optional logo
```

### Benchmarks
Modify industry benchmarks in `config/settings.py`:

```python
benchmarks: dict = field(default_factory=lambda: {
    "bounce_rate": 55.0,
    "avg_session_duration": 120.0,
    "pages_per_session": 2.5,
    # Add or modify benchmarks
})
```

### Insight Thresholds
Adjust sensitivity for insight detection:

```python
significant_change_threshold: float = 10.0  # % change to flag
anomaly_threshold: float = 25.0  # % change for anomaly alert
```

---

## 🔧 API Reference

### ReportGenerator

```python
from config.settings import get_settings
from src.reports.report_generator import ReportGenerator

# Load client config
settings = get_settings()
client_config = settings.load_client("bee_conservancy")

# Initialize generator
generator = ReportGenerator(client_config)

# Generate report
report = generator.generate(
    quarter="Q4",
    year=2024,
    comparison_type="yoy"  # or "qoq"
)

# Export
generator.export_excel(report)
generator.export_powerpoint(report)
report.save_json()

# Or export all
paths = generator.export_all(report)
```

### GA4Client

```python
from src.clients.ga4_client import GA4Client

ga4 = GA4Client(client_config)

# Get all metrics for a period
traffic = ga4.get_traffic_overview("2024-01-01", "2024-03-31")
top_pages = ga4.get_top_pages("2024-01-01", "2024-03-31")
channels = ga4.get_traffic_by_channel("2024-01-01", "2024-03-31")
```

### SearchConsoleClient

```python
from src.clients.gsc_client import SearchConsoleClient

gsc = SearchConsoleClient(client_config)

# Get search data
keywords = gsc.get_top_keywords_by_clicks("2024-01-01", "2024-03-31")
opportunities = gsc.get_keyword_opportunities("2024-01-01", "2024-03-31")
```

---

## 🔒 Security Notes

- **Never commit credentials**: The `credentials/` folder is gitignored
- **Service accounts**: Use service accounts, not personal OAuth
- **Minimal permissions**: Grant only Viewer/Read access
- **Rotate keys**: Periodically rotate service account keys

---

## 🐛 Troubleshooting

### "Client config not found"
- Ensure YAML file exists in `config/clients/`
- Check filename matches the client name parameter

### "API quota exceeded"
- Clear cache: `python main.py clear-cache`
- Wait and retry (quotas reset daily)
- Cached data reduces redundant API calls

### "Permission denied"
- Verify service account has access to GA4 property
- Verify service account has access to Search Console site
- Check credentials file path is correct

### "No data returned"
- Verify date range has data in GA4/GSC
- Check property ID and site URL are correct
- Try `python main.py test-connection --client your_client`

---

## 📝 License

MIT License - Feel free to use for commercial consulting work.

---

## 🙋 Support

For issues or feature requests, please check:
1. Configuration is correct
2. API access is properly set up
3. Date ranges contain data

---

Built with ❤️ for nonprofit consultants

