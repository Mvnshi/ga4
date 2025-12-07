# 🚀 Quick Start Guide

Get your first report in 10 minutes!

## Step 1: Install Dependencies

```powershell
cd C:\Users\pl0g\Desktop\ga4
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Set Up Google APIs

### Create Service Account (5 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Go to **APIs & Services** → **Enable APIs**
   - Enable: `Google Analytics Data API`
   - Enable: `Search Console API`
4. Go to **IAM & Admin** → **Service Accounts**
   - Click **Create Service Account**
   - Name it (e.g., "analytics-reports")
   - Click **Create and Continue**
   - Skip role assignment
   - Click **Done**
5. Click on the new service account
6. Go to **Keys** → **Add Key** → **Create new key** → **JSON**
7. Download the JSON file

### Save Credentials

Save the JSON file to:
```
C:\Users\pl0g\Desktop\ga4\credentials\bee_conservancy_credentials.json
```

### Grant Access

**For GA4:**
1. Go to [Google Analytics](https://analytics.google.com)
2. Admin → Property → Property Access Management
3. Add the service account email (from the JSON file) with **Viewer** role

**For Search Console:**
1. Go to [Search Console](https://search.google.com/search-console)
2. Settings → Users and permissions
3. Add user → Paste service account email → **Full** permission

## Step 3: Configure Client

Edit `config/clients/bee_conservancy.yaml`:

```yaml
name: "bee_conservancy"
display_name: "The Bee Conservancy"
ga4_property_id: "123456789"  # ← Your GA4 Property ID
gsc_site_url: "https://thebeeconservancy.org/"  # ← Your site URL
credentials_file: "bee_conservancy_credentials.json"
```

**Find your GA4 Property ID:**
- GA4 → Admin → Property Settings → Copy the Property ID (just the number)

## Step 4: Test Connection

```powershell
python main.py test-connection --client bee_conservancy
```

You should see:
```
Testing GA4 connection... ✓ Connected
Testing Search Console connection... ✓ Connected
```

## Step 5: Generate Your First Report!

```powershell
# Generate Q4 2024 report with all exports
python main.py generate Q4 2024 --client bee_conservancy --export all
```

Or use the dashboard:
```powershell
streamlit run dashboard.py
```

## 🎉 Done!

Your reports are saved in the `output/` folder:
- `bee_conservancy_quarterly_report_Q4_2024.xlsx` - Excel data
- `bee_conservancy_quarterly_presentation_Q4_2024.pptx` - PowerPoint slides
- `bee_conservancy_report_Q4_2024.json` - Raw data

---

## Adding More Clients

```powershell
# Interactive setup
python main.py setup another_nonprofit

# Then edit the generated YAML file with their details
```

## Common Commands

```powershell
# List all clients
python main.py list-clients

# Generate with YoY comparison (default)
python main.py generate Q1 2025 -c bee_conservancy

# Generate with QoQ comparison
python main.py generate Q1 2025 -c bee_conservancy --comparison qoq

# Export only Excel
python main.py generate Q4 2024 -c bee_conservancy --export excel

# Export only PowerPoint
python main.py generate Q4 2024 -c bee_conservancy --export powerpoint

# Clear cache if needed
python main.py clear-cache
```

## Optional Integrations

The tool supports these optional integrations (all work without them!):

### PageSpeed Insights (Free - Enabled by Default)
No setup needed! Just generates site performance data automatically.

### Hotjar (If you have a subscription)
Add to your client YAML:
```yaml
integrations:
  hotjar_enabled: true
  hotjar_site_id: "YOUR_SITE_ID"
  hotjar_api_token: "YOUR_API_TOKEN"
```

### Google Ads (For nonprofits with Ad Grants)
Even without full API setup, can pull Ads data from GA4 if accounts are linked:
```yaml
integrations:
  google_ads_use_ga4_fallback: true  # This is enabled by default!
```

---

## Troubleshooting

**"Permission denied" errors:**
- Double-check the service account email was added to GA4 and Search Console

**"No data" or empty reports:**
- Verify the GA4 Property ID is correct (just the number, no "properties/" prefix)
- Verify the GSC site URL matches exactly how it appears in Search Console

**"Module not found" errors:**
- Make sure virtual environment is activated: `.\venv\Scripts\activate`
- Reinstall: `pip install -r requirements.txt`

**"Hotjar not configured" warning:**
- This is fine! Hotjar is optional. The report still generates without it.

**"PageSpeed failed" warning:**
- Usually a network issue. Report still generates with other data.

