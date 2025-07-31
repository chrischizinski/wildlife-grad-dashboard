# Supabase Setup Guide for Wildlife Graduate Assistantships Dashboard

This guide explains how to migrate your wildlife graduate assistantships dashboard from static JSON files to a dynamic Supabase database.

## Why Supabase?

- **Scalable**: No file size limits, handles growing datasets
- **Real-time**: Automatic updates and real-time data
- **Free tier**: 500MB database, 1GB file storage, unlimited API requests
- **GitHub Pages compatible**: Works with static site hosting
- **Future-proof**: Easy to add authentication, real-time subscriptions, etc.

## Setup Steps

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project
3. Choose a name and password for your database
4. Wait for the project to be ready (1-2 minutes)

### 2. Set Up Database Schema

1. In your Supabase dashboard, go to the SQL Editor
2. Copy and paste the contents of `database/supabase_schema.sql`
3. Run the SQL to create tables and views

### 3. Configure Credentials

1. In Supabase dashboard, go to Settings > API
2. Copy your Project URL and anon/public key
3. Update `dashboard/assets/js/supabase-config.js`:

```javascript
const SUPABASE_CONFIG = {
    url: 'https://your-actual-project-id.supabase.co',
    anonKey: 'your-actual-anon-key-here'
};
```

### 4. Populate Database

1. Install required Python packages:
```bash
pip install supabase python-dotenv
```

2. Create a `.env` file in your project root:
```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

3. Run the population script:
```bash
python3 scripts/populate_supabase.py
```

## Current Status

The dashboard is already set up to work with both Supabase and JSON files:

- **Without Supabase**: Falls back to JSON files (current behavior)
- **With Supabase**: Automatically uses database for better performance

## Benefits After Migration

### Performance
- **Faster loading**: Database queries vs large JSON files
- **Efficient filtering**: Server-side filtering and aggregation
- **Real-time updates**: No need to regenerate static files

### Scalability
- **No file size limits**: Database can handle millions of records
- **Automatic indexing**: Fast searches and filtering
- **Optimized views**: Pre-calculated analytics for dashboard

### Maintenance
- **Automated updates**: Scripts can update database directly
- **Version control**: Database migrations track schema changes
- **Backup**: Automatic database backups

## Database Schema

### Main Tables
- `jobs`: All job postings with full details
- Analytics views for dashboard performance:
  - `job_analytics`: Overall statistics
  - `monthly_trends`: Time series data
  - `discipline_analytics`: Breakdown by discipline
  - `geographic_distribution`: Location analysis

### Key Features
- **Full-text search**: Indexed search across all job content
- **Efficient filtering**: Indexed on common filter fields
- **Data integrity**: Constraints and validation
- **Performance views**: Pre-calculated analytics

## Migration Timeline

### Phase 1: Setup (Current)
- ✅ Database schema created
- ✅ Population script ready
- ✅ Dashboard supports both sources
- ✅ Documentation complete

### Phase 2: Data Population
- Create Supabase project
- Configure credentials
- Run population script
- Verify data integrity

### Phase 3: Go Live
- Update dashboard configuration
- Test all functionality
- Monitor performance
- Update data pipeline

## Ongoing Data Updates

### Option 1: Scheduled Updates
Update your scraping pipeline to write directly to Supabase:

```python
from supabase import create_client

supabase = create_client(url, key)
supabase.table('jobs').insert(new_jobs).execute()
```

### Option 2: Batch Updates
Continue using JSON files and sync periodically:

```bash
python3 scripts/populate_supabase.py
```

### Option 3: Real-time Pipeline
Set up webhooks or triggers for automatic updates.

## Deployment Options

### GitHub Pages (Current)
- Static hosting with Supabase API calls
- Free and easy to maintain
- Limited to client-side processing

### Netlify (Recommended Upgrade)
- Better build tools and environment variables
- Serverless functions for data processing
- More generous bandwidth limits

### Vercel
- Excellent performance and global CDN
- API routes for custom endpoints
- Great for React/Next.js if you upgrade

## Cost Analysis

### Free Tiers Comparison
| Service | GitHub Pages | Netlify | Vercel | Supabase |
|---------|--------------|---------|---------|----------|
| Bandwidth | 100GB/month | 100GB/month | 100GB/month | Unlimited |
| Build time | N/A | 300 min/month | 6000 min/month | N/A |
| Database | None | None | None | 500MB |
| Functions | None | 125k/month | 12 per day | 2M/month |

**Total cost: $0/month** for typical usage

## Support

If you need help with the setup:

1. Check the console logs in your browser
2. Verify your Supabase credentials
3. Ensure the database schema is properly created
4. Test the population script with a small dataset first

## Next Steps

Once Supabase is set up, you can enhance the dashboard with:

- **Real-time updates**: Live data without page refresh
- **Advanced filtering**: Complex search and filter options
- **User accounts**: Save searches and favorites
- **API endpoints**: Expose data for other applications
- **Admin interface**: Content management for job postings
