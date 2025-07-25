-- Wildlife Graduate Positions Database Schema for Supabase
-- This schema supports the wildlife graduate assistantships dashboard

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types for better data consistency
CREATE TYPE position_type AS ENUM ('Graduate', 'Undergraduate', 'Professional', 'Unknown');
CREATE TYPE scraper_version AS ENUM ('1.0', '2.0', '3.0');

-- Main jobs table
CREATE TABLE jobs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title TEXT NOT NULL,
    organization TEXT,
    location TEXT,
    salary TEXT,
    starting_date TEXT,
    published_date DATE,
    tags TEXT,
    url TEXT UNIQUE,
    description TEXT,
    requirements TEXT,
    project_details TEXT,
    contact_info TEXT,
    application_deadline TEXT,
    
    -- Graduate position classification
    is_graduate_position BOOLEAN DEFAULT FALSE,
    grad_confidence DECIMAL(3,2) CHECK (grad_confidence >= 0 AND grad_confidence <= 1),
    position_type position_type DEFAULT 'Unknown',
    
    -- Discipline classification
    discipline TEXT,
    discipline_confidence DECIMAL(3,2) CHECK (discipline_confidence >= 0 AND discipline_confidence <= 1),
    discipline_keywords TEXT[], -- Array of keywords
    
    -- University information
    is_big10_university BOOLEAN DEFAULT FALSE,
    university_name TEXT,
    
    -- Metadata
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scrape_run_id TEXT,
    scraper_version TEXT DEFAULT '2.0',
    
    -- Indexing and constraints
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_jobs_published_date ON jobs (published_date DESC);
CREATE INDEX idx_jobs_discipline ON jobs (discipline);
CREATE INDEX idx_jobs_is_graduate ON jobs (is_graduate_position);
CREATE INDEX idx_jobs_location ON jobs USING gin(to_tsvector('english', location));
CREATE INDEX idx_jobs_scraped_at ON jobs (scraped_at DESC);
CREATE INDEX idx_jobs_scrape_run_id ON jobs (scrape_run_id);

-- Full text search index
CREATE INDEX idx_jobs_search ON jobs USING gin(
    to_tsvector('english', 
        COALESCE(title, '') || ' ' || 
        COALESCE(description, '') || ' ' || 
        COALESCE(organization, '') || ' ' ||
        COALESCE(discipline, '')
    )
);

-- Analytics view for dashboard performance
CREATE OR REPLACE VIEW job_analytics AS
SELECT 
    COUNT(*) as total_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true) as graduate_positions,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as positions_with_salary,
    COUNT(DISTINCT discipline) FILTER (WHERE discipline IS NOT NULL) as unique_disciplines,
    COUNT(DISTINCT EXTRACT(YEAR FROM published_date) || '-' || LPAD(EXTRACT(MONTH FROM published_date)::text, 2, '0')) as months_with_data,
    MIN(published_date) as earliest_posting,
    MAX(published_date) as latest_posting,
    MAX(updated_at) as last_updated
FROM jobs;

-- Monthly trends view
CREATE OR REPLACE VIEW monthly_trends AS
SELECT 
    EXTRACT(YEAR FROM published_date) as year,
    EXTRACT(MONTH FROM published_date) as month,
    TO_CHAR(published_date, 'YYYY-MM') as month_key,
    COUNT(*) as total_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true) as graduate_positions,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as positions_with_salary
FROM jobs 
WHERE published_date IS NOT NULL
GROUP BY year, month, month_key
ORDER BY year DESC, month DESC;

-- Discipline breakdown view
CREATE OR REPLACE VIEW discipline_analytics AS
SELECT 
    discipline,
    COUNT(*) as total_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true) as grad_positions,
    AVG(grad_confidence) as avg_grad_confidence,
    AVG(discipline_confidence) as avg_discipline_confidence,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as positions_with_salary,
    array_agg(DISTINCT unnest(discipline_keywords)) FILTER (WHERE discipline_keywords IS NOT NULL) as all_keywords
FROM jobs 
WHERE discipline IS NOT NULL AND discipline != 'Unknown'
GROUP BY discipline
ORDER BY grad_positions DESC, total_positions DESC;

-- Geographic distribution view
CREATE OR REPLACE VIEW geographic_distribution AS
SELECT 
    CASE 
        WHEN location ~* ',\s*([A-Z]{2})\s*$' THEN 
            regexp_replace(location, '^.*,\s*([A-Z]{2})\s*$', '\1')
        WHEN location ~* ',\s*([A-Za-z\s]+)\s*$' THEN 
            trim(regexp_replace(location, '^.*,\s*([A-Za-z\s]+)\s*$', '\1'))
        ELSE 'Unknown'
    END as state_or_country,
    COUNT(*) as total_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true) as graduate_positions
FROM jobs 
WHERE location IS NOT NULL AND location != ''
GROUP BY state_or_country
ORDER BY graduate_positions DESC, total_positions DESC;

-- Enable Row Level Security (optional, for future multi-user support)
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations for now (adjust based on your needs)
CREATE POLICY "Allow all operations on jobs" ON jobs
    FOR ALL USING (true);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_jobs_updated_at 
    BEFORE UPDATE ON jobs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data structure comment
/*
Sample insert:
INSERT INTO jobs (
    title, organization, location, salary, published_date,
    is_graduate_position, grad_confidence, discipline, discipline_confidence,
    url, description
) VALUES (
    'PhD Student Position in Wildlife Ecology',
    'University of Example',
    'Example City, ST',
    '$25,000 - $30,000',
    '2024-01-15',
    true,
    0.95,
    'Wildlife Management and Conservation',
    0.85,
    'https://example.com/job/123',
    'Research position in wildlife ecology...'
);
*/