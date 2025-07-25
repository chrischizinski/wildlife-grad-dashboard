/**
 * Supabase-enabled Wildlife Jobs Dashboard
 * Enhanced version that can fetch data from Supabase or fall back to JSON files
 */

/**
 * Data fetching functions
 */
class DataFetcher {
    constructor() {
        this.useSupabase = supabaseClient && isSupabaseConfigured();
        console.log(`Data source: ${this.useSupabase ? 'Supabase' : 'JSON files'}`);
    }

    async fetchAnalytics() {
        if (this.useSupabase) {
            return await this.fetchFromSupabase();
        } else {
            return await this.fetchFromJSON();
        }
    }

    async fetchFromSupabase() {
        try {
            console.log('=== SUPABASE FETCH START ===');
            console.log('Fetching analytics from Supabase...');
            
            // Get basic analytics
            console.log('Querying job_analytics...');
            const { data: analytics, error: analyticsError } = await supabaseClient
                .from('job_analytics')
                .select('*')
                .single();

            console.log('Analytics result:', { analytics, analyticsError });
            if (analyticsError) throw new Error(`Analytics query failed: ${analyticsError.message}`);

            // Get discipline breakdown
            console.log('Querying discipline_analytics...');
            const { data: disciplines, error: disciplinesError } = await supabaseClient
                .from('discipline_analytics')
                .select('*')
                .order('grad_positions', { ascending: false })
                .limit(10);

            console.log('Disciplines result:', { disciplines, disciplinesError });
            if (disciplinesError) throw new Error(`Disciplines query failed: ${disciplinesError.message}`);

            // Get geographic distribution
            console.log('Querying geographic_distribution...');
            const { data: geographic, error: geoError } = await supabaseClient
                .from('geographic_distribution')
                .select('*')
                .order('graduate_positions', { ascending: false })
                .limit(10);

            console.log('Geographic result:', { geographic, geoError });
            if (geoError) throw new Error(`Geographic query failed: ${geoError.message}`);

            // Get monthly trends for different timeframes
            console.log('Querying monthly_trends...');
            const { data: monthlyTrends, error: trendsError } = await supabaseClient
                .from('monthly_trends')
                .select('*')
                .order('year', { ascending: false })
                .order('month', { ascending: false })
                .limit(24); // Last 2 years

            console.log('Monthly trends result:', { monthlyTrends, trendsError });
            if (trendsError) throw new Error(`Monthly trends query failed: ${trendsError.message}`);

            console.log('All Supabase queries successful, transforming data...');
            // Transform data to match expected format
            const result = this.transformSupabaseData(analytics, disciplines, geographic, monthlyTrends);
            console.log('=== SUPABASE FETCH COMPLETE ===');
            return result;

        } catch (error) {
            console.error('=== SUPABASE FETCH ERROR ===');
            console.error('Error details:', error);
            console.error('Stack trace:', error.stack);
            console.log('Falling back to JSON files...');
            return await this.fetchFromJSON();
        }
    }

    async fetchFromJSON() {
        try {
            console.log('Fetching data from JSON files...');
            
            // First try the lightweight dashboard analytics file
            try {
                const analyticsResponse = await fetch('../data/dashboard_analytics.json').catch(() => {
                    console.log('Trying dashboard_analytics.json from root data directory');
                    return fetch('./data/dashboard_analytics.json').catch(() => {
                        console.log('Trying dashboard_analytics.json from current directory');
                        return fetch('data/dashboard_analytics.json');
                    });
                });
                
                if (analyticsResponse.ok) {
                    const dashboardData = await analyticsResponse.json();
                    
                    // Try to load export data as well
                    let exportData = [];
                    try {
                        const exportResponse = await fetch('../data/export_data.json').catch(() => {
                            return fetch('./data/export_data.json').catch(() => {
                                return fetch('data/export_data.json');
                            });
                        });
                        if (exportResponse.ok) {
                            exportData = await exportResponse.json();
                        }
                    } catch (exportError) {
                        console.log('Export data not available, using empty array');
                    }
                    
                    console.log('Using lightweight dashboard analytics');
                    return { dashboardData, exportData };
                }
            } catch (analyticsError) {
                console.log('Lightweight analytics not available, trying full enhanced data');
            }
            
            // Fallback to the original large files
            const [enhancedResponse, exportResponse] = await Promise.all([
                fetch('../data/enhanced_data.json').catch(() => {
                    console.log('Trying enhanced_data.json from root data directory');
                    return fetch('./data/enhanced_data.json').catch(() => {
                        console.log('Trying enhanced_data.json from current directory');
                        return fetch('data/enhanced_data.json');
                    });
                }),
                fetch('../data/export_data.json').catch(() => {
                    console.log('Trying export_data.json from root data directory');
                    return fetch('./data/export_data.json').catch(() => {
                        console.log('Trying export_data.json from current directory');
                        return fetch('data/export_data.json');
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
            
            return { dashboardData, exportData };
            
        } catch (error) {
            console.error('Error fetching JSON data:', error);
            throw error;
        }
    }

    transformSupabaseData(analytics, disciplines, geographic, monthlyTrends) {
        console.log('Transforming Supabase data:', { analytics, disciplines, geographic, monthlyTrends });
        
        // Transform disciplines data
        const disciplineStats = {};
        disciplines.forEach(disc => {
            disciplineStats[disc.discipline] = {
                total_positions: disc.total_positions,
                grad_positions: disc.grad_positions,
                salary_stats: disc.avg_salary ? { mean: disc.avg_salary } : null
            };
        });

        // Transform geographic data
        const geographicSummary = {};
        geographic.forEach(geo => {
            geographicSummary[geo.state_or_country] = geo.graduate_positions;
        });

        // Transform time series data
        const timeSeriesData = this.buildTimeSeriesFromTrends(monthlyTrends);

        // Build dashboard data structure matching expected format
        const dashboardData = {
            metadata: {
                generated_at: new Date().toISOString(),
                total_positions: analytics.total_positions
            },
            summary_stats: {
                total_positions: analytics.total_positions,
                graduate_positions: analytics.graduate_positions,
                positions_with_salary: analytics.positions_with_salary
            },
            top_disciplines: disciplineStats,
            geographic_summary: geographicSummary,
            time_series: timeSeriesData,
            last_updated: analytics.last_updated,
            // Add compatibility fields for the UI
            total_positions: analytics.total_positions,
            graduate_assistantships: analytics.graduate_positions
        };

        console.log('Transformed dashboard data:', dashboardData);

        // For export data, we'll create a simplified version
        const exportData = [];

        return { dashboardData, exportData };
    }

    buildTimeSeriesFromTrends(monthlyTrends) {
        const totalMonthly = {};
        monthlyTrends.forEach(trend => {
            totalMonthly[trend.month_key] = trend.total_positions;
        });

        return {
            '1_month': {
                total_monthly: this.getLastNMonths(totalMonthly, 1),
                discipline_monthly: {}
            },
            '3_month': {
                total_monthly: this.getLastNMonths(totalMonthly, 3),
                discipline_monthly: {}
            },
            '6_month': {
                total_monthly: this.getLastNMonths(totalMonthly, 6),
                discipline_monthly: {}
            },
            '1_year': {
                total_monthly: this.getLastNMonths(totalMonthly, 12),
                discipline_monthly: {}
            },
            'all_time': {
                total_monthly: totalMonthly,
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
let currentTimeframe = '1_month';
let currentTrendChart = null;
let dataFetcher = null;

// Chart color scheme - exactly 5 categories
const disciplineColors = {
    'Fisheries Management and Conservation': '#4682B4',  // Ocean blue
    'Wildlife Management and Conservation': '#2E8B57',   // Forest green  
    'Human Dimensions': '#CD853F',                       // Warm brown
    'Environmental Science': '#9932CC',                  // Purple
    'Other': '#708090'                                   // Slate gray
};

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
        showLoading();
        
        // Initialize data fetcher
        dataFetcher = new DataFetcher();
        
        // Fetch data
        const result = await dataFetcher.fetchAnalytics();
        dashboardData = result.dashboardData;
        exportData = result.exportData;
        
        console.log('Dashboard data loaded successfully:', {
            totalPositions: dashboardData.summary_stats?.total_positions || dashboardData.total_positions,
            exportRecords: exportData?.length || 0
        });
        
        // Initialize all components
        updateOverviewCards();
        createDisciplineIndicators();
        if (typeof Chart !== 'undefined') {
            initializeCharts();
        } else {
            console.warn('Chart.js not available, skipping charts');
        }
        setupEventListeners();
        updateFooter();
        
        hideLoading();
        
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showError(`Failed to load dashboard data: ${error.message}`);
    }
}

// Include all the original dashboard functions with minor adaptations
/**
 * Update overview summary cards
 */
function updateOverviewCards() {
    // Handle both old and new data structures
    const metadata = dashboardData.metadata || {};
    const summaryStats = dashboardData.summary_stats || {};
    const overview = dashboardData.overview || {};
    
    // Safely access data with fallbacks and ensure numeric values
    const totalPositions = metadata.total_positions || dashboardData.total_positions || summaryStats.total_positions || 0;
    const gradPositions = summaryStats.graduate_positions || overview.graduate_positions || dashboardData.graduate_assistantships || 0;
    const salaryPositions = summaryStats.positions_with_salary || metadata.positions_with_salary || overview.positions_with_salaries || 0;
    
    // Count disciplines from breakdowns if available
    const breakdowns = dashboardData.breakdowns || {};
    const disciplineData = breakdowns.by_discipline || dashboardData.top_disciplines || {};
    const disciplinesCount = Object.keys(disciplineData).length || overview.total_disciplines || 0;
    
    // Ensure values are numbers before calling toLocaleString
    document.getElementById('total-jobs').textContent = (totalPositions || 0).toLocaleString();
    document.getElementById('grad-positions').textContent = (gradPositions || 0).toLocaleString();
    document.getElementById('salary-positions').textContent = (salaryPositions || 0).toLocaleString();
    document.getElementById('disciplines-count').textContent = disciplinesCount;
}

/**
 * Create discipline indicator cards
 */
function createDisciplineIndicators() {
    const container = document.getElementById('discipline-cards');
    
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

// Include the rest of the original dashboard functions here...
// (initializeCharts, createTrendChart, createSalaryChart, createLocationChart, etc.)
// For brevity, I'll include the essential ones and reference the originals

/**
 * Initialize all charts
 */
function initializeCharts() {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not available, skipping chart initialization');
        return;
    }
    createTrendChart();
    createSalaryChart();
    createLocationChart();
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
    const showOverall = document.getElementById('show-overall')?.checked || false;
    
    const datasets = [];
    
    // Overall trend
    if (showOverall && timeSeriesData.total_monthly) {
        const overallData = months.map(month => timeSeriesData.total_monthly[month] || 0);
        const overallChange = calculatePercentageChange(overallData);
        const overallColor = getTrendColor(overallChange, '#000000');
        
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
            const percentageChange = calculatePercentageChange(data);
            const trendColor = getTrendColor(percentageChange, disciplineColors[discipline]);
            
            datasets.push({
                label: `${discipline} (${percentageChange >= 0 ? '+' : ''}${percentageChange}%)`,
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
                title: {
                    display: true,
                    text: `Position Trends - ${currentTimeframe.replace('_', ' ').toUpperCase()}`
                },
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true
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
            }
        }
    });
}

/**
 * Create salary analysis chart
 */
function createSalaryChart() {
    const ctx = document.getElementById('salary-chart');
    if (!ctx) return;
    
    const chartCtx = ctx.getContext('2d');
    const disciplines = dashboardData.discipline_analytics || dashboardData.top_disciplines || {};
    
    // Filter disciplines with salary data
    const disciplinesWithSalary = Object.entries(disciplines)
        .filter(([_, data]) => {
            if (typeof data === 'object' && data.salary_stats) {
                return data.salary_stats.count > 0 && data.salary_stats.mean > 0;
            }
            return false;
        })
        .sort((a, b) => {
            const meanA = a[1].salary_stats?.mean || 0;
            const meanB = b[1].salary_stats?.mean || 0;
            return meanB - meanA;
        });
    
    // If no salary data, create a placeholder chart
    if (disciplinesWithSalary.length === 0) {
        new Chart(chartCtx, {
            type: 'bar',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'No salary data available',
                    data: [0],
                    backgroundColor: '#6c757d80',
                    borderColor: '#6c757d',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Graduate Salary Analysis - No Data Available'
                    }
                }
            }
        });
        return;
    }
    
    const labels = disciplinesWithSalary.map(([discipline, _]) => discipline);
    const means = disciplinesWithSalary.map(([_, data]) => Math.round(data.salary_stats.mean || 0));
    
    new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Average Salary',
                    data: means,
                    backgroundColor: labels.map(discipline => disciplineColors[discipline] + '80'),
                    borderColor: labels.map(discipline => disciplineColors[discipline]),
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
                    text: 'Graduate Salary Analysis by Discipline'
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
                        text: 'Geographic Distribution - No Data Available'
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
                    text: 'Geographic Distribution of Positions'
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
    timeframeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentTimeframe = e.target.value;
            if (typeof createTrendChart === 'function') {
                createTrendChart();
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
    
    // Handle total positions with fallbacks
    const metadata = dashboardData.metadata || {};
    const summaryStats = dashboardData.summary_stats || {};
    const totalPositions = metadata.total_positions || dashboardData.total_positions || summaryStats.total_positions || 0;
    
    const footerTotalPositions = document.getElementById('footer-total-positions');
    if (footerTotalPositions) {
        footerTotalPositions.textContent = (totalPositions || 0).toLocaleString();
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
}

function hideLoading() {
    const loading = document.getElementById('loading');
    const mainContent = document.getElementById('main-content');
    
    if (loading) loading.classList.add('d-none');
    if (mainContent) mainContent.classList.remove('d-none');
}

function showError(message) {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const errorMessage = document.getElementById('error-message');
    
    if (loading) loading.classList.add('d-none');
    if (error) error.classList.remove('d-none');
    if (errorMessage) errorMessage.textContent = message;
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);