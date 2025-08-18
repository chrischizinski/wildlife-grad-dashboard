/**
 * Geographic region mapping utilities
 * Maps US states to regions and handles international locations
 */

// US State to Region mapping (both abbreviations and full names)
const US_REGIONS = {
    // Northeast - abbreviations
    'ME': 'Northeast US', 'NH': 'Northeast US', 'VT': 'Northeast US', 'MA': 'Northeast US',
    'RI': 'Northeast US', 'CT': 'Northeast US', 'NY': 'Northeast US', 'NJ': 'Northeast US', 'PA': 'Northeast US',

    // Southeast - abbreviations
    'DE': 'Southeast US', 'MD': 'Southeast US', 'DC': 'Southeast US', 'VA': 'Southeast US',
    'WV': 'Southeast US', 'KY': 'Southeast US', 'TN': 'Southeast US', 'NC': 'Southeast US',
    'SC': 'Southeast US', 'GA': 'Southeast US', 'FL': 'Southeast US', 'AL': 'Southeast US',
    'MS': 'Southeast US', 'AR': 'Southeast US', 'LA': 'Southeast US',

    // Midwest - abbreviations
    'OH': 'Midwest US', 'MI': 'Midwest US', 'IN': 'Midwest US', 'WI': 'Midwest US',
    'IL': 'Midwest US', 'MN': 'Midwest US', 'IA': 'Midwest US', 'MO': 'Midwest US',
    'ND': 'Midwest US', 'SD': 'Midwest US', 'NE': 'Midwest US', 'KS': 'Midwest US',

    // Southwest - abbreviations
    'TX': 'Southwest US', 'OK': 'Southwest US', 'NM': 'Southwest US', 'AZ': 'Southwest US',

    // West - abbreviations
    'MT': 'West US', 'WY': 'West US', 'CO': 'West US', 'UT': 'West US', 'ID': 'West US',
    'WA': 'West US', 'OR': 'West US', 'NV': 'West US', 'CA': 'West US', 'AK': 'West US', 'HI': 'West US',

    // US Territories - abbreviations
    'PR': 'US Territories', 'VI': 'US Territories', 'GU': 'US Territories',
    'AS': 'US Territories', 'MP': 'US Territories',

    // Northeast - full names (case insensitive keys)
    'maine': 'Northeast US', 'new hampshire': 'Northeast US', 'vermont': 'Northeast US', 'massachusetts': 'Northeast US',
    'rhode island': 'Northeast US', 'connecticut': 'Northeast US', 'new york': 'Northeast US', 'new jersey': 'Northeast US', 'pennsylvania': 'Northeast US',

    // Southeast - full names
    'delaware': 'Southeast US', 'maryland': 'Southeast US', 'virginia': 'Southeast US',
    'west virginia': 'Southeast US', 'kentucky': 'Southeast US', 'tennessee': 'Southeast US', 'north carolina': 'Southeast US',
    'south carolina': 'Southeast US', 'georgia': 'Southeast US', 'florida': 'Southeast US', 'alabama': 'Southeast US',
    'mississippi': 'Southeast US', 'arkansas': 'Southeast US', 'louisiana': 'Southeast US',

    // Midwest - full names
    'ohio': 'Midwest US', 'michigan': 'Midwest US', 'indiana': 'Midwest US', 'wisconsin': 'Midwest US',
    'illinois': 'Midwest US', 'minnesota': 'Midwest US', 'iowa': 'Midwest US', 'missouri': 'Midwest US',
    'north dakota': 'Midwest US', 'south dakota': 'Midwest US', 'nebraska': 'Midwest US', 'kansas': 'Midwest US',

    // Southwest - full names
    'texas': 'Southwest US', 'oklahoma': 'Southwest US', 'new mexico': 'Southwest US', 'arizona': 'Southwest US',

    // West - full names
    'montana': 'West US', 'wyoming': 'West US', 'colorado': 'West US', 'utah': 'West US', 'idaho': 'West US',
    'washington': 'West US', 'oregon': 'West US', 'nevada': 'West US', 'california': 'West US', 'alaska': 'West US', 'hawaii': 'West US'
};

// International location patterns
const INTERNATIONAL_PATTERNS = {
    'Canada': /Canada|Canadian/i,
    'Mexico': /Mexico|Mexican/i,
    'Australia': /Australia|Australian/i,
    'New Zealand': /New Zealand/i,
    'United Kingdom': /United Kingdom|UK|England|Scotland|Wales|Ireland/i,
    'Germany': /Germany|German/i,
    'France': /France|French/i,
    'South Africa': /South Africa|African/i,
    'Brazil': /Brazil|Brazilian/i,
    'Japan': /Japan|Japanese/i,
    'China': /China|Chinese/i,
    'India': /India|Indian/i
};

/**
 * Map a location string to a region
 * @param {string} location - The location string (e.g., "Austin, TX" or "Toronto, Canada")
 * @returns {string} - The region name
 */
function mapLocationToRegion(location) {
    console.log(`Mapping location: "${location}"`);

    if (!location || location.trim() === '') {
        console.log('  → Unknown (empty location)');
        return 'Unknown';
    }

    const locationLower = location.toLowerCase().trim();

    // First, check if it's a direct state name match (case-insensitive)
    if (US_REGIONS[locationLower]) {
        const region = US_REGIONS[locationLower];
        console.log(`  → ${region} (direct state name match: ${location})`);
        return region;
    }

    // Check for US state abbreviation in various patterns
    let stateMatch = location.match(/,\s*([A-Z]{2})\s*$/);  // City, ST
    if (!stateMatch) {
        stateMatch = location.match(/\b([A-Z]{2})\b(?!.*[A-Z]{2})/);  // Any 2-letter code (last one)
    }

    if (stateMatch) {
        const stateCode = stateMatch[1];
        const region = US_REGIONS[stateCode] || 'Unknown';
        console.log(`  → ${region} (US state abbreviation: ${stateCode})`);
        return region;
    }

    // Check international patterns - but return "International" for all
    for (const [country, pattern] of Object.entries(INTERNATIONAL_PATTERNS)) {
        if (pattern.test(location)) {
            console.log(`  → International (${country} pattern match)`);
            return 'International';
        }
    }

    // If it doesn't match US state pattern and isn't a known country, assume international
    console.log(`  → International (no US state pattern match)`);
    return 'International';

    console.log('  → Unknown (fallback)');
    return 'Unknown';
}

/**
 * Group geographic data by regions
 * @param {Array} geographicData - Array of {state_or_country, graduate_positions}
 * @returns {Object} - Grouped data by region
 */
function groupGeographicDataByRegions(geographicData) {
    const regionSummary = {};

    geographicData.forEach(item => {
        const location = item.state_or_country || item.region;
        const region = mapLocationToRegion(location);
        const positions = item.graduate_positions || 0;

        if (regionSummary[region]) {
            regionSummary[region] += positions;
        } else {
            regionSummary[region] = positions;
        }
    });

    return regionSummary;
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        mapLocationToRegion,
        groupGeographicDataByRegions,
        US_REGIONS,
        INTERNATIONAL_PATTERNS
    };
}
