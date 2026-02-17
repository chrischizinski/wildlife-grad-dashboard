/**
 * Wildlife Jobs Dashboard Core
 * JSON-based dashboard for graduate assistantship positions
 * Refactored to remove Supabase dependencies.
 */

/**
 * Runtime logging utilities
 */
const WGD_DEBUG = true; // Enabled for development
const dlog = (...args) => { if (WGD_DEBUG) console.log(...args); };
const derror = (...args) => { if (WGD_DEBUG) console.error(...args); };

/**
 * Data fetching functions - loads from static JSON files
 */
class DataFetcher {
    constructor() {
        dlog('=== DataFetcher Constructor ===');
        dlog('Data source: JSON files only');
        this.dashboardData = null;
        this.exportData = null;
    }

    async fetchAllData() {
        try {
            dlog('Fetching data from JSON files...');

            // Fetch both analytics and raw data in parallel
            const [analyticsResponse, jobsResponse] = await Promise.all([
                fetchDataWithFallback('data/dashboard_analytics.json'),
                fetchDataWithFallback('data/enhanced_data.json') // This usually contains the full list or summary
            ]);

            // Try to get the detailed export data which has the job list
            let jobList = [];
            const exportResponse = await fetchDataWithFallback('data/export_data.json').catch(e => {
                dlog('export_data.json not found, falling back');
                return null;
            });

            if (exportResponse && exportResponse.ok) {
                jobList = await exportResponse.json();
            } else if (jobsResponse && jobsResponse.ok) {
                // Fallback if export_data isn't there
                const data = await jobsResponse.json();
                if (Array.isArray(data)) jobList = data;
                else if (data.jobs) jobList = data.jobs;
            }

            let dashboardAnalytics = {};
            if (analyticsResponse && analyticsResponse.ok) {
                dashboardAnalytics = await analyticsResponse.json();
            } else if (jobsResponse && jobsResponse.ok) {
                // Fallback: try to derive analytics from enhanced_data if separate file missing
                const data = await jobsResponse.json();
                dashboardAnalytics = data; // Assuming it matches structure
            }

            this.dashboardData = dashboardAnalytics;
            this.exportData = jobList;

            // Ensure dashboard shape matches what the UI expects
            this.ensureDashboardCompatibility(this.dashboardData);

            // Enrich trends if we have the full job list
            if (jobList.length > 0) {
                this.addDisciplineTrends(this.dashboardData, jobList);
            }

            return { dashboardData: this.dashboardData, exportData: this.exportData };

        } catch (error) {
            console.error('Error fetching JSON data:', error);
            throw error;
        }
    }


    ensureDashboardCompatibility(dashboardData) {
        if (!dashboardData) return;

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
            // We only care about grad positions usually, but let's be inclusive if flag is missing
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
        const entries = Object.entries(mapObj).sort((a, b) => a[0].localeCompare(b[0]));
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

    buildTimeSeriesFromTrends(monthlyTrends) {
        const graduateMonthly = {};
        monthlyTrends.forEach(trend => {
            graduateMonthly[trend.month_key] = trend.graduate_positions;
        });

        return {
            '1_month': { total_monthly: this.getLastNMonths(graduateMonthly, 1), discipline_monthly: {} },
            '3_month': { total_monthly: this.getLastNMonths(graduateMonthly, 3), discipline_monthly: {} },
            '6_month': { total_monthly: this.getLastNMonths(graduateMonthly, 6), discipline_monthly: {} },
            '1_year': { total_monthly: this.getLastNMonths(graduateMonthly, 12), discipline_monthly: {} },
            'all_time': { total_monthly: graduateMonthly, discipline_monthly: {} }
        };
    }

    getLastNMonths(monthlyData, n) {
        const sorted = Object.entries(monthlyData).sort();
        return Object.fromEntries(sorted.slice(-n));
    }
}

// Helper to fetch keys with fallbacks
async function fetchDataWithFallback(filename) {
    // Try current dir
    let res = await fetch(filename).catch(() => null);
    if (res && res.ok) return res;

    // Try up one level
    res = await fetch('../' + filename).catch(() => null);
    if (res && res.ok) return res;

    // Try ./ prefix
    res = await fetch('./' + filename).catch(() => null);
    return res;
}


// --- Main Application State ---
let dashboardData = null;
let jobList = null; // Full list of jobs
let appState = {
    timeframe: '1_year',
    charts: {},
    colIndex: null,
    disciplineColors: {}
};

// --- Color Palette ---
const PALETTE = {
    primary: '#0f766e', // Teal 700
    primaryLight: '#2dd4bf', // Teal 400
    secondary: '#475569', // Slate 600
    accent: '#f59e0b', // Amber 500
    disciplines: [
        '#0ea5e9', // Sky
        '#22c55e', // Green
        '#eab308', // Yellow
        '#f97316', // Orange
        '#ef4444', // Red
        '#a855f7', // Purple
        '#6366f1', // Indigo
        '#14b8a6'  // Teal
    ]
};

function buildDisciplineColorMap(disciplines) {
    const map = {};
    const names = Object.keys(disciplines || {});
    names.forEach((name, idx) => {
        map[name] = PALETTE.disciplines[idx % PALETTE.disciplines.length];
    });
    appState.disciplineColors = map;
}

// --- Initialization ---

async function initDashboard() {
    try {
        // Show loading
        document.getElementById('loading').classList.remove('d-none');
        document.getElementById('main-content').classList.add('d-none');

        // 1. Load Data
        const fetcher = new DataFetcher();
        const { dashboardData: dd, exportData: jobs } = await fetcher.fetchAllData();
        dashboardData = dd;
        jobList = jobs;

        if (!dashboardData) throw new Error('No dashboard data loaded');

        dlog('Data loaded:', { jobCount: jobList ? jobList.length : 0 });

        // 2. Prep State
        try {
            buildDisciplineColorMap(dashboardData.top_disciplines);
        } catch (e) { derror('Error in buildDisciplineColorMap', e); }

        // 3. Render Components
        renderKPIs();
        renderCharts();
        if (jobList) renderJobTable(jobList);

        // 4. Load Map (if component exists)
        if (window.renderJobMap && dashboardData.geographic_summary) {
            window.renderJobMap(dashboardData.geographic_summary);
        }

        // 5. Update Footer/Meta
        updateFooter();

        // 6. Show Content
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('main-content').classList.remove('d-none');

        // Update Status indicator
        const statusText = document.getElementById('status-text');
        if (statusText) statusText.textContent = 'Connected (JSON)';

        const statusIcon = document.getElementById('status-icon');
        if (statusIcon) statusIcon.className = 'fas fa-check-circle me-2 text-success';

        const statusBanner = document.getElementById('status-banner');
        if (statusBanner) statusBanner.classList.remove('d-none');

    } catch (e) {
        derror('Init failed', e);
        document.getElementById('error').classList.remove('d-none');
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('error-message').textContent = e.message;
    }
}


function renderKPIs() {
    const stats = dashboardData.summary_stats || {};

    setText('total-positions', (stats.total_scraped_positions || 0).toLocaleString());
    setText('grad-positions', (stats.graduate_positions || 0).toLocaleString());
    setText('disciplines-count', (stats.graduate_disciplines || 0).toLocaleString());

    // Derived or specific stats
    // Growth rate example (mock or real if available)
    setText('posting-growth-rate', '+5%'); // Placeholder logic could go here

    // Top discipline
    const topDisc = Object.entries(dashboardData.top_disciplines || {})
        .sort((a, b) => b[1].grad_positions - a[1].grad_positions)[0];
    setText('top-discipline', topDisc ? topDisc[0] : 'N/A');
}

function renderCharts() {
    if (typeof Chart === 'undefined') return;

    // Cleanup old
    Object.values(appState.charts).forEach(c => c.destroy());
    appState.charts = {};

    // 1. Trends Chart
    const trendsCtx = document.getElementById('trend-chart');
    if (trendsCtx && dashboardData.time_series) {
        const timeSeries = dashboardData.time_series[appState.timeframe];
        if (timeSeries && timeSeries.total_monthly) {
            const labels = Object.keys(timeSeries.total_monthly).sort();
            const data = labels.map(k => timeSeries.total_monthly[k]);

            appState.charts.trends = new Chart(trendsCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Graduate Positions',
                        data: data,
                        borderColor: PALETTE.primary,
                        backgroundColor: PALETTE.primaryLight + '44', // transparent
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
    }

    // 2. Discipline Chart (Doughnut)
    const discCtx = document.getElementById('discipline-chart');
    if (discCtx && dashboardData.top_disciplines) {
        const discData = Object.entries(dashboardData.top_disciplines)
            .sort((a, b) => b[1].grad_positions - a[1].grad_positions)
            .slice(0, 6);

        appState.charts.discipline = new Chart(discCtx, {
            type: 'doughnut',
            data: {
                labels: discData.map(d => d[0]),
                datasets: [{
                    data: discData.map(d => d[1].grad_positions),
                    backgroundColor: discData.map(d => appState.disciplineColors[d[0]] || '#cbd5e1'),
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12, usePointStyle: true } }
                },
                cutout: '70%'
            }
        });
    }

    // 3. Salary Chart
    const salaryCtx = document.getElementById('salary-chart');
    if (salaryCtx && dashboardData.top_disciplines) {
        // Filter disciplines with salary data
        const discWithSalary = Object.entries(dashboardData.top_disciplines)
            .filter(([, data]) => data.salary_stats && data.salary_stats.mean > 0)
            .sort((a, b) => b[1].salary_stats.mean - a[1].salary_stats.mean)
            .slice(0, 8);

        appState.charts.salary = new Chart(salaryCtx, {
            type: 'bar',
            data: {
                labels: discWithSalary.map(d => d[0]),
                datasets: [{
                    label: 'Avg Annual Salary',
                    data: discWithSalary.map(d => d[1].salary_stats.mean),
                    backgroundColor: PALETTE.primary,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: '#f1f5f9' }, ticks: { callback: (v) => '$' + v / 1000 + 'k' } },
                    y: { grid: { display: false } }
                }
            }
        });
    }
}

// --- Job Table Logic ---

function renderJobTable(jobs) {
    const tableBody = document.getElementById('job-table-body');
    if (!tableBody) return;
    if (!Array.isArray(jobs)) return;

    // Sort by date desc
    const sorted = [...jobs].sort((a, b) =>
        new Date(b.published_date || b.scraped_at) - new Date(a.published_date || a.scraped_at)
    );

    // Pagination or limit could go here. For now, top 50.
    const displayJobs = sorted.slice(0, 50);

    tableBody.innerHTML = displayJobs.map(job => `
        <tr>
            <td>
                <div class="fw-medium text-dark">${escapeHTML(job.title)}</div>
                <div class="small text-muted">${escapeHTML(job.organization)}</div>
            </td>
            <td><span class="badge bg-light text-dark border">${escapeHTML(job.discipline || 'Other')}</span></td>
            <td>${escapeHTML(job.location || 'Remote')}</td>
            <td><span class="text-success fw-medium">${formatSalary(job.salary || job.salary_min)}</span></td>
            <td class="text-end">
                <a href="${job.url}" target="_blank" class="btn btn-sm btn-outline-primary">View</a>
            </td>
        </tr>
    `).join('');
}

// --- Utilities ---

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function escapeHTML(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, function (m) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return map[m];
    });
}

function formatSalary(val) {
    if (!val) return '-';
    if (typeof val === 'number') return '$' + val.toLocaleString();
    return val;
}

function updateFooter() {
    const d = new Date().toLocaleDateString();
    setText('last-updated-date', dashboardData.metadata.last_updated ? new Date(dashboardData.metadata.last_updated).toLocaleDateString() : d);
}


// Event Listeners for Timeframe controls
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();

    document.querySelectorAll('input[name="timeframe"]').forEach(r => {
        r.addEventListener('change', (e) => {
            if (e.target.checked) {
                appState.timeframe = e.target.value;
                renderCharts();
            }
        });
    });
});

/**
 * Utility Functions
 */
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function escapeHTML(str) {
    if (typeof str !== 'string') return String(str);
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatSalary(value) {
    if (typeof value !== 'number' || isNaN(value)) return 'N/A';
    return '$' + Math.round(value).toLocaleString();
}
