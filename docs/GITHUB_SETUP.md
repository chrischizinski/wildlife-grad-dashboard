# 🐾 Wildlife Graduate Assistantship Scraper - GitHub Setup Guide

This guide will walk you through setting up the complete automated workflow for the Wildlife Graduate Assistantship Analytics Dashboard.

## 📋 Overview

The system consists of:
- **Automated Scraping**: Weekly job data collection via GitHub Actions
- **Data Processing**: AI-powered classification and analytics generation
- **Dashboard Deployment**: Automatic deployment to GitHub Pages
- **Big 10 Filtering**: University classification and filtering capabilities

---

## 🚀 Quick Setup Steps

### 1. Repository Setup
```bash
# Clone or ensure you're in the repository
git clone https://github.com/chrischizinski/wildlife-grad-dashboard.git
cd wildlife-grad-dashboard

# Verify setup
python scripts/verify_github_setup.py
```

### 2. GitHub Pages Configuration
1. Go to your repository on GitHub
2. Navigate to **Settings** → **Pages**
3. Under **Source**, select **GitHub Actions**
4. Do not select a branch source for this repository
5. Click **Save**

### 3. Test the Workflow
1. Go to **Actions** tab in your GitHub repository
2. Find **Scrape Jobs and Update Supabase**
3. Click **Run workflow** → **Run workflow** (manual trigger)
4. Monitor the workflow execution

### 4. Verify Dashboard Deployment
- Dashboard URL: `https://chrischizinski.github.io/wildlife-grad-dashboard/`
- Should be live within 2-3 minutes after successful workflow

---

## 🤖 Automated Schedule

### Weekly Scraping
- **When**: Every Sunday at 6:00 AM UTC (1:00 AM EST / 12:00 AM CST)
- **What happens**:
  1. Scrapes Texas A&M Wildlife & Fisheries job board
  2. Classifies positions using AI (90%+ accuracy)
  3. Generates Big 10 university classifications
  4. Creates enhanced analytics and trend data
  5. Archives historical data with timestamps
  6. Deploys updated dashboard to GitHub Pages

### Manual Triggers
- Can be triggered manually from GitHub Actions tab
- Useful for testing or updating dashboard immediately
- Also triggers on pushes to main branch (dashboard files only)

---

## 📁 Project Structure

```
wildlife-grad-dashboard/
├── .github/workflows/
│   └── scrape-and-update-dashboard.yml   # Main automation workflow
├── dashboard/
│   ├── analytics_dashboard.html  # Main dashboard interface
│   ├── analytics_dashboard.js    # Dashboard functionality
│   ├── analytics-styles.css      # Dashboard styling
│   └── [data files]              # Generated during workflow
├── data/
│   ├── archive/                  # Historical data backups
│   └── [generated files]         # Current scraping results
├── scripts/
│   ├── verify_github_setup.py   # Setup verification tool
│   ├── enhanced_analysis.py     # Analytics generation
│   └── enhanced_dashboard_data.py # Dashboard data prep
├── wildlife_job_scraper.py      # Main scraping script
├── requirements.txt              # Python dependencies
└── GITHUB_SETUP.md              # This guide
```

---

## 🔧 Technical Details

### Python Dependencies
- **Selenium**: Web scraping automation
- **BeautifulSoup4**: HTML parsing
- **Pydantic**: Data validation and modeling
- **Pandas**: Data manipulation and analysis

### GitHub Actions Features
- **Chrome Browser**: Automated with ChromeDriver
- **Data Archiving**: Timestamped backups in `data/archive/`
- **Error Handling**: Comprehensive logging and failure reporting
- **Permissions**: Minimal required permissions for security

### Dashboard Features
- **Big 10 Filter**: Toggle to show only Big 10 university positions
- **Real-time Analytics**: Trend analysis, geographic distribution
- **Mobile Responsive**: Works on all device sizes
- **Export Options**: JSON, CSV data download

---

## 🛠️ Troubleshooting

### Common Issues

**1. Workflow fails on first run**
```bash
# Check Python dependencies
pip install -r requirements.txt

# Verify all files are committed
git add .
git commit -m "Complete setup"
git push origin main
```

**2. Dashboard not updating**
- Check GitHub Pages is enabled in repository settings
- Ensure Pages source is set to **GitHub Actions** (not branch deploy)
- Look for errors in the Actions tab

**3. Scraper finds no data**
- This is normal if the job board has no new graduate positions
- The workflow will still complete successfully
- Check archive folder for historical data

**4. Big 10 filter not working**
- Ensure `analytics_dashboard.js` has Big 10 filtering code
- Check browser console for JavaScript errors
- Verify data includes `is_big10_university` fields

### Verification Commands
```bash
# Check setup
python scripts/verify_github_setup.py

# Test scraper locally
python wildlife_job_scraper.py

# Check git status
git status
git remote -v
```

---

## 📊 Expected Output

### Successful Workflow Run
1. **Data Files Created**:
   - `data/graduate_assistantships.json`
   - `data/verified_graduate_assistantships.json`
   - `data/enhanced_data.json`

2. **Dashboard Updated**:
   - Latest job analytics
   - Big 10 university filtering
   - Trend analysis and charts

3. **Archive Created**:
   - `data/archive/jobs_YYYYMMDD_HHMMSS.json`
   - Historical data preservation

### Dashboard Features
- **Overview**: Total positions, Big 10 count, trend metrics
- **Analytics**: Discipline breakdown, salary analysis
- **Geographic**: Regional distribution with filtering
- **Export**: Data download in multiple formats

---

## 🔐 Security & Privacy

### Data Protection
- **No Personal Info**: Only job titles, organizations, locations
- **Public Data**: Sources from publicly available job boards
- **No Authentication**: Dashboard is read-only, no login required

### GitHub Permissions
- **Contents: Write**: For committing scraped data
- **Pages: Write**: For deploying dashboard
- **Actions**: For workflow automation

---

## 🎯 Success Indicators

✅ **Setup Complete When**:
- Verification script passes all checks
- GitHub Pages shows dashboard URL
- Manual workflow run completes successfully
- Dashboard loads with current data

✅ **Working Correctly When**:
- Weekly runs complete automatically
- Dashboard updates with new data
- Big 10 filter toggle works
- Export functions download data

---

## 📞 Support & Maintenance

### Regular Maintenance
- **Monthly**: Check workflow logs for any failures
- **Quarterly**: Review scraped data quality
- **Annually**: Update Python dependencies

### Monitoring
- **GitHub Actions**: Check for failed workflow runs
- **Dashboard**: Verify data freshness (last updated date)
- **Archive**: Ensure historical data is being saved

---

## 🏆 Final Notes

This setup provides a **fully automated, production-ready** system for monitoring wildlife graduate assistantship opportunities. The dashboard provides valuable insights for students, researchers, and career advisors in the wildlife and fisheries field.

**Dashboard URL**: https://chrischizinski.github.io/wildlife-grad-dashboard/

For questions or issues, check the GitHub repository issues or workflow logs for detailed information.

---

*Last updated: June 2025 | Version: 2.0*
