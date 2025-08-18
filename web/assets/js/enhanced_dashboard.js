/**
 * Enhanced Wildlife Jobs Dashboard
 * Implements discipline indicators, trend analysis, and CSV export functionality
 */

/**
 * Sanitize HTML content to prevent XSS attacks
 * @param {string} str - String to sanitize
 * @returns {string} - Escaped HTML string
 */
function escapeHTML(str) {
    if (typeof str !== 'string') return String(str);
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

let dashboardData = null;
let exportData = null;
let currentTimeframe = '1_month';
let currentTrendChart = null;

// Chart color scheme - exactly 5 categories
const disciplineColors = {
    'Fisheries Management and Conservation': '#4682B4',  // Ocean blue
    'Wildlife Management and Conservation': '#2E8B57',   // Forest green
    'Human Dimensions': '#CD853F',                       // Warm brown
    'Environmental Science': '#9932CC',                  // Purple
    'Other': '#708090'                                   // Slate gray
};

/**
 * Initialize the dashboard
 */
async function initDashboard() {
    try {
        showLoading();

        // Add modern loading animations
        addLoadingAnimations();

        // Try to load data files with better error handling
        try {
            // Load both enhanced data and export data
            const [enhancedResponse, exportResponse] = await Promise.all([
                fetch('data/enhanced_data.json').catch(() => {
                    console.log('Trying to load enhanced_data.json from data directory');
                    return fetch('./data/enhanced_data.json');
                }),
                fetch('data/export_data.json').catch(() => {
                    console.log('Trying to load export_data.json from data directory');
                    return fetch('./data/export_data.json');
                })
            ]);

            if (!enhancedResponse.ok) {
                throw new Error(`Enhanced data fetch failed: ${enhancedResponse.status} ${enhancedResponse.statusText}`);
            }
            if (!exportResponse.ok) {
                throw new Error(`Export data fetch failed: ${exportResponse.status} ${exportResponse.statusText}`);
            }

            dashboardData = await enhancedResponse.json();
            exportData = await exportResponse.json();

            console.log('Dashboard data loaded successfully:', {
                totalPositions: dashboardData.total_positions,
                exportRecords: exportData.length
            });

        } catch (fetchError) {
            console.error('Fetch error:', fetchError);

            // If fetch fails, show a helpful error message about CORS
            if (window.location.protocol === 'file:') {
                showError('CORS Error: Please serve this dashboard from a web server. Run: python3 -m http.server 8080 in the dashboard directory, then visit http://localhost:8080');
                return;
            } else {
                throw fetchError;
            }
        }

        // Initialize all components with staggered animations
        updateOverviewCards();
        createDisciplineIndicators();
        initializeCharts();
        setupEventListeners();
        updateFooter();

        // Add entrance animations and enhanced interactivity
        addEntranceAnimations();
        enhanceInteractivity();

        hideLoading();

    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showError(`Failed to load dashboard data: ${error.message}`);
    }
}

/**
 * Update overview summary cards
 */
function updateOverviewCards() {
    const overview = dashboardData.overview || {};

    // Safely access data with fallbacks
    const totalPositions = dashboardData.total_positions || 0;
    const gradPositions = overview.graduate_positions || dashboardData.graduate_assistantships || 0;
    const salaryPositions = overview.positions_with_salaries || 0;
    const disciplinesCount = overview.total_disciplines || 0;

    document.getElementById('total-jobs').textContent = totalPositions.toLocaleString();
    document.getElementById('grad-positions').textContent = gradPositions.toLocaleString();
    document.getElementById('salary-positions').textContent = salaryPositions.toLocaleString();
    document.getElementById('disciplines-count').textContent = disciplinesCount;
}

/**
 * Create discipline indicator cards
 */
function createDisciplineIndicators() {
    const container = document.getElementById('discipline-cards');
    const disciplines = dashboardData.top_disciplines;

    container.innerHTML = '';

    Object.entries(disciplines).forEach(([discipline, data]) => {
        const color = disciplineColors[discipline] || '#708090';
        const gradPositions = data.grad_positions || 0;
        const avgSalary = data.salary_stats.mean ? `$${Math.round(data.salary_stats.mean).toLocaleString()}` : 'N/A';

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
                                data-bs-title="All job postings in this discipline (includes graduate positions, internships, and professional roles)">
                                ${escapeHTML(data.total_positions)}
                            </h4>
                            <small class="text-muted">
                                <i class="fas fa-list me-1"></i>Total Postings
                            </small>
                        </div>
                        <div class="col-6 text-center">
                            <h4 class="text-success mb-0"
                                data-bs-toggle="tooltip"
                                data-bs-placement="top"
                                data-bs-title="Confirmed graduate assistantships, fellowships, and PhD/Masters positions only (excludes internships and professional jobs)">
                                ${escapeHTML(gradPositions)}
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
                               data-bs-title="Average salary for graduate positions in this discipline, adjusted to Lincoln, NE cost of living">
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
 * Initialize all charts
 */
function initializeCharts() {
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
    const ctx = document.getElementById('trend-chart').getContext('2d');
    const timeSeriesData = dashboardData.time_series[currentTimeframe];

    if (currentTrendChart) {
        currentTrendChart.destroy();
    }

    // Prepare data
    const months = Object.keys(timeSeriesData.total_monthly).sort();
    const showOverall = document.getElementById('show-overall').checked;

    const datasets = [];

    // Overall trend
    if (showOverall) {
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
    const disciplineData = timeSeriesData.discipline_monthly;
    Object.entries(disciplineData).forEach(([discipline, monthlyData]) => {
        if (dashboardData.top_disciplines[discipline]) { // Only show top disciplines
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

    currentTrendChart = new Chart(ctx, {
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
                        usePointStyle: true,
                        generateLabels: function(chart) {
                            const original = Chart.defaults.plugins.legend.labels.generateLabels;
                            const labels = original.call(this, chart);

                            // Color the legend text based on trend
                            labels.forEach((label, index) => {
                                const dataset = chart.data.datasets[index];
                                label.fillStyle = dataset.borderColor;
                                label.strokeStyle = dataset.borderColor;
                            });

                            return labels;
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
            }
        }
    });
}

/**
 * Create salary analysis chart
 */
function createSalaryChart() {
    const ctx = document.getElementById('salary-chart').getContext('2d');
    const disciplines = dashboardData.discipline_analytics;

    // Filter disciplines with salary data
    const disciplinesWithSalary = Object.entries(disciplines)
        .filter(([_, data]) => data.salary_stats.count > 0)
        .sort((a, b) => b[1].salary_stats.mean - a[1].salary_stats.mean);

    const labels = disciplinesWithSalary.map(([discipline, _]) => discipline);
    const means = disciplinesWithSalary.map(([_, data]) => Math.round(data.salary_stats.mean));
    const mins = disciplinesWithSalary.map(([_, data]) => Math.round(data.salary_stats.min));
    const maxs = disciplinesWithSalary.map(([_, data]) => Math.round(data.salary_stats.max));

    new Chart(ctx, {
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
                },
                {
                    label: 'Salary Range (Min)',
                    data: mins,
                    backgroundColor: 'rgba(255, 99, 132, 0.3)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1,
                    type: 'scatter',
                    pointRadius: 3
                },
                {
                    label: 'Salary Range (Max)',
                    data: maxs,
                    backgroundColor: 'rgba(54, 162, 235, 0.3)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1,
                    type: 'scatter',
                    pointRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Graduate Salary Analysis by Discipline (Lincoln, NE Adjusted)'
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
    const ctx = document.getElementById('location-chart').getContext('2d');
    const geographic = dashboardData.geographic_summary;

    const sortedRegions = Object.entries(geographic)
        .sort((a, b) => b[1] - a[1]);

    const labels = sortedRegions.map(([region, _]) => region);
    const data = sortedRegions.map(([_, count]) => count);

    const colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
    ];

    new Chart(ctx, {
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
            createTrendChart();
        });
    });

    // Show overall trend toggle
    document.getElementById('show-overall').addEventListener('change', () => {
        createTrendChart();
    });

    // Download buttons
    document.getElementById('download-json').addEventListener('click', downloadJSON);
    document.getElementById('download-csv').addEventListener('click', downloadCSV);
    document.getElementById('download-analytics').addEventListener('click', downloadAnalytics);

    // Initialize Bootstrap tooltips
    initializeTooltips();
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    // Initialize tooltips for existing elements
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
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

/**
 * Convert data to CSV format
 */
function convertToCSV(data) {
    if (!data || data.length === 0) return '';

    const headers = Object.keys(data[0]);
    const csvRows = [headers.join(',')];

    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            // Escape commas and quotes
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
        });
        csvRows.push(values.join(','));
    }

    return csvRows.join('\n');
}

/**
 * Download file helper
 */
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
    const lastUpdated = dashboardData.last_updated ?
        new Date(dashboardData.last_updated).toLocaleDateString() : 'Never';
    document.getElementById('footer-last-updated').innerHTML =
        `<i class="fas fa-clock me-2"></i>Last updated: ${lastUpdated}`;

    const totalPositions = dashboardData.total_positions || 0;
    document.getElementById('footer-total-positions').textContent =
        totalPositions.toLocaleString();
}

/**
 * UI Helper functions
 */
function showLoading() {
    document.getElementById('loading').classList.remove('d-none');
    document.getElementById('main-content').classList.add('d-none');
    document.getElementById('error').classList.add('d-none');
}

function hideLoading() {
    document.getElementById('loading').classList.add('d-none');
    document.getElementById('main-content').classList.remove('d-none');
}

function showError(message) {
    document.getElementById('loading').classList.add('d-none');
    document.getElementById('error').classList.remove('d-none');
    document.getElementById('error-message').textContent = message;
}

/**
 * Add modern loading animations
 */
function addLoadingAnimations() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.classList.add('fade-in');
    }
}

/**
 * Add entrance animations to dashboard elements
 */
function addEntranceAnimations() {
    // Animate stats cards with stagger
    const statsCards = document.querySelectorAll('.stats-card');
    statsCards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, index * 100);
    });

    // Animate chart containers
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach((container, index) => {
        setTimeout(() => {
            container.classList.add('scale-in');
        }, 500 + (index * 150));
    });

    // Animate discipline cards
    const disciplineCards = document.querySelectorAll('#discipline-cards .card');
    disciplineCards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('slide-in');
        }, 800 + (index * 50));
    });
}

/**
 * Enhanced chart creation with loading states
 */
function createChartWithLoading(chartId, createFunction) {
    const container = document.querySelector(`#${chartId}`).closest('.chart-container');
    if (container) {
        container.classList.add('loading-shimmer');

        setTimeout(() => {
            container.classList.remove('loading-shimmer');
            createFunction();
            container.classList.add('fade-in');
        }, 300);
    } else {
        createFunction();
    }
}

/**
 * Add hover effects to interactive elements
 */
function enhanceInteractivity() {
    // Add click feedback to buttons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 100);
        });
    });

    // Add hover effects to cards
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard);
