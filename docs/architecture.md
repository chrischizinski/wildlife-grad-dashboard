## Project Architecture

### Core Components
1. **Scraper** (`wildlife_job_scraper.py`)
   - Selenium WebDriver with Chrome
   - Anti-detection measures
   - Rate limiting and human-like behavior
   - Robust pagination handling

2. **Data Pipeline** (`scripts/generate_dashboard_data.py`)
   - Data analysis and categorization
   - Trend analysis over time
   - Export preparation for dashboard

3. **Dashboard** (`dashboard/`)
   - Interactive visualizations with Chart.js
   - Real-time filtering capabilities
   - Responsive design
   - Download functionality

4. **Automation** (`.github/workflows/`)
   - Weekly scheduled scraping (`scrape-and-update-supabase.yml`)
   - Automatic dashboard updates
   - Data archiving with timestamps

### Data Flow
```
Website → Scraper → JSON/CSV → Analysis → Dashboard → GitHub Pages
                                    ↓
                               Data Archive
```

## Technical Specifications

### Dependencies
- Python 3.11+
- Selenium WebDriver
- BeautifulSoup4
- Pandas for data analysis
- Pydantic for validation
- Chrome browser + ChromeDriver

### Output Formats
- **JSON**: `data/graduate_assistantships.json`
- **CSV**: `data/graduate_assistantships.csv`
- **Dashboard Data**: `dashboard/data.json`
- **Archives**: `data/archive/jobs_YYYY-MM-DD.*`

### Data Fields
- Title, Organization, Location
- Salary, Starting Date, Published Date
- Tags, Education Requirements
- Application Deadlines
