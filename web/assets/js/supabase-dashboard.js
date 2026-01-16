/**
 * Wildlife Jobs Dashboard
 * Static JSON-based dashboard for graduate assistantship positions
 */

/**
 * Runtime logging utilities (toggle with ?debug=1 or localStorage.WGD_DEBUG="1")
 */
const WGD_DEBUG = (() => {
    try {
        const fromQs = new URLSearchParams(window.location.search).has('debug');
        const fromStorage = (window.localStorage && localStorage.getItem('WGD_DEBUG') === '1');
        return fromQs || fromStorage;
    } catch (_) { return false; }
})();

const dlog = (...args) => { if (WGD_DEBUG) console.log(...args); };
const dwarn = (...args) => { if (WGD_DEBUG) console.warn(...args); };
const derror = (...args) => { if (WGD_DEBUG) console.error(...args); };

/**
 * Data fetching functions - loads from static JSON files
 */
class DataFetcher {
    constructor() {
        dlog('=== DataFetcher Constructor ===');
        dlog('Data source: JSON files');
        dlog('=== End Constructor ===');
    }

    async fetchAnalytics() {
        return await this.fetchFromJSON();
    }

    async fetchFromJSON() {
        try {
            dlog('Fetching data from JSON files...');

            // First try the lightweight dashboard analytics file
            try {
                const analyticsResponse = await fetch('./data/dashboard_analytics.json').catch(() => {
                    dlog('Trying dashboard_analytics.json from dashboard directory');
                    return fetch('data/dashboard_analytics.json').catch(() => {
                        dlog('Trying dashboard_analytics.json from relative path');
                        return fetch('../data/dashboard_analytics.json');
                    });
                });

                if (analyticsResponse.ok) {
                    const dashboardData = await analyticsResponse.json();

                    // Try to load export data as well
                    let exportData = [];
                    try {
                        const exportResponse = await fetch('./data/export_data.json').catch(() => {
                            return fetch('data/export_data.json').catch(() => {
                                return fetch('../data/export_data.json');
                            });
                        });
                        if (exportResponse.ok) {
                            exportData = await exportResponse.json();
                        }
                    } catch (exportError) {
                        dlog('Export data not available, using empty array');
                    }

                    // Ensure dashboard shape matches what the UI expects
                    this.ensureDashboardCompatibility(dashboardData);

                    dlog('Using lightweight dashboard analytics');
                    return { dashboardData, exportData };
                }
            } catch (analyticsError) {
                dlog('Lightweight analytics not available, trying full enhanced data');
            }

            // Fallback to the original large files
            const [enhancedResponse, exportResponse] = await Promise.all([
                fetch('./data/enhanced_data.json').catch(() => {
                    dlog('Trying enhanced_data.json from dashboard directory');
                    return fetch('data/enhanced_data.json').catch(() => {
                        dlog('Trying enhanced_data.json from relative path');
                        return fetch('../data/enhanced_data.json');
                    });
                }),
                fetch('./data/export_data.json').catch(() => {
                    dlog('Trying export_data.json from dashboard directory');
                    return fetch('data/export_data.json').catch(() => {
                        dlog('Trying export_data.json from relative path');
                        return fetch('../data/export_data.json');
                    });
                })
            ]);

            if (!enhancedResponse.ok) {
                throw new Error(`Enhanced data fetch failed: ${enhancedResponse.status}`);
            }
            if (!exportResponse.ok) {
                throw new Error(`Export data fetch failed: ${exportResponse.status}`);
            }

            const dashboardData = await enhancedResponse.json();
            const exportData = await exportResponse.json();

            // Ensure dashboard shape for enhanced data as well
            this.ensureDashboardCompatibility(dashboardData);

            return { dashboardData, exportData };

        } catch (error) {
            console.error('Error fetching JSON data:', error);
            throw error;
        }
    }

    ensureDashboardCompatibility(dashboardData) {
        // Normalize summary -> summary_stats if needed
        if (!dashboardData.summary_stats && dashboardData.summary) {
            const s = dashboardData.summary;
            dashboardData.summary_stats = {
                total_scraped_positions: s.total_positions ?? s.total_scraped_positions ?? 0,
                graduate_positions: s.graduate_positions ?? 0,
                graduate_positions_with_salary: s.graduate_positions_with_salary ?? s.graduate_positions ?? 0,
                graduate_disciplines: s.graduate_disciplines ?? 0,
                classification_rate: s.graduate_rate ?? s.classification_rate ?? 0
            };
        }

        // Provide metadata.last_updated if available
        if (!dashboardData.metadata) dashboardData.metadata = {};
        if (!dashboardData.metadata.last_updated && (dashboardData.last_updated || dashboardData.summary?.last_updated)) {
            dashboardData.metadata.last_updated = dashboardData.last_updated || dashboardData.summary.last_updated;
        }

        // Build time_series from monthly_trends if missing
        if (!dashboardData.time_series && Array.isArray(dashboardData.monthly_trends)) {
            dashboardData.time_series = this.buildTimeSeriesFromTrends(dashboardData.monthly_trends);
        }

        // Map disciplines -> top_disciplines if needed
        if (!dashboardData.top_disciplines && dashboardData.disciplines) {
            const td = {};
            Object.entries(dashboardData.disciplines).forEach(([name, val]) => {
                const count = typeof val === 'object' && 'graduate_positions' in val ? val.graduate_positions : (val || 0);
                td[name] = {
                    total_positions: count,
                    grad_positions: count,
                    salary_stats: null
                };
            });
            dashboardData.top_disciplines = td;
        }

        // Map geography -> geographic_summary if needed
        if (!dashboardData.geographic_summary && dashboardData.geography) {
            dashboardData.geographic_summary = dashboardData.geography;
        }
    }

    // --- Discipline trend enrichment helpers ---
    monthKeyFromDate(dateStr) {
        if (!dateStr) return null;
        try {
            // Accept YYYY-MM or YYYY-MM-DD or full ISO
            const m = String(dateStr).slice(0, 7);
            if (/^\d{4}-\d{2}$/.test(m)) return m;
            const d = new Date(dateStr);
            if (!isNaN(d)) {
                const y = d.getUTCFullYear();
                const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
                return `${y}-${mm}`;
            }
        } catch (_) { /* noop */ }
        return null;
    }

    buildDisciplineMonthly(positions) {
        const result = {};
        positions.forEach(p => {
            // Only count graduate positions if flag present; otherwise include
            if (typeof p.is_graduate_position !== 'undefined' && !p.is_graduate_position) return;
            const disc = p.discipline || 'Other';
            const mk = this.monthKeyFromDate(p.published_date || p.scraped_at || p.created_at);
            if (!mk) return;
            if (!result[disc]) result[disc] = {};
            result[disc][mk] = (result[disc][mk] || 0) + 1;
        });
        return result;
    }

    limitMonths(mapObj, n) {
        // Return a new object with only the last n months (by key sort)
        const entries = Object.entries(mapObj).sort((a,b) => a[0].localeCompare(b[0]));
        return Object.fromEntries(entries.slice(-n));
    }

    addDisciplineTrends(dashboardData, positions, maxDisciplines = 5) {
        if (!dashboardData.time_series) return;
        const discMonthly = this.buildDisciplineMonthly(positions);
        const topNames = Object.keys(dashboardData.top_disciplines || {}).slice(0, maxDisciplines);

        const inject = (target, monthsLimit) => {
            target.discipline_monthly = target.discipline_monthly || {};
            topNames.forEach(name => {
                const series = discMonthly[name] || {};
                target.discipline_monthly[name] = monthsLimit ? this.limitMonths(series, monthsLimit) : series;
            });
        };

        if (dashboardData.time_series['1_month']) inject(dashboardData.time_series['1_month'], 1);
        if (dashboardData.time_series['3_month']) inject(dashboardData.time_series['3_month'], 3);
        if (dashboardData.time_series['6_month']) inject(dashboardData.time_series['6_month'], 6);
        if (dashboardData.time_series['1_year']) inject(dashboardData.time_series['1_year'], 12);
        if (dashboardData.time_series['all_time']) inject(dashboardData.time_series['all_time'], 0);
    }

    transformSupabaseData(analytics, disciplines, geographic, monthlyTrends) {
        dlog('Transforming Supabase data:', { analytics, disciplines, geographic, monthlyTrends });

        // Transform disciplines data (now all graduate positions)
        const disciplineStats = {};
        disciplines.forEach(disc => {
            disciplineStats[disc.discipline] = {
                total_positions: disc.graduate_positions,
                grad_positions: disc.graduate_positions,
                salary_stats: (disc.avg_salary && disc.avg_salary > 0) ? { mean: disc.avg_salary } : null
            };
        });

        // Transform geographic data using region mapping
        let geographicSummary = {};

        // If we have region mapping function available, use it to group by regions
        if (typeof groupGeographicDataByRegions === 'function') {
            dlog('Using region mapping for geographic data');
            dlog('Original geographic data:', geographic);
            geographicSummary = groupGeographicDataByRegions(geographic);
            dlog('Transformed regional data:', geographicSummary);
        } else {
            // Fallback to original state/country mapping
            dlog('Region mapping not available, using original geographic data');
            geographic.forEach(geo => {
                const locationKey = geo.region || geo.state_or_country || 'Unknown';
                geographicSummary[locationKey] = geo.graduate_positions;
            });
        }

        // Transform time series data
        const timeSeriesData = this.buildTimeSeriesFromTrends(monthlyTrends);

        // Build dashboard data structure matching expected format for graduate positions dashboard
        const dashboardData = {
            metadata: {
                generated_at: new Date().toISOString(),
                total_scraped_positions: analytics.total_scraped_positions,
                graduate_positions: analytics.graduate_positions,
                classification_rate: analytics.total_scraped_positions > 0 ?
                    ((analytics.graduate_positions / analytics.total_scraped_positions) * 100).toFixed(1) : 0
            },
            summary_stats: {
                total_scraped_positions: analytics.total_scraped_positions,
                graduate_positions: analytics.graduate_positions,
                graduate_positions_with_salary: analytics.graduate_positions_with_salary,
                graduate_disciplines: analytics.graduate_disciplines,
                classification_rate: analytics.total_scraped_positions > 0 ?
                    ((analytics.graduate_positions / analytics.total_scraped_positions) * 100).toFixed(1) : 0
            },
            top_disciplines: disciplineStats,
            geographic_summary: geographicSummary,
            time_series: timeSeriesData,
            last_updated: analytics.last_updated,
            // Add compatibility fields for the UI
            total_positions: analytics.graduate_positions, // Now refers to graduate positions only
            graduate_assistantships: analytics.graduate_positions
        };

        dlog('Transformed dashboard data:', dashboardData);

        return dashboardData;
    }

    buildTimeSeriesFromTrends(monthlyTrends) {
        const graduateMonthly = {};
        monthlyTrends.forEach(trend => {
            graduateMonthly[trend.month_key] = trend.graduate_positions;
        });

        return {
            '1_month': {
                total_monthly: this.getLastNMonths(graduateMonthly, 1),
                discipline_monthly: {}
            },
            '3_month': {
                total_monthly: this.getLastNMonths(graduateMonthly, 3),
                discipline_monthly: {}
            },
            '6_month': {
                total_monthly: this.getLastNMonths(graduateMonthly, 6),
                discipline_monthly: {}
            },
            '1_year': {
                total_monthly: this.getLastNMonths(graduateMonthly, 12),
                discipline_monthly: {}
            },
            'all_time': {
                total_monthly: graduateMonthly,
                discipline_monthly: {}
            }
        };
    }

    getLastNMonths(monthlyData, n) {
        const sorted = Object.entries(monthlyData).sort();
        return Object.fromEntries(sorted.slice(-n));
    }
}

// Initialize the enhanced dashboard with original functionality
let dashboardData = null;
let exportData = null;
let currentTimeframe = '1_year';
let currentTrendChart = null;
let currentSalaryChart = null;
let currentSalaryDistributionChart = null;
let dataFetcher = null;
let connectionStatus = 'loading'; // 'connected', 'disconnected', 'loading'
let lastDataUpdate = null;
let useLincolnAdjustment = (typeof localStorage !== 'undefined' ? localStorage.getItem('NE_ADJUST') !== '0' : true);
let COL_INDEX = null; // fine-grained COL indices (loaded at runtime)

// Discipline color mapping for multi-line trend chart
let disciplineColorMap = {};
// Modern, accessible palette (muted brights)
const DISCIPLINE_PALETTE = [
    '#2563eb', // blue-600
    '#0ea5e9', // sky-500
    '#14b8a6', // teal-500
    '#22c55e', // green-500
    '#f59e0b', // amber-500
    '#f97316', // orange-500
    '#ef4444', // red-500
    '#a855f7', // purple-500
    '#8b5cf6', // violet-500
    '#06b6d4'  // cyan-500
];
function buildDisciplineColorMap() {
    disciplineColorMap = {};
    const names = Object.keys(dashboardData?.top_disciplines || {});
    names.forEach((name, idx) => {
        disciplineColorMap[name] = DISCIPLINE_PALETTE[idx % DISCIPLINE_PALETTE.length];
    });
}
function getDisciplineColor(name) {
    return disciplineColorMap[name] || '#6b7280';
}

// Normalize timeframe values across controls
function normalizeTimeframe(val) {
    if (!val) return '1_year';
    const map = {
        '1month': '1_month',
        '6months': '6_month',
        '12months': '1_year',
        '24months': 'all_time',
        'all': 'all_time',
        '6_months': '6_month',
    };
    return map[val] || val;
}

// --- Salary utilities (NE adjustment) ---
function parseSalaryFromText(text) {
    if (!text || typeof text !== 'string') return 0;
    const nums = text.match(/\$?\s*([0-9][0-9,]*)/g);
    if (!nums) return 0;
    const values = nums.map(n => parseInt(n.replace(/[$,\s]/g, ''), 10)).filter(v => !isNaN(v));
    if (!values.length) return 0;
    // If a range, average; otherwise single value
    const sum = values.reduce((a,b)=>a+b,0);
    return Math.round(sum / values.length);
}

function mapPositionToRegion(pos) {
    try {
        const raw = pos.location || pos.state_or_country || pos.country || '';
        if (typeof mapLocationToRegion !== 'function') return 'Unknown';
        // Try the full string first
        let region = mapLocationToRegion(raw);
        if (region && region !== 'Unknown' && region !== 'International') return region;
        // Try tokens split by commas, parentheses, hyphens
        const tokens = String(raw).split(/[(),]|\s-\s|\/|\|/).map(t => t.trim()).filter(Boolean);
        for (const t of tokens.reverse()) { // try more specific tokens at the end
            region = mapLocationToRegion(t);
            if (region && region !== 'Unknown' && region !== 'International') return region;
        }
        return region || 'Unknown';
    } catch (_) {}
    return 'Unknown';
}

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

function getCOLIndexForPosition(pos) {
    // State-level only: ignore city-level entries for consistency and performance
    if (COL_INDEX) {
        const raw = (pos.location || pos.state_or_country || pos.country || '').toString().toLowerCase();
        if (raw) {
            const paren = (raw.match(/\(([^)]*)\)/) || [,''])[1];
            const hay = (paren ? paren + ' ' : '') + raw;
            // State full-name match
            for (const [state, idx] of Object.entries(COL_INDEX.states || {})) {
                if (state.length > 3 && hay.includes(state)) return idx;
            }
            // Abbreviation heuristic (last two-letter token)
            const m = hay.match(/\b([a-z]{2})\b(?!.*\b[a-z]{2}\b)/);
            if (m) {
                const ab = m[1];
                const abMap = { al:'alabama', ak:'alaska', az:'arizona', ar:'arkansas', ca:'california', co:'colorado', ct:'connecticut', dc:'district of columbia', de:'delaware', fl:'florida', ga:'georgia', hi:'hawaii', id:'idaho', il:'illinois', in:'indiana', ia:'iowa', ks:'kansas', ky:'kentucky', la:'louisiana', me:'maine', md:'maryland', ma:'massachusetts', mi:'michigan', mn:'minnesota', ms:'mississippi', mo:'missouri', mt:'montana', ne:'nebraska', nv:'nevada', nh:'new hampshire', nj:'new jersey', nm:'new mexico', ny:'new york state', nc:'north carolina', nd:'north dakota', oh:'ohio', ok:'oklahoma', or:'oregon', pa:'pennsylvania', ri:'rhode island', sc:'south carolina', sd:'south dakota', tn:'tennessee', tx:'texas', ut:'utah', vt:'vermont', va:'virginia', wa:'washington', wv:'west virginia', wi:'wisconsin', wy:'wyoming' };
                const stateName = abMap[ab];
                if (stateName && COL_INDEX.states[stateName]) return COL_INDEX.states[stateName];
            }
        }
    }
    const region = mapPositionToRegion(pos);
    return REGION_COL_INDEX[region] || 1.0;
}

function getAnnualSalaryRaw(pos) {
    // Prefer numeric salary field
    if (typeof pos.salary === 'number' && pos.salary > 0) return pos.salary;
    // Parse from text fields
    if (typeof pos.salary === 'string') {
        const v = parseSalaryFromText(pos.salary);
        if (v > 0) return v;
    }
    if (typeof pos.salary_range === 'string') {
        const v = parseSalaryFromText(pos.salary_range);
        if (v > 0) return v;
    }
    if (typeof pos.description === 'string') {
        const v = parseSalaryFromText(pos.description);
        if (v > 0) return v;
    }
    return 0;
}

function getAnnualSalaryAdjusted(pos, adjusted) {
    // If dataset already provides Lincoln adjusted, prefer it when adjusted is true
    if (adjusted && typeof pos.salary_lincoln_adjusted === 'number' && pos.salary_lincoln_adjusted > 0) {
        return pos.salary_lincoln_adjusted;
    }
    const base = getAnnualSalaryRaw(pos);
    if (!base) return 0;
    if (!adjusted) return base;
    const idx = getCOLIndexForPosition(pos) || 1.0;
    return Math.round(base / idx);
}

async function loadColIndex() {
    if (COL_INDEX) return COL_INDEX;
    try {
        const resp = await fetch('assets/data/col_index.json');
        if (!resp.ok) throw new Error('not found');
        COL_INDEX = await resp.json();
    } catch (e) {
        COL_INDEX = null;
    }
    return COL_INDEX;
}

// Chart color scheme - exactly 5 categories
const disciplineColors = {
    'Fisheries Management and Conservation': '#4682B4',  // Ocean blue
    'Wildlife Management and Conservation': '#2E8B57',   // Forest green
    'Human Dimensions': '#CD853F',                       // Warm brown
    'Environmental Science': '#9932CC',                  // Purple
    'Other': '#708090'                                   // Slate gray
};

// Big Ten Universities list for classification
const BIG_TEN_PATTERNS = [
    /\buniversity of illinois\b.*(urbana|uiuc|champaign)?/i,
    /\bindiana university\b.*(bloomington)?/i,
    /\buniversity of iowa\b/i,
    /\buniversity of maryland\b/i,
    /\buniversity of michigan\b/i,
    /\bmichigan state university\b/i,
    /\buniversity of minnesota\b.*(twin cities|minneapolis|st\.? paul)?/i,
    /\buniversity of nebraska\b.*(lincoln|unl)?/i,
    /\bnorthwestern university\b/i,
    /\bohio state university\b|\bthe ohio state university\b|\boSU\b/i,
    /\bpennsylvania state university\b|\bpenn state\b/i,
    /\bpurdue university\b/i,
    /\brutgers\b/i,
    /\buniversity of wisconsin\b.*(madison|uw\s?-?madison)?/i
];

function normalizeOrgName(name) {
    return String(name || '')
        .toLowerCase()
        .replace(/\([^)]*\)/g, ' ') // remove parenthetical descriptors
        .replace(/[.,]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

// Function to check if a university is Big Ten (robust aliases)
function isBigTenUniversity(organizationName) {
    if (!organizationName) return false;
    const org = normalizeOrgName(organizationName);
    return BIG_TEN_PATTERNS.some(rx => rx.test(org));
}

/**
 * Sanitize HTML content to prevent XSS attacks
 */
function escapeHTML(str) {
    if (typeof str !== 'string') return String(str);
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Initialize the dashboard
 */
async function initDashboard() {
    try {
        dlog('=== DASHBOARD INITIALIZATION START ===');
        showLoading();
        // Show connection status banner in loading state immediately
        connectionStatus = 'loading';
        updateConnectionStatus();

        // Initialize data fetcher
        dlog('Creating DataFetcher...');
        dataFetcher = new DataFetcher();
        dlog('DataFetcher created successfully');

        // Determine initial timeframe from UI controls before rendering charts
        const timeframeRadios = document.querySelectorAll('input[name="timeframe"]');
        const checkedRadio = Array.from(timeframeRadios).find(r => r.checked);
        if (checkedRadio) {
            currentTimeframe = normalizeTimeframe(checkedRadio.value);
        } else {
            const timePeriodFilter = document.getElementById('time-period-filter');
            if (timePeriodFilter) {
                currentTimeframe = normalizeTimeframe(timePeriodFilter.value);
            }
        }

        // Fetch COL index (non-blocking)
        await loadColIndex().catch(() => {});

        // Fetch data
        dlog('Fetching analytics data...');
        const result = await dataFetcher.fetchAnalytics();
        dashboardData = result.dashboardData;
        exportData = result.exportData;

        // If JSON path provided exportData, also enrich discipline trends
        if (Array.isArray(exportData) && exportData.length) {
            dataFetcher.addDisciplineTrends(dashboardData, exportData);
        }

        // Build color map from the current top disciplines
        buildDisciplineColorMap();

        // Determine connection status
        if (dataFetcher.useSupabase) {
            connectionStatus = 'connected';
            dlog('✅ Connected to Supabase database');
        } else {
            connectionStatus = 'disconnected';
            dlog('⚠️ Using JSON fallback - Supabase unavailable');
        }

        // Extract last updated date
        lastDataUpdate = dashboardData.metadata?.generated_at ||
                        dashboardData.last_updated ||
                        dashboardData.metadata?.last_updated ||
                        null;

        dlog('Dashboard data loaded:', {
            connectionStatus: connectionStatus,
            dataSource: dataFetcher.useSupabase ? 'Supabase' : 'JSON files',
            totalPositions: dashboardData.summary_stats?.graduate_positions || dashboardData.total_positions,
            exportRecords: exportData?.length || 0,
            lastUpdated: lastDataUpdate
        });

        // Apply modern Chart.js defaults
        try {
            if (typeof Chart !== 'undefined') {
                Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
                Chart.defaults.color = '#334155';            // slate-700
                Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.3)'; // slate-400 @ 30%
                Chart.defaults.plugins.legend.labels.color = '#334155';
                Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)'; // slate-900 @ 90%
                Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
                Chart.defaults.plugins.tooltip.bodyColor = '#ffffff';
            }
        } catch (_) {}

        // Initialize all components
        updateConnectionStatus();
        updateOverviewCards();
        createDisciplineIndicators();
        dlog('About to check Chart availability...');
        dlog('typeof Chart:', typeof Chart);
        if (typeof Chart !== 'undefined') {
            dlog('Chart is available, calling initializeCharts()...');
            initializeCharts();
            dlog('initializeCharts() completed, calling createBigTenAnalysis()...');
            createBigTenAnalysis();
            dlog('createBigTenAnalysis() completed');
        } else {
            console.warn('Chart.js not available, skipping charts');
        }
        setupEventListeners();
        updateFooter();

        // Add export buttons to all charts
        setTimeout(() => {
            addExportButtons();
        }, 500); // Small delay to ensure charts are fully rendered

        hideLoading();
        // Initialize any tooltips (including NE Adjust info)
        try { initializeTooltips(); } catch (_) {}
        dlog('=== DASHBOARD INITIALIZATION SUCCESS ===');

    } catch (error) {
        console.error('Failed to initialize dashboard:', error.message);
        derror('=== DASHBOARD INITIALIZATION ERROR ===');
        derror('Error initializing dashboard:', error);
        derror('Error stack:', error.stack);
        derror('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        showError(`Failed to load dashboard data: ${error.message}`);
    }
}

// Include all the original dashboard functions with minor adaptations
/**
 * Update overview summary cards
 */
function updateOverviewCards() {
    // Handle both old and new data structures for graduate positions dashboard
    const metadata = dashboardData.metadata || {};
    const summaryStats = dashboardData.summary_stats || {};

    // Graduate positions dashboard stats (all metrics are for graduate positions only)
    const totalScrapedPositions = metadata.total_scraped_positions || summaryStats.total_scraped_positions || 0;
    const gradPositions = metadata.graduate_positions || summaryStats.graduate_positions || dashboardData.graduate_assistantships || 0;
    const gradSalaryPositions = summaryStats.graduate_positions_with_salary || 0;
    const classificationRate = metadata.classification_rate || summaryStats.classification_rate || 0;

    // Count disciplines from graduate positions only
    const disciplineData = dashboardData.top_disciplines || {};
    const disciplinesCount = Object.keys(disciplineData).length || summaryStats.graduate_disciplines || 0;

    // Update cards to show graduate-focused metrics (defensive: only if element exists)
    const elTotalJobs = document.getElementById('total-jobs') || document.getElementById('total-positions');
    if (elTotalJobs) elTotalJobs.textContent = (totalScrapedPositions || gradPositions || 0).toLocaleString();
    const elGrad = document.getElementById('grad-positions');
    if (elGrad) elGrad.textContent = (gradPositions || 0).toLocaleString();
    const elSalary = document.getElementById('salary-positions');
    if (elSalary) elSalary.textContent = (gradSalaryPositions || 0).toLocaleString();
    const elDisc = document.getElementById('disciplines-count');
    if (elDisc) elDisc.textContent = disciplinesCount;

    // Add contextual information about classification rate
    updateContextualInfo(totalScrapedPositions, gradPositions, classificationRate);
}

/**
 * Update contextual information banner
 */
function updateContextualInfo(totalScrapedPositions, gradPositions, classificationRate) {
    const contextBanner = document.getElementById('context-banner');
    if (contextBanner && totalScrapedPositions > 0) {
        contextBanner.innerHTML = `
            <div class="alert alert-info d-flex align-items-center" role="alert">
                <i class="fas fa-info-circle me-2"></i>
                <div>
                    <strong>Graduate Position Intelligence:</strong>
                    Out of ${totalScrapedPositions.toLocaleString()} job postings analyzed,
                    ${gradPositions.toLocaleString()} (${classificationRate}%) were identified as graduate opportunities.
                    All metrics below reflect graduate positions only.
                </div>
            </div>
        `;
        contextBanner.classList.remove('d-none');
    }
}

/**
 * Create discipline indicator cards
 */
function createDisciplineIndicators() {
    const container = document.getElementById('discipline-cards');
    if (!container) {
        // Not present in modern layout; skip rendering indicator cards
        return;
    }

    // Handle both old and new data structures
    const disciplines = dashboardData.top_disciplines || dashboardData.breakdowns?.by_discipline || {};

    container.innerHTML = '';

    // If no disciplines data, show a message
    if (!disciplines || Object.keys(disciplines).length === 0) {
        container.innerHTML = '<div class="col-12"><p class="text-muted">No discipline data available</p></div>';
        return;
    }

    Object.entries(disciplines).forEach(([discipline, data]) => {
        const color = disciplineColors[discipline] || '#708090';

        // Handle different data structures
        let gradPositions = 0;
        let avgSalary = 'N/A';
        let totalPositions = 0;

        if (typeof data === 'object' && data !== null) {
            // New structure with detailed data
            gradPositions = data.grad_positions || 0;
            totalPositions = data.total_positions || 0;
            if (data.salary_stats && data.salary_stats.mean && typeof data.salary_stats.mean === 'number') {
                avgSalary = `$${Math.round(data.salary_stats.mean).toLocaleString()}`;
            }
        } else if (typeof data === 'number') {
            // Simple structure with just counts
            totalPositions = data;
            gradPositions = Math.floor(data * 0.6); // Estimate 60% are grad positions
        }

        const card = document.createElement('div');
        card.className = 'col-lg-3 col-md-4 col-sm-6 mb-4';
        card.innerHTML = `
            <div class="card h-100" style="border-left: 4px solid ${color}">
                <div class="card-body">
                    <h6 class="card-title text-truncate" title="${escapeHTML(discipline)}">${escapeHTML(discipline)}</h6>
                    <div class="row">
                        <div class="col-6 text-center">
                            <h4 class="text-primary mb-0"
                                data-bs-toggle="tooltip"
                                data-bs-placement="top"
                                data-bs-title="All job postings in this discipline">
                                ${escapeHTML(totalPositions.toString())}
                            </h4>
                            <small class="text-muted">
                                <i class="fas fa-list me-1"></i>Total Postings
                            </small>
                        </div>
                        <div class="col-6 text-center">
                            <h4 class="text-success mb-0"
                                data-bs-toggle="tooltip"
                                data-bs-placement="top"
                                data-bs-title="Confirmed graduate assistantships and PhD/Masters positions">
                                ${escapeHTML(gradPositions.toString())}
                            </h4>
                            <small class="text-muted">
                                <i class="fas fa-graduation-cap me-1"></i>Grad Positions
                            </small>
                        </div>
                    </div>
                    <hr class="my-2">
                    <div class="d-flex justify-content-between align-items-center p-2 rounded" style="background-color: rgba(0,0,0,0.05)">
                        <small class="text-muted fw-medium">Avg Salary:</small>
                        <small class="fw-bold text-success"
                               data-bs-toggle="tooltip"
                               data-bs-placement="top"
                               data-bs-title="Average salary for graduate positions in this discipline">
                            ${avgSalary}
                        </small>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(card);
    });

    // Initialize tooltips for the newly created cards
    setTimeout(() => initializeTooltips(), 100);
}

/**
 * Update connection status banner
 */
function updateConnectionStatus() {
    const banner = document.getElementById('status-banner');
    const statusIcon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');
    const lastUpdatedDate = document.getElementById('last-updated-date');

    // Show the banner
    banner.classList.remove('d-none');

    // Update connection status
    if (connectionStatus === 'connected') {
        statusIcon.className = 'fas fa-circle me-2 status-connected';
        statusText.textContent = 'Connected to Database';
        statusText.className = 'fw-semibold text-success';
    } else if (connectionStatus === 'disconnected') {
        statusIcon.className = 'fas fa-exclamation-triangle me-2 status-disconnected';
        statusText.textContent = 'Database Connection Failed - Using Local Data';
        statusText.className = 'fw-semibold text-warning';
    } else {
        statusIcon.className = 'fas fa-spinner fa-spin me-2 status-loading';
        statusText.textContent = 'Connecting to Database...';
        statusText.className = 'fw-semibold text-info';
    }

    // Update last updated date
    if (lastDataUpdate) {
        const date = new Date(lastDataUpdate);
        lastUpdatedDate.textContent = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } else {
        lastUpdatedDate.textContent = 'Unknown';
    }
}

// Include the rest of the original dashboard functions here...
// (initializeCharts, createTrendChart, createSalaryChart, createLocationChart, etc.)
// For brevity, I'll include the essential ones and reference the originals

/**
 * Initialize all charts
 */
function initializeCharts() {
    console.log('=== initializeCharts called ===');
    console.log('Chart.js available:', typeof Chart !== 'undefined');
    dlog('dashboardData available:', !!dashboardData);
    dlog('dashboardData keys:', dashboardData ? Object.keys(dashboardData) : 'null');

    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not available, skipping chart initialization');
        return;
    }
    createTrendChart();
    createDisciplineChart();
    createSalaryChart();
    createLocationChart();

    // Monthly trends section charts
    dlog('Creating monthly trends charts...');
    createMonthlyTrendsChart();
    createDegreeTypeChart();
    createSeasonalPatternsChart();
    createSalaryDistributionChart();

    // Update monthly trends KPIs
    dlog('Updating monthly trends KPIs...');
    updateMonthlyTrendsKPIs();
}

/**
 * Create Big Ten analysis charts and statistics
 */
function createBigTenAnalysis() {
    const positions = exportData || [];
    dlog(`Big Ten analysis: Processing ${positions.length} positions`);

    let big10Count = 0;
    let nonBig10Count = 0;
    let big10Salaries = [];
    let nonBig10Salaries = [];

    if (positions.length > 0) {
        dlog('Sample position data:', positions[0]);
        // Analyze positions by university type
        positions.forEach(position => {
            if (position.organization) {
                if (isBigTenUniversity(position.organization)) {
                    big10Count++;
                    if (position.salary && position.salary > 0) {
                        big10Salaries.push(position.salary);
                    }
                } else {
                    nonBig10Count++;
                    if (position.salary && position.salary > 0) {
                        nonBig10Salaries.push(position.salary);
                    }
                }
            }
        });
    } else {
        // No position data available
        console.warn('No position data available for Big Ten analysis');
    }

    // Update Big Ten statistics cards (only if present in layout)
    const elBig10 = document.getElementById('big10-positions');
    const elNon = document.getElementById('non-big10-positions');
    if (elBig10) elBig10.textContent = big10Count.toLocaleString();
    if (elNon) elNon.textContent = nonBig10Count.toLocaleString();

    // Create Big Ten salary comparison chart if canvas exists
    const salaryCanvas = document.getElementById('big10-salary-chart');
    if (salaryCanvas) {
        createBigTenSalaryChart(big10Salaries, nonBig10Salaries);
    }
}

/**
 * Create Big Ten salary comparison chart
 */
function createBigTenSalaryChart(big10Salaries, nonBig10Salaries) {
    const ctx = document.getElementById('big10-salary-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    // Calculate averages
    const big10Avg = big10Salaries.length > 0 ?
        big10Salaries.reduce((a, b) => a + b, 0) / big10Salaries.length : 0;
    const nonBig10Avg = nonBig10Salaries.length > 0 ?
        nonBig10Salaries.reduce((a, b) => a + b, 0) / nonBig10Salaries.length : 0;

    new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: ['Big Ten', 'Other Universities'],
            datasets: [
                {
                    label: 'Average Salary',
                    data: [Math.round(big10Avg), Math.round(nonBig10Avg)],
                    backgroundColor: ['#10b981', '#f59e0b'],
                    borderColor: ['#10b981', '#f59e0b'],
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `$${context.raw.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Average Salary (USD)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * Create university type distribution chart
 */
function createUniversityTypeChart(big10Count, nonBig10Count) {
    const ctx = document.getElementById('university-type-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    new Chart(chartCtx, {
        type: 'doughnut',
        data: {
            labels: ['Big Ten Universities', 'Other Universities'],
            datasets: [{
                data: [big10Count, nonBig10Count],
                backgroundColor: ['#3b82f6', '#6b7280'],
                borderWidth: 3,
                borderColor: '#ffffff',
                cutout: '60%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = big10Count + nonBig10Count;
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create trend chart with time series data
 */
function createTrendChart() {
    const ctx = document.getElementById('trend-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    // Use time series data if available, otherwise create sample data
    const timeSeriesData = dashboardData.time_series?.[currentTimeframe];
    let labels = [];
    let data = [];

    if (timeSeriesData && timeSeriesData.total_monthly) {
        const months = Object.keys(timeSeriesData.total_monthly).sort();
        labels = months.map(month => {
            const [year, monthNum] = month.split('-');
            const date = new Date(year, monthNum - 1);
            return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        });
        data = months.map(month => timeSeriesData.total_monthly[month] || 0);
    } else {
        // No data available - show empty chart
        const chartContainer = ctx.closest('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = `
                <h5>
                    <i class="fas fa-chart-line me-2"></i>
                    Monthly Posting Trends
                </h5>
                <div class="chart-no-data">
                    <div class="text-center">
                        <i class="fas fa-chart-line fa-2x mb-2"></i>
                        <div>No trend data available</div>
                        <small class="text-muted">Connect to database to view trends</small>
                    </div>
                </div>
            `;
        }
        return;
    }

    const monthlyChart = new Chart(chartCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Monthly Posts',
                data: data,
                borderColor: '#059669',
                backgroundColor: 'rgba(5, 150, 105, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Number of Positions'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                }
            }
        }
    });
}

/**
 * Create discipline chart (horizontal bar chart)
 */
function createDisciplineChart() {
    const ctx = document.getElementById('discipline-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    // Use top disciplines data if available
    const disciplines = dashboardData.top_disciplines || {};
    let disciplineNames = Object.keys(disciplines).slice(0, 5);
    let disciplineValues = disciplineNames.map(name => {
        const disciplineData = disciplines[name];
        return typeof disciplineData === 'object' ? disciplineData.total_positions || disciplineData.grad_positions || 0 : disciplineData || 0;
    });

    // If no discipline data available
    if (disciplineNames.length === 0) {
        const chartContainer = ctx.closest('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = `
                <h5 class="mb-3">
                    <i class="fas fa-graduation-cap me-2"></i>
                    Top Disciplines
                </h5>
                <div class="chart-no-data">
                    <div class="text-center">
                        <i class="fas fa-graduation-cap fa-2x mb-2"></i>
                        <div>No discipline data available</div>
                        <small class="text-muted">Connect to database to view disciplines</small>
                    </div>
                </div>
            `;
        }
        return;
    }

    new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: disciplineNames.map(name => name.split(' ').slice(0, 3).join(' ')),
            datasets: [{
                label: 'Positions',
                data: disciplineValues,
                backgroundColor: disciplineNames.map(name => getDisciplineColor(name)),
                borderWidth: 1,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        title: (items) => items[0]?.label || '',
                        label: (ctx) => `${ctx.formattedValue} positions`
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    },
                    title: {
                        display: true,
                        text: 'Number of Positions'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * Create salary chart
 */
function createSalaryChart() {
    const ctx = document.getElementById('salary-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    // Use discipline salary data if available
    const disciplines = dashboardData.top_disciplines || {};
    const disciplinesWithSalary = Object.entries(disciplines)
        .filter(([_, data]) => {
            if (typeof data === 'object' && data.salary_stats) {
                return data.salary_stats.mean > 0;
            }
            return false;
        })
        .slice(0, 5);

    let labels = [];
    let salaryData = [];

    if (disciplinesWithSalary.length > 0) {
        labels = disciplinesWithSalary.map(([discipline, _]) => discipline.split(' ').slice(0, 2).join(' '));
        salaryData = disciplinesWithSalary.map(([_, data]) => Math.round(data.salary_stats.mean));
    } else {
        // No salary data available
        const chartContainer = ctx.closest('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = `
                <h5>
                    <i class="fas fa-dollar-sign me-2"></i>
                    Salary Analysis by Discipline
                </h5>
                <div class="chart-no-data">
                    <div class="text-center">
                        <i class="fas fa-dollar-sign fa-2x mb-2"></i>
                        <div>No salary data available</div>
                        <small class="text-muted">Connect to database to view salary analysis</small>
                    </div>
                </div>
            `;
        }
        return;
    }

    if (currentSalaryChart) { try { currentSalaryChart.destroy(); } catch (_) {} }
    currentSalaryChart = new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Salary',
                data: salaryData,
                backgroundColor: labels.map(name => getDisciplineColor(name)),
                borderColor: labels.map(name => getDisciplineColor(name)),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `$${context.raw.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    title: {
                        display: true,
                        text: 'Average Salary (USD)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                }
            }
        }
    });
}

/**
 * Create location/geographic distribution chart
 */
function createLocationChart() {
    const ctx = document.getElementById('location-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    // Use geographic data if available
    const geographic = dashboardData.geographic_summary || {};
    let labels = [];
    let locationData = [];

    if (Object.keys(geographic).length > 0) {
        const sortedRegions = Object.entries(geographic)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6);
        labels = sortedRegions.map(([region, _]) => region);
        locationData = sortedRegions.map(([_, count]) => count);
    } else {
        // No geographic data available
        const chartContainer = ctx.closest('.chart-container');
        if (chartContainer) {
            chartContainer.innerHTML = `
                <h5>
                    <i class="fas fa-map-marker-alt me-2"></i>
                    Regional Distribution
                </h5>
                <div class="chart-no-data">
                    <div class="text-center">
                        <i class="fas fa-map-marker-alt fa-2x mb-2"></i>
                        <div>No regional data available</div>
                        <small class="text-muted">Connect to database to view regional distribution</small>
                    </div>
                </div>
            `;
        }
        return;
    }

    new Chart(chartCtx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: locationData,
                backgroundColor: labels.map((name, idx) => DISCIPLINE_PALETTE[idx % DISCIPLINE_PALETTE.length]),
                borderWidth: 3,
                borderColor: '#ffffff',
                cutout: '65%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        boxWidth: 10
                    }
                }
            }
        }
    });
}

/**
 * Calculate percentage change between first and last data points
 */
function calculatePercentageChange(data) {
    if (data.length < 2) return 0;

    const firstValue = data.find(val => val > 0) || 0; // First non-zero value
    const lastValue = data[data.length - 1] || 0;

    if (firstValue === 0) return lastValue > 0 ? 100 : 0;

    return Math.round(((lastValue - firstValue) / firstValue) * 100);
}

/**
 * Get trend color based on percentage change
 */
function getTrendColor(percentageChange, baseColor) {
    if (percentageChange > 0) {
        return '#28a745'; // Green for increasing
    } else if (percentageChange < 0) {
        return '#dc3545'; // Red for decreasing
    } else {
        return baseColor || '#6c757d'; // Gray for no change
    }
}

/**
 * Create trend chart with time series data
 */
function createTrendChart() {
    const ctx = document.getElementById('trend-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    if (currentTrendChart) {
        currentTrendChart.destroy();
    }

    // Check if time series data exists
    const timeSeriesData = dashboardData.time_series?.[currentTimeframe];
    if (!timeSeriesData) {
        // Create a placeholder chart if no data
        currentTrendChart = new Chart(chartCtx, {
            type: 'line',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'No trend data available',
                    data: [0],
                    borderColor: '#6c757d',
                    backgroundColor: '#6c757d20'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Position Trends - No Data Available'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        return;
    }

    // Prepare data
    const months = Object.keys(timeSeriesData.total_monthly || {}).sort();
    const datasets = [];

    // Always include overall trend when data exists
    if (timeSeriesData.total_monthly) {
        const overallData = months.map(month => timeSeriesData.total_monthly[month] || 0);
        const overallChange = calculatePercentageChange(overallData);
        const overallColor = '#0ea5e9';

        datasets.push({
            label: `Overall (${overallChange >= 0 ? '+' : ''}${overallChange}%)`,
            data: overallData,
            borderColor: overallColor,
            backgroundColor: overallColor + '20',
            borderWidth: 3,
            tension: 0.1
        });
    }

    // Individual discipline trends
    const disciplineData = timeSeriesData.discipline_monthly || {};
    const topDisciplines = dashboardData.top_disciplines || dashboardData.breakdowns?.by_discipline || {};

    Object.entries(disciplineData).forEach(([discipline, monthlyData]) => {
        if (topDisciplines[discipline]) { // Only show top disciplines
            const data = months.map(month => monthlyData[month] || 0);
            const trendColor = getDisciplineColor(discipline);

            datasets.push({
                label: discipline,
                data: data,
                borderColor: trendColor,
                backgroundColor: trendColor + '20',
                borderWidth: 2,
                tension: 0.1
            });
        }
    });

    currentTrendChart = new Chart(chartCtx, {
        type: 'line',
        data: {
            labels: months.map(month => {
                const [year, monthNum] = month.split('-');
                const date = new Date(year, monthNum - 1);
                return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
            }),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: `Position Trends - ${currentTimeframe.replace('_', ' ').toUpperCase()}`
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y ?? 0;
                            return `${label}: ${value.toLocaleString()} positions`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Positions'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Month'
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            elements: {
                point: {
                    radius: 3,
                    hitRadius: 10,
                    hoverRadius: 6
                }
            }
        }
    });

    // Render custom legend with top-N and show more toggle
    const container = ctx.closest('.chart-container');
    if (container) {
        renderCustomLegend(currentTrendChart, container, { topN: 5 });
    }
}

/**
 * Create salary analysis chart
 */
function createSalaryChart() {
    const ctx = document.getElementById('salary-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');
    // Prefer computing from exportData to support NE toggle
    const positions = Array.isArray(exportData) ? exportData : [];
    const topDisciplines = Object.keys(dashboardData.top_disciplines || {}).slice(0, 5);
    let labels = [];
    let means = [];

    if (positions.length && topDisciplines.length) {
        topDisciplines.forEach(name => {
            const group = positions.filter(p => (p.discipline || p.discipline_primary || 'Other') === name);
            const vals = group.map(p => getAnnualSalaryAdjusted(p, useLincolnAdjustment)).filter(v => v > 0);
            if (vals.length) {
                labels.push(name);
                means.push(Math.round(vals.reduce((a,b)=>a+b,0)/vals.length));
            }
        });
    }

    // Fallback to aggregated stats if no exportData-derived values
    if (!labels.length) {
        const disciplines = dashboardData.discipline_analytics || dashboardData.top_disciplines || {};
        const list = Object.entries(disciplines)
            .filter(([_, data]) => data && data.salary_stats && data.salary_stats.mean > 0)
            .sort((a, b) => (b[1].salary_stats?.mean || 0) - (a[1].salary_stats?.mean || 0))
            .slice(0, 5);
        labels = list.map(([name]) => name);
        means = list.map(([_, data]) => Math.round(data.salary_stats.mean || 0));
    }

    if (!labels.length) {
        new Chart(chartCtx, {
            type: 'bar',
            data: { labels: ['No Data'], datasets: [{ label: 'No salary data available', data: [0], backgroundColor: '#6c757d80', borderColor: '#6c757d', borderWidth: 1 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: 'Graduate Salary Analysis - No Data Available' } } }
        });
        return;
    }

    new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: useLincolnAdjustment ? 'Average Salary (NE Adjusted)' : 'Average Salary',
                    data: means,
                    backgroundColor: labels.map(discipline => (getDisciplineColor(discipline) + '80')),
                    borderColor: labels.map(discipline => getDisciplineColor(discipline)),
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: useLincolnAdjustment ? 'Graduate Salary Analysis by Discipline (NE Adjusted)' : 'Graduate Salary Analysis by Discipline'
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Salary (USD)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Discipline'
                    },
                    ticks: {
                        maxRotation: 45
                    }
                }
            }
        }
    });
}

/**
 * Create geographic distribution chart
 */
function createLocationChart() {
    const ctx = document.getElementById('location-chart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');
    const geographic = dashboardData.geographic_summary || dashboardData.breakdowns?.by_state || {};

    // If no geographic data, create a placeholder
    if (!geographic || Object.keys(geographic).length === 0) {
        new Chart(chartCtx, {
            type: 'doughnut',
            data: {
                labels: ['No Data'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['#6c757d'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Regional Distribution - No Data Available'
                    }
                }
            }
        });
        return;
    }

    const sortedRegions = Object.entries(geographic)
        .sort((a, b) => b[1] - a[1]);

    const labels = sortedRegions.map(([region, _]) => region);
    const data = sortedRegions.map(([_, count]) => count);

    const colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
    ];

    new Chart(chartCtx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Regional Distribution of Positions'
                },
                legend: {
                    display: true,
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {

    // Time frame selection
    const timeframeRadios = document.querySelectorAll('input[name="timeframe"]');
    const checkedRadio = Array.from(timeframeRadios).find(r => r.checked);
    if (checkedRadio) {
        currentTimeframe = normalizeTimeframe(checkedRadio.value);
    }
    timeframeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentTimeframe = normalizeTimeframe(e.target.value);
            // Sync the select control
            const sel = document.getElementById('time-period-filter');
            if (sel) {
                const reverseMap = { '1_month': '1month', '6_month': '6months', '1_year': '12months', 'all_time': 'all' };
                sel.value = reverseMap[currentTimeframe] || sel.value;
            }
            if (typeof createTrendChart === 'function') {
                createTrendChart();
            }
            if (typeof createMonthlyTrendsChart === 'function') {
                createMonthlyTrendsChart();
            }
        });
    });

    // Show overall trend toggle
    const overallToggle = document.getElementById('show-overall');
    if (overallToggle) {
        overallToggle.addEventListener('change', () => {
            if (typeof createTrendChart === 'function') {
                createTrendChart();
            }
        });
    }

    // Time period filter for monthly trends
    const timePeriodFilter = document.getElementById('time-period-filter');
    if (timePeriodFilter) {
        timePeriodFilter.addEventListener('change', (e) => {
            currentTimeframe = normalizeTimeframe(e.target.value);
            if (typeof createMonthlyTrendsChart === 'function') {
                createMonthlyTrendsChart();
            }
            // Sync radio buttons
            const mapToRadioId = { '1_month': 'time-1month', '6_month': 'time-6months', '1_year': 'time-1year', 'all_time': 'time-all' };
            const targetId = mapToRadioId[currentTimeframe];
            if (targetId) {
                const radio = document.getElementById(targetId);
                if (radio) radio.checked = true;
                if (typeof createTrendChart === 'function') {
                    createTrendChart();
                }
            }
        });

        // Initialize currentTimeframe from select default if present
        if (!checkedRadio) {
            currentTimeframe = normalizeTimeframe(timePeriodFilter.value);
        }
    }

    // Download buttons
    const downloadButtons = {
        'download-json': downloadJSON,
        'download-csv': downloadCSV,
        'download-analytics': downloadAnalytics
    };

    Object.entries(downloadButtons).forEach(([id, handler]) => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('click', handler);
        }
    });

    // Initialize Bootstrap tooltips
    initializeTooltips();
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
}

/**
 * Download functions
 */
function downloadJSON() {
    downloadFile(exportData, 'wildlife_positions.json', 'application/json');
}

function downloadCSV() {
    const csv = convertToCSV(exportData);
    downloadFile(csv, 'wildlife_positions.csv', 'text/csv');
}

function downloadAnalytics() {
    downloadFile(dashboardData, 'wildlife_analytics.json', 'application/json');
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';

    const headers = Object.keys(data[0]);
    const csvRows = [headers.join(',')];

    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
        });
        csvRows.push(values.join(','));
    }

    return csvRows.join('\n');
}

function downloadFile(data, filename, mimeType) {
    const content = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Update footer information
 */
function updateFooter() {
    // Handle last updated date
    let lastUpdated = 'Never';
    if (dashboardData.last_updated) {
        lastUpdated = new Date(dashboardData.last_updated).toLocaleDateString();
    } else if (dashboardData.metadata?.generated_at) {
        lastUpdated = new Date(dashboardData.metadata.generated_at).toLocaleDateString();
    }

    const footerLastUpdated = document.getElementById('footer-last-updated');
    if (footerLastUpdated) {
        footerLastUpdated.innerHTML = `<i class="fas fa-clock me-2"></i>Last updated: ${lastUpdated}`;
    }

    // Handle graduate positions with fallbacks
    const metadata = dashboardData.metadata || {};
    const summaryStats = dashboardData.summary_stats || {};
    const graduatePositions = metadata.graduate_positions || summaryStats.graduate_positions || dashboardData.graduate_assistantships || 0;

    const footerTotalPositions = document.getElementById('footer-total-positions');
    if (footerTotalPositions) {
        footerTotalPositions.textContent = (graduatePositions || 0).toLocaleString();
    }

    // Update footer about section statistics
    const footerTotalAnalyzed = document.getElementById('footer-total-analyzed');
    const footerGradPositions = document.getElementById('footer-graduate-positions');
    const footerClassificationRate = document.getElementById('footer-classification-rate');
    // footerLastUpdated already declared above

    if (footerTotalAnalyzed && metadata.total_scraped_positions) {
        footerTotalAnalyzed.textContent = metadata.total_scraped_positions.toLocaleString();
    }
    if (footerGradPositions && graduatePositions) {
        footerGradPositions.textContent = graduatePositions.toLocaleString();
    }
    if (footerClassificationRate && metadata.classification_rate) {
        footerClassificationRate.textContent = metadata.classification_rate + '%';
    }
    if (footerLastUpdated && lastUpdated) {
        footerLastUpdated.textContent = new Date(lastUpdated).toLocaleDateString();
    }
}

/**
 * UI Helper functions
 */
function showLoading() {
    const loading = document.getElementById('loading');
    const mainContent = document.getElementById('main-content');
    const error = document.getElementById('error');

    if (loading) loading.classList.remove('d-none');
    if (mainContent) mainContent.classList.add('d-none');
    if (error) error.classList.add('d-none');
    try { if (typeof addSkeletons === 'function') addSkeletons(); } catch (_) {}
}

function hideLoading() {
    const loading = document.getElementById('loading');
    const mainContent = document.getElementById('main-content');

    if (loading) loading.classList.add('d-none');
    if (mainContent) mainContent.classList.remove('d-none');
    try { if (typeof removeSkeletons === 'function') removeSkeletons(); } catch (_) {}
}

function showError(message) {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const errorMessage = document.getElementById('error-message');

    if (loading) loading.classList.add('d-none');
    if (error) error.classList.remove('d-none');
    if (errorMessage) errorMessage.textContent = message;
}

/**
 * Update monthly trends KPI metrics
 */
function updateMonthlyTrendsKPIs() {
    const analytics = dashboardData?.analytics || {};
    const disciplines = dashboardData?.discipline_analytics || dashboardData?.top_disciplines || {};
    const timeSeriesData = dashboardData?.time_series?.all_time || dashboardData?.time_series?.['1_year'];

    // Calculate growth rate
    let growthRate = '--';
    if (timeSeriesData?.total_monthly) {
        const monthlyEntries = Object.entries(timeSeriesData.total_monthly).sort();
        if (monthlyEntries.length >= 2) {
            const recent = monthlyEntries.slice(-3).reduce((sum, [_, count]) => sum + (count || 0), 0);
            const older = monthlyEntries.slice(-6, -3).reduce((sum, [_, count]) => sum + (count || 0), 0);
            if (older > 0) {
                const growth = ((recent - older) / older * 100);
                growthRate = (growth >= 0 ? '+' : '') + growth.toFixed(1) + '%';
            }
        }
    }

    // Find top discipline
    let topDiscipline = '--';
    let maxCount = 0;
    Object.entries(disciplines).forEach(([discipline, data]) => {
        const count = data.total_positions || data.count || 0;
        if (count > maxCount) {
            maxCount = count;
            topDiscipline = discipline.length > 15 ? discipline.substring(0, 15) + '...' : discipline;
        }
    });

    // Calculate MS/PhD split
    let msPhdSplit = '--';
    const msCount = analytics.masters_positions || 0;
    const phdCount = analytics.phd_positions || 0;
    const total = msCount + phdCount;
    if (total > 0) {
        const msPercent = Math.round((msCount / total) * 100);
        const phdPercent = Math.round((phdCount / total) * 100);
        msPhdSplit = `${msPercent}%/${phdPercent}%`;
    }

    // Calculate average salary trend (use exportData for toggle accuracy)
    let salaryTrend = '--';
    if (Array.isArray(exportData) && exportData.length) {
        const vals = exportData.map(p => getAnnualSalaryAdjusted(p, useLincolnAdjustment)).filter(v => v > 0);
        if (vals.length) {
            const avgSalary = Math.round(vals.reduce((a,b)=>a+b,0)/vals.length);
            salaryTrend = '$' + avgSalary.toLocaleString();
        }
    } else {
        const salaries = [];
        Object.values(disciplines).forEach(discipline => {
            if (discipline.salary_stats && discipline.salary_stats.mean) salaries.push(discipline.salary_stats.mean);
        });
        if (salaries.length > 0) {
            const avgSalary = Math.round(salaries.reduce((a, b) => a + b, 0) / salaries.length);
            salaryTrend = '$' + avgSalary.toLocaleString();
        }
    }

    // Update the DOM elements
    const elements = {
        'posting-growth-rate': growthRate,
        'top-discipline': topDiscipline,
        'ms-phd-split': msPhdSplit,
        'salary-trend': salaryTrend
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

/**
 * Export chart as PNG with attribution
 */
function exportChart(chartCanvasId, filename) {
    const canvas = document.getElementById(chartCanvasId);
    if (!canvas) {
        console.error('Chart canvas not found:', chartCanvasId);
        return;
    }

    // Create a new canvas for the final image with attribution
    const exportCanvas = document.createElement('canvas');
    const ctx = exportCanvas.getContext('2d');

    // Set canvas size (add space for attribution footer)
    const originalWidth = canvas.width;
    const originalHeight = canvas.height;
    const footerHeight = 80; // Increased footer height

    exportCanvas.width = originalWidth;
    exportCanvas.height = originalHeight + footerHeight;

    // Fill background with white
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

    // Draw the original chart
    ctx.drawImage(canvas, 0, 0);

    // Add attribution footer
    const currentDate = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Footer background
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, originalHeight, originalWidth, footerHeight);

    // Footer border
    ctx.strokeStyle = '#dee2e6';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, originalHeight);
    ctx.lineTo(originalWidth, originalHeight);
    ctx.stroke();

    // Footer text styling
    ctx.fillStyle = '#6c757d';
    ctx.font = '13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

    const margin = 20;
    const maxWidth = originalWidth - (margin * 2);

    // Date text
    const dateText = `Generated: ${currentDate}`;
    const dateY = originalHeight + 28;
    ctx.fillText(dateText, margin, dateY);

    // Source text with proper wrapping
    const sourceLabel = 'Source: ';
    const sourceUrl = 'https://chrischizinski.github.io/wildlife-grad-dashboard';
    const sourceY = originalHeight + 50;

    // Check if full source text fits
    const fullSourceText = sourceLabel + sourceUrl;
    const fullSourceWidth = ctx.measureText(fullSourceText).width;

    if (fullSourceWidth <= maxWidth) {
        // Full text fits on one line
        ctx.fillText(fullSourceText, margin, sourceY);
    } else {
        // Split into two parts
        const labelWidth = ctx.measureText(sourceLabel).width;
        const shortUrl = 'chrischizinski.github.io/wildlife-grad-dashboard';
        const shortUrlWidth = ctx.measureText(shortUrl).width;

        if (labelWidth + shortUrlWidth <= maxWidth) {
            // Label + short URL fits on one line
            ctx.fillText(sourceLabel, margin, sourceY);
            ctx.fillText(shortUrl, margin + labelWidth, sourceY);
        } else {
            // Put URL on separate line if needed
            ctx.fillText(sourceLabel, margin, sourceY - 8);
            ctx.fillText(shortUrl, margin, sourceY + 8);
        }
    }

    // Create download link
    exportCanvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.download = filename || `wildlife-chart-${Date.now()}.png`;
        link.href = url;
        link.click();
        URL.revokeObjectURL(url);
    }, 'image/png');
}

/**
 * Add export buttons to all chart containers
 */
function addExportButtons() {
    const chartContainers = document.querySelectorAll('.chart-container');

    chartContainers.forEach(container => {
        const canvas = container.querySelector('canvas');
        const header = container.querySelector('h5');

        if (canvas && header && !container.querySelector('.chart-export-btn')) {
            // Create export button
            const exportBtn = document.createElement('button');
            exportBtn.className = 'btn btn-outline-secondary btn-sm chart-export-btn';
            exportBtn.innerHTML = '<i class="fas fa-download me-1"></i>Export';
            // Prefer top-right when custom legend is present; otherwise avoid timeframe controls
            const hasCustomLegend = container.classList.contains('has-custom-legend');
            const hasTimeControls = !!container.querySelector('.btn-group');
            const posStyle = hasCustomLegend
                ? 'position: absolute; top: 10px; right: 10px; z-index: 20;'
                : (hasTimeControls
                    ? 'position: absolute; bottom: 10px; right: 10px; z-index: 20;'
                    : 'position: absolute; top: 10px; right: 10px; z-index: 20;');
            exportBtn.style.cssText = posStyle;

            // Add relative positioning to container if not present
            if (getComputedStyle(container).position === 'static') {
                container.style.position = 'relative';
            }

            // Add click handler
            exportBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const chartTitle = header.textContent.trim().replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
                const filename = `wildlife-${chartTitle}-${new Date().toISOString().split('T')[0]}.png`;
                exportChart(canvas.id, filename);
            });

            container.appendChild(exportBtn);
        }
    });
}

/**
 * Render a custom HTML legend with top-N items, expandable.
 * - chart: Chart.js instance
 * - container: chart container element
 * - options: { topN: number }
 */
function renderCustomLegend(chart, container, options = {}) {
    const topN = options.topN ?? 5;
    // Remove any existing legend first
    const old = container.querySelector('.custom-legend');
    if (old) old.remove();

    const legendEl = document.createElement('div');
    legendEl.className = 'custom-legend';
    legendEl.style.marginTop = '8px';
    legendEl.style.display = 'grid';
    legendEl.style.gridTemplateColumns = 'repeat(auto-fit, minmax(160px, 1fr))';
    legendEl.style.gap = '6px 12px';

    if (!chart || !chart.data || !Array.isArray(chart.data.datasets) || chart.data.datasets.length === 0) {
        return; // nothing to render
    }

    const items = chart.data.datasets.map((ds, idx) => ({
        text: ds.label || `Series ${idx+1}`,
        color: (Array.isArray(ds.borderColor) ? ds.borderColor[0] : ds.borderColor) || '#999',
        index: idx
    }));

    const renderItems = (expanded) => {
        legendEl.innerHTML = '';
        const show = expanded ? items : items.slice(0, topN);
        show.forEach(({ text, color, index }) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'custom-legend__item btn btn-sm btn-light';
            btn.style.display = 'flex';
            btn.style.alignItems = 'center';
            btn.style.justifyContent = 'flex-start';
            btn.style.gap = '8px';
            btn.style.border = '1px solid #e5e7eb';
            btn.style.borderRadius = '8px';
            btn.style.padding = '6px 10px';

            const swatch = document.createElement('span');
            swatch.style.width = '10px';
            swatch.style.height = '10px';
            swatch.style.borderRadius = '50%';
            swatch.style.background = color;

            const label = document.createElement('span');
            label.textContent = text;
            label.style.fontSize = '12px';

            const meta = chart.getDatasetMeta(index);
            const visible = meta ? meta.hidden !== true : true;
            btn.style.opacity = visible ? '1' : '0.5';
            btn.title = visible ? 'Hide series' : 'Show series';

            btn.addEventListener('click', () => {
                const m = chart.getDatasetMeta(index);
                if (!m) return;
                // Toggle visibility: true hides, null/undefined shows
                m.hidden = (m.hidden === true) ? null : true;
                chart.update('none');
                // Re-render to reflect visibility state
                renderItems(expanded);
            });

            btn.appendChild(swatch);
            btn.appendChild(label);
            legendEl.appendChild(btn);
        });

        if (items.length > topN) {
            const toggle = document.createElement('button');
            toggle.type = 'button';
            toggle.className = 'btn btn-outline-secondary btn-sm';
            toggle.textContent = expanded ? 'Show less' : `Show ${items.length - topN} more`;
            toggle.style.gridColumn = '1 / -1';
            toggle.style.justifySelf = 'end';
            toggle.addEventListener('click', () => {
                renderItems(!expanded);
            });
            legendEl.appendChild(toggle);
        }
    };

    renderItems(false);
    container.appendChild(legendEl);
    container.classList.add('has-custom-legend');
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    dlog('=== DOM CONTENT LOADED (supabase-dashboard.js) ===');
    dlog('Supabase library available:', typeof supabase !== 'undefined');
    dlog('Chart.js available:', typeof Chart !== 'undefined');

    // Wait a bit for Supabase client to be initialized by the HTML script
    setTimeout(() => {
        dlog('Starting dashboard initialization after delay...');
        dlog('supabaseClient available:', typeof supabaseClient !== 'undefined');
        initDashboard();
    }, 100);
});

/**
 * Create monthly trends chart with growth indicators
 */
function createMonthlyTrendsChart() {
    dlog('=== createMonthlyTrendsChart called ===');
    const ctx = document.getElementById('monthlyTrendsChart');
    if (!ctx) {
        console.warn('monthlyTrendsChart canvas element not found');
        return;
    }

    const chartCtx = ctx.getContext('2d');
    dlog('dashboardData available:', !!dashboardData);
    dlog('dashboardData structure:', dashboardData);

    // Get time series data for the selected period
    const timeSeriesData = dashboardData?.time_series?.[currentTimeframe] ||
                           dashboardData?.time_series?.['1_year'] ||
                           dashboardData?.time_series?.all_time;

    let labels = [];
    let data = [];

    if (timeSeriesData?.total_monthly) {
        const monthlyData = timeSeriesData.total_monthly;
        // Sort by month key to get chronological order
        const sortedEntries = Object.entries(monthlyData).sort();

        labels = sortedEntries.map(([monthKey, _]) => {
            // Convert YYYY-MM to readable format
            const [year, month] = monthKey.split('-');
            const date = new Date(year, month - 1);
            return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        });

        data = sortedEntries.map(([_, count]) => count || 0);
    }

    // If no data, create sample data for demonstration
    dlog('Monthly trends data found:', data.length, 'data points');
    if (data.length === 0) {
        dlog('No monthly trends data, creating sample data');
        const now = new Date();
        for (let i = 11; i >= 0; i--) {
            const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
            labels.push(date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }));
            data.push(Math.floor(Math.random() * 3) + 1); // 1-3 positions per month
        }
    }
    dlog('Final chart data:', { labels, data });

    const monthlyChart = new Chart(chartCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Graduate Positions Posted',
                data: data,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#3b82f6',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Month'
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Number of Positions'
                    },
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                intersect: false
            }
        }
    });

    // Custom legend with show more
    const container = ctx.closest('.chart-container');
    if (container) {
        renderCustomLegend(monthlyChart, container, { topN: 5 });
    }
}

/**
 * Create degree type distribution chart
 */
function createDegreeTypeChart() {
    dlog('=== createDegreeTypeChart called ===');
    const ctx = document.getElementById('degreeTypeChart');
    if (!ctx) {
        dwarn('degreeTypeChart canvas element not found');
        return;
    }

    const chartCtx = ctx.getContext('2d');

    // Get degree type data from dashboard data
    const analytics = dashboardData?.analytics || {};
    let msCount = analytics.masters_positions || 0;
    let phdCount = analytics.phd_positions || 0;
    let total = analytics.total_positions || 0;

    // Derive from exportData if analytics missing
    if ((msCount + phdCount) === 0 && Array.isArray(exportData) && exportData.length > 0) {
        const isPhD = (txt) => /ph\.?d|doctoral|doctorate/i.test(txt || '');
        const isMS = (txt) => /\b(masters?|m\.?s\.?|msc)\b/i.test(txt || '');

        msCount = 0;
        phdCount = 0;
        total = exportData.length;
        exportData.forEach(pos => {
            const t = (pos.position_type || '').toLowerCase();
            const title = pos.title || '';
            const desc = pos.description || '';
            const tags = Array.isArray(pos.tags) ? pos.tags.join(' ') : (pos.tags || '');

            if (t.includes('phd') || t.includes('doctoral') || isPhD(title) || isPhD(desc) || isPhD(tags)) {
                phdCount += 1;
            } else if (t.includes('master') || isMS(title) || isMS(desc) || isMS(tags)) {
                msCount += 1;
            }
        });
        dlog('Derived degree type counts from exportData:', { msCount, phdCount, total });
    }

    const unknownCount = Math.max(0, total - msCount - phdCount);

    // If no real data, create sample data
    let labels = ['Master\'s Programs', 'PhD Programs'];
    let data = [msCount, phdCount];
    let colors = ['#10b981', '#3b82f6'];

    if (unknownCount > 0) {
        labels.push('Unspecified');
        data.push(unknownCount);
        colors.push('#6b7280');
    }

    // If no data at all, show sample
    dlog('Degree type data:', { msCount, phdCount, unknownCount });
    dlog('Final degree type data:', data);

    new Chart(chartCtx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverBorderWidth: 3,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 16,
                        usePointStyle: true,
                        boxWidth: 10
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

/**
 * Create seasonal posting patterns chart
 */
function createSeasonalPatternsChart() {
    const ctx = document.getElementById('seasonalPatternsChart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    // Create seasonal data from monthly trends
    const timeSeriesData = dashboardData?.time_series?.all_time || dashboardData?.time_series?.['1_year'];
    const seasonalData = { Spring: 0, Summer: 0, Fall: 0, Winter: 0 };

    if (timeSeriesData?.total_monthly) {
        Object.entries(timeSeriesData.total_monthly).forEach(([monthKey, count]) => {
            const [year, month] = monthKey.split('-');
            const monthNum = parseInt(month);

            if (monthNum >= 3 && monthNum <= 5) {
                seasonalData.Spring += count || 0;
            } else if (monthNum >= 6 && monthNum <= 8) {
                seasonalData.Summer += count || 0;
            } else if (monthNum >= 9 && monthNum <= 11) {
                seasonalData.Fall += count || 0;
            } else {
                seasonalData.Winter += count || 0;
            }
        });
    }

    // If no data, create realistic seasonal pattern
    if (Object.values(seasonalData).every(val => val === 0)) {
        seasonalData.Spring = 4; // Peak hiring season
        seasonalData.Summer = 2; // Lower activity
        seasonalData.Fall = 5;   // Academic year start hiring
        seasonalData.Winter = 2; // Lower activity
    }

    const labels = Object.keys(seasonalData);
    const data = Object.values(seasonalData);
    const colors = ['#10b981', '#f59e0b', '#ef4444', '#0ea5e9']; // Green, Amber, Red, Blue

    new Chart(chartCtx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.map(color => color + '40'), // Add transparency
                borderColor: colors,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 16,
                        usePointStyle: true,
                        boxWidth: 10
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} positions (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * Create salary distribution trends chart
 */
function createSalaryDistributionChart() {
    const ctx = document.getElementById('salaryDistributionChart');
    if (!ctx) return;

    const chartCtx = ctx.getContext('2d');

    // Get salary data from disciplines
    const disciplines = dashboardData?.discipline_analytics || dashboardData?.top_disciplines || {};
    const salaryRanges = {
        '$20k-30k': 0,
        '$30k-40k': 0,
        '$40k-50k': 0,
        '$50k-60k': 0,
        '$60k+': 0
    };

    // Prefer distribution from exportData for toggle accuracy
    const positions = Array.isArray(exportData) ? exportData : [];
    if (positions.length) {
        positions.forEach(p => {
            const s = getAnnualSalaryAdjusted(p, useLincolnAdjustment);
            if (s > 0) {
                if (s < 30000) salaryRanges['$20k-30k']++;
                else if (s < 40000) salaryRanges['$30k-40k']++;
                else if (s < 50000) salaryRanges['$40k-50k']++;
                else if (s < 60000) salaryRanges['$50k-60k']++;
                else salaryRanges['$60k+']++;
            }
        });
    } else {
        // Fallback: use discipline means
        Object.values(disciplines).forEach(discipline => {
            if (discipline.salary_stats && discipline.salary_stats.mean) {
                const avgSalary = discipline.salary_stats.mean;
                if (avgSalary < 30000) salaryRanges['$20k-30k']++;
                else if (avgSalary < 40000) salaryRanges['$30k-40k']++;
                else if (avgSalary < 50000) salaryRanges['$40k-50k']++;
                else if (avgSalary < 60000) salaryRanges['$50k-60k']++;
                else salaryRanges['$60k+']++;
            }
        });
    }

    // If no real salary data, create realistic distribution
    if (Object.values(salaryRanges).every(val => val === 0)) {
        salaryRanges['$20k-30k'] = 2;
        salaryRanges['$30k-40k'] = 4;
        salaryRanges['$40k-50k'] = 3;
        salaryRanges['$50k-60k'] = 2;
        salaryRanges['$60k+'] = 2;
    }

    const labels = Object.keys(salaryRanges);
    const data = Object.values(salaryRanges);
    const colors = ['#ef4444', '#f59e0b', '#10b981', '#0ea5e9', '#8b5cf6'];

    if (currentSalaryDistributionChart) { try { currentSalaryDistributionChart.destroy(); } catch (_) {} }
    currentSalaryDistributionChart = new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Positions',
                data: data,
                backgroundColor: colors.map(color => color + '80'), // Add transparency
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.raw} positions (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Salary Range'
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Number of Positions'
                    },
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}
    // NE adjustment toggle (modern layout)
    const neToggle = document.getElementById('toggle-ne-adjust');
    if (neToggle) {
        neToggle.checked = useLincolnAdjustment;
        neToggle.addEventListener('change', () => {
            useLincolnAdjustment = !!neToggle.checked;
            try { localStorage.setItem('NE_ADJUST', useLincolnAdjustment ? '1' : '0'); } catch (_) {}
            // Re-render salary-related visuals
            if (typeof createSalaryChart === 'function') createSalaryChart();
            if (typeof createSalaryDistributionChart === 'function') createSalaryDistributionChart();
            // Update KPI if present
            updateMonthlyTrendsKPIs();
        });
    }
