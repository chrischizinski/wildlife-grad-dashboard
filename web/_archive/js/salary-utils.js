/**
 * Wildlife Dashboard - Salary Utilities
 * Cost of living adjustments and salary analysis functions
 */

window.WildlifeDashboard = window.WildlifeDashboard || {};

(function(WD) {
    'use strict';

    // Regional Cost of Living Index (baseline: Midwest US = 1.0)
    const REGION_COL_INDEX = {
        'Northeast US': 1.12,
        'West US': 1.10,
        'Southwest US': 0.98,
        'Southeast US': 0.94,
        'Midwest US': 1.00,
        'US Territories': 1.05,
        'International': 1.00,
        'Unknown': 1.00
    };

    // State abbreviation to full name mapping
    const STATE_ABBREV_MAP = {
        al: 'alabama', ak: 'alaska', az: 'arizona', ar: 'arkansas',
        ca: 'california', co: 'colorado', ct: 'connecticut',
        dc: 'district of columbia', de: 'delaware', fl: 'florida',
        ga: 'georgia', hi: 'hawaii', id: 'idaho', il: 'illinois',
        in: 'indiana', ia: 'iowa', ks: 'kansas', ky: 'kentucky',
        la: 'louisiana', me: 'maine', md: 'maryland', ma: 'massachusetts',
        mi: 'michigan', mn: 'minnesota', ms: 'mississippi', mo: 'missouri',
        mt: 'montana', ne: 'nebraska', nv: 'nevada', nh: 'new hampshire',
        nj: 'new jersey', nm: 'new mexico', ny: 'new york state',
        nc: 'north carolina', nd: 'north dakota', oh: 'ohio',
        ok: 'oklahoma', or: 'oregon', pa: 'pennsylvania', ri: 'rhode island',
        sc: 'south carolina', sd: 'south dakota', tn: 'tennessee',
        tx: 'texas', ut: 'utah', vt: 'vermont', va: 'virginia',
        wa: 'washington', wv: 'west virginia', wi: 'wisconsin', wy: 'wyoming'
    };

    // Fine-grained COL index (loaded at runtime)
    let COL_INDEX = null;

    /**
     * Load Cost of Living index data
     * @returns {Promise<object|null>} COL index data
     */
    WD.loadColIndex = async function() {
        if (COL_INDEX) return COL_INDEX;
        try {
            const resp = await fetch('assets/data/col_index.json');
            if (!resp.ok) throw new Error('not found');
            COL_INDEX = await resp.json();
        } catch (e) {
            COL_INDEX = null;
        }
        return COL_INDEX;
    };

    /**
     * Map position to US region
     * @param {object} pos - Position object
     * @returns {string} Region name
     */
    WD.mapPositionToRegion = function(pos) {
        try {
            const raw = pos.location || pos.state_or_country || pos.country || '';
            if (typeof mapLocationToRegion !== 'function') return 'Unknown';

            // Try the full string first
            let region = mapLocationToRegion(raw);
            if (region && region !== 'Unknown' && region !== 'International') return region;

            // Try tokens split by commas, parentheses, hyphens
            const tokens = String(raw).split(/[(),]|\s-\s|\/|\|/).map(t => t.trim()).filter(Boolean);
            for (const t of tokens.reverse()) {
                region = mapLocationToRegion(t);
                if (region && region !== 'Unknown' && region !== 'International') return region;
            }
            return region || 'Unknown';
        } catch (_) {}
        return 'Unknown';
    };

    /**
     * Get Cost of Living index for a position
     * @param {object} pos - Position object
     * @returns {number} COL index
     */
    WD.getCOLIndexForPosition = function(pos) {
        // State-level only: ignore city-level entries for consistency
        if (COL_INDEX) {
            const raw = (pos.location || pos.state_or_country || pos.country || '').toString().toLowerCase();
            if (raw) {
                const paren = (raw.match(/\(([^)]*)\)/) || ['', ''])[1];
                const hay = (paren ? paren + ' ' : '') + raw;

                // State full-name match
                for (const [state, idx] of Object.entries(COL_INDEX.states || {})) {
                    if (state.length > 3 && hay.includes(state)) return idx;
                }

                // Abbreviation heuristic (last two-letter token)
                const m = hay.match(/\b([a-z]{2})\b(?!.*\b[a-z]{2}\b)/);
                if (m) {
                    const ab = m[1];
                    const stateName = STATE_ABBREV_MAP[ab];
                    if (stateName && COL_INDEX.states[stateName]) {
                        return COL_INDEX.states[stateName];
                    }
                }
            }
        }
        const region = WD.mapPositionToRegion(pos);
        return REGION_COL_INDEX[region] || 1.0;
    };

    /**
     * Get annual salary (raw, unadjusted)
     * @param {object} pos - Position object
     * @returns {number} Annual salary
     */
    WD.getAnnualSalaryRaw = function(pos) {
        // Prefer numeric salary field
        if (typeof pos.salary === 'number' && pos.salary > 0) return pos.salary;

        // Parse from text fields
        if (typeof pos.salary === 'string') {
            const v = WD.parseSalaryFromText(pos.salary);
            if (v > 0) return v;
        }
        if (typeof pos.salary_range === 'string') {
            const v = WD.parseSalaryFromText(pos.salary_range);
            if (v > 0) return v;
        }
        if (typeof pos.description === 'string') {
            const v = WD.parseSalaryFromText(pos.description);
            if (v > 0) return v;
        }
        return 0;
    };

    /**
     * Get annual salary with optional Lincoln, NE adjustment
     * @param {object} pos - Position object
     * @param {boolean} adjusted - Whether to apply COL adjustment
     * @returns {number} Salary value
     */
    WD.getAnnualSalaryAdjusted = function(pos, adjusted) {
        // If dataset already provides Lincoln adjusted, prefer it when adjusted is true
        if (adjusted && typeof pos.salary_lincoln_adjusted === 'number' && pos.salary_lincoln_adjusted > 0) {
            return pos.salary_lincoln_adjusted;
        }
        const base = WD.getAnnualSalaryRaw(pos);
        if (!base) return 0;
        if (!adjusted) return base;
        const idx = WD.getCOLIndexForPosition(pos) || 1.0;
        return Math.round(base / idx);
    };

    /**
     * Calculate salary statistics for a group of positions
     * @param {object[]} positions - Array of position objects
     * @param {boolean} adjusted - Whether to use COL adjustment
     * @returns {object} Salary statistics
     */
    WD.calculateSalaryStats = function(positions, adjusted = true) {
        const salaries = positions
            .map(p => WD.getAnnualSalaryAdjusted(p, adjusted))
            .filter(s => s > 0);

        if (salaries.length === 0) {
            return { count: 0, mean: 0, median: 0, min: 0, max: 0 };
        }

        const sorted = [...salaries].sort((a, b) => a - b);
        const sum = salaries.reduce((a, b) => a + b, 0);
        const mean = sum / salaries.length;
        const median = sorted.length % 2 === 0
            ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
            : sorted[Math.floor(sorted.length / 2)];

        return {
            count: salaries.length,
            mean: Math.round(mean),
            median: Math.round(median),
            min: sorted[0],
            max: sorted[sorted.length - 1]
        };
    };

    WD.dlog && WD.dlog('Salary utilities loaded');

})(window.WildlifeDashboard);
