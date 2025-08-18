-- Update geographic_distribution view to show US regions instead of individual states
CREATE OR REPLACE VIEW geographic_distribution AS
SELECT
    CASE
        -- Northeast Region
        WHEN location ~* ',\s*(ME|NH|VT|MA|RI|CT|NY|NJ|PA)\s*$' THEN 'Northeast US'

        -- Southeast Region
        WHEN location ~* ',\s*(DE|MD|DC|VA|WV|KY|TN|NC|SC|GA|FL|AL|MS|AR|LA)\s*$' THEN 'Southeast US'

        -- Midwest Region
        WHEN location ~* ',\s*(OH|MI|IN|WI|IL|MN|IA|MO|ND|SD|NE|KS)\s*$' THEN 'Midwest US'

        -- Southwest Region
        WHEN location ~* ',\s*(TX|OK|NM|AZ)\s*$' THEN 'Southwest US'

        -- West Region
        WHEN location ~* ',\s*(MT|WY|CO|UT|ID|WA|OR|NV|CA|AK|HI)\s*$' THEN 'West US'

        -- US territories
        WHEN location ~* ',\s*(PR|VI|GU|AS|MP)\s*$' THEN 'US Territories'

        -- International - specific countries we might see
        WHEN location ~* 'Canada|Canadian' THEN 'Canada'
        WHEN location ~* 'Mexico|Mexican' THEN 'Mexico'
        WHEN location ~* 'Australia|Australian' THEN 'Australia'
        WHEN location ~* 'New Zealand' THEN 'New Zealand'
        WHEN location ~* 'United Kingdom|UK|England|Scotland|Wales|Ireland' THEN 'United Kingdom'
        WHEN location ~* 'Germany|German' THEN 'Germany'
        WHEN location ~* 'France|French' THEN 'France'
        WHEN location ~* 'South Africa|African' THEN 'South Africa'
        WHEN location ~* 'Brazil|Brazilian' THEN 'Brazil'
        WHEN location ~* 'Japan|Japanese' THEN 'Japan'
        WHEN location ~* 'China|Chinese' THEN 'China'
        WHEN location ~* 'India|Indian' THEN 'India'

        -- Generic international fallback for anything that doesn't match US state pattern
        WHEN location IS NOT NULL AND location != ''
             AND NOT location ~* ',\s*[A-Z]{2}\s*$'  -- Doesn't end with US state abbreviation
             THEN 'International'

        ELSE 'Unknown'
    END as region,
    COUNT(*) as graduate_positions
FROM jobs
WHERE location IS NOT NULL AND location != '' AND is_graduate_position = true
GROUP BY region
HAVING COUNT(*) > 0  -- Only show regions with positions
ORDER BY graduate_positions DESC;
