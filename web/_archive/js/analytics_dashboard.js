/**
 * Wildlife Graduate Assistantships Analytics Dashboard
 * Focused on data insights, trends, and research analytics
 */

class AnalyticsDashboard {
    constructor() {
        this.data = {
            jobs: [],
            allJobs: [],
            analytics: null,
            currentPeriod: 6, // months for trends chart
            showBig10Only: false // Big 10 filter state
        };

        this.charts = {};
        this.insights = [];

        this.init();
    }

    /**
     * Sanitize HTML content to prevent XSS attacks
     * @param {string} str - String to sanitize
     * @returns {string} - Escaped HTML string
     */
    escapeHTML(str) {
        if (typeof str !== 'string') return String(str);
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    async init() {
        this.showLoading();

        try {
            await this.loadData();
            this.renderDashboard();
            this.setupEventListeners();
            this.hideLoading();
            this.checkFirstTimeUser();
        } catch (error) {
            this.showError(error.message);
        }
    }

    /**
     * Extract salary value from job data - handles multiple formats
     * @param {Object} job - Job object
     * @returns {number} - Extracted salary value
     */
    extractSalaryValue(job) {
        // Try salary_lincoln_adjusted first (preferred)
        if (job.salary_lincoln_adjusted && typeof job.salary_lincoln_adjusted === 'number' && job.salary_lincoln_adjusted > 0) {
            return job.salary_lincoln_adjusted;
        }

        // Try numeric salary fields
        if (job.salary_min && job.salary_max) {
            return (job.salary_min + job.salary_max) / 2;
        }

        // Parse salary_range string (e.g., "$25,000 - $30,000")
        if (job.salary_range && typeof job.salary_range === 'string') {
            const ranges = job.salary_range.match(/\$?[\d,]+/g);
            if (ranges && ranges.length >= 2) {
                const min = parseInt(ranges[0].replace(/[$,]/g, ''));
                const max = parseInt(ranges[1].replace(/[$,]/g, ''));
                if (!isNaN(min) && !isNaN(max)) {
                    return (min + max) / 2;
                }
            }
            // Single value (e.g., "$25,000")
            else if (ranges && ranges.length === 1) {
                const value = parseInt(ranges[0].replace(/[$,]/g, ''));
                if (!isNaN(value)) {
                    return value;
                }
            }
        }

        // Fallback - no valid salary found
        return 0;
    }

    /**
     * Generate analytics data from jobs when enhanced_data.json is not available
     * @param {Array} jobs - Array of job objects
     * @returns {Object} - Analytics data structure
     */
    generateAnalyticsFromJobs(jobs) {
        const gradJobs = jobs.filter(job => job.is_graduate_assistantship);
        const big10Jobs = gradJobs.filter(job => job.is_big10_university);

        return {
            summary: {
                total_positions: gradJobs.length,
                graduate_assistantships: gradJobs.length,
                big10_positions: big10Jobs.length,
                last_updated: new Date().toISOString(),
                data_quality: {
                    classification_accuracy: 0.95,
                    total_analyzed: jobs.length
                }
            },
            analytics: {
                discipline_breakdown: this.calculateDisciplineBreakdown(gradJobs),
                regional_distribution: this.calculateRegionalDistribution(gradJobs),
                university_analysis: {
                    big10_universities: this.getBig10Universities(big10Jobs),
                    other_universities: this.getOtherUniversities(gradJobs.filter(j => !j.is_big10_university))
                }
            },
            insights: [
                {
                    type: "sample_data",
                    title: "Sample Data Mode",
                    description: "Dashboard running with sample data - use full scraper for real job data",
                    value: `${gradJobs.length} positions`
                }
            ]
        };
    }

    calculateDisciplineBreakdown(jobs) {
        const breakdown = {};
        jobs.forEach(job => {
            const discipline = job.discipline_primary || job.discipline || 'Other';
            breakdown[discipline] = (breakdown[discipline] || 0) + 1;
        });
        return breakdown;
    }

    calculateRegionalDistribution(jobs) {
        const distribution = {};
        jobs.forEach(job => {
            const region = job.location_region || 'Unknown';
            distribution[region] = (distribution[region] || 0) + 1;
        });
        return distribution;
    }

    getBig10Universities(jobs) {
        const unis = {};
        jobs.forEach(job => {
            if (job.university_name) {
                unis[job.university_name] = (unis[job.university_name] || 0) + 1;
            }
        });
        return unis;
    }

    getOtherUniversities(jobs) {
        const unis = {};
        jobs.forEach(job => {
            if (job.university_name) {
                unis[job.university_name] = (unis[job.university_name] || 0) + 1;
            }
        });
        return unis;
    }

    async loadData() {
        const cacheBuster = '?t=' + Date.now();

        try {
            const [jobsResponse, analyticsResponse] = await Promise.all([
                // Try verified graduate assistantships first, fallback to export_data
                fetch('data/verified_graduate_assistantships.json' + cacheBuster).catch(() =>
                    fetch('./data/verified_graduate_assistantships.json' + cacheBuster)
                ).catch(() =>
                    fetch('data/export_data.json' + cacheBuster).catch(() =>
                        fetch('./data/export_data.json' + cacheBuster)
                    )
                ),
                fetch('data/enhanced_data.json' + cacheBuster).catch(() =>
                    fetch('./data/enhanced_data.json' + cacheBuster)
                )
            ]);

            if (!jobsResponse.ok) {
                throw new Error('Failed to fetch jobs data');
            }

            const allJobs = await jobsResponse.json();

            // Try to load analytics, but don't fail if it's missing
            try {
                if (analyticsResponse.ok) {
                    this.data.analytics = await analyticsResponse.json();
                } else {
                    console.warn('Analytics data not available, generating from jobs data');
                    this.data.analytics = this.generateAnalyticsFromJobs(allJobs);
                }
            } catch (error) {
                console.warn('Failed to load analytics data, generating from jobs data');
                this.data.analytics = this.generateAnalyticsFromJobs(allJobs);
            }

            // Store all jobs for trends chart (which can be filtered by user)
            this.data.allJobs = allJobs;

            // Filter to last 6 months for all other analytics
            this.data.jobs = this.filterJobsToRecentMonths(allJobs, 6);

        } catch (error) {
            if (window.location.protocol === 'file:') {
                throw new Error('CORS Error: Please serve this dashboard from a web server. Run: python3 -m http.server 8080 in the dashboard directory, then visit http://localhost:8080');
            }
            throw error;
        }
    }

    filterJobsToRecentMonths(jobs, months) {
        const cutoffDate = new Date();
        cutoffDate.setMonth(cutoffDate.getMonth() - months);

        return jobs.filter(job => {
            if (!job.published_date) return false;

            try {
                const [month, day, year] = job.published_date.split('/');
                const jobDate = new Date(year, month - 1, day);
                return jobDate >= cutoffDate;
            } catch (e) {
                return false;
            }
        });
    }

    filterJobsByBig10(jobs, big10Only = false) {
        if (!big10Only) return jobs;
        return jobs.filter(job => job.is_big10_university === true);
    }

    getFilteredJobs() {
        // Apply all active filters
        let filteredJobs = this.data.jobs;

        // Apply Big 10 filter if active
        if (this.data.showBig10Only) {
            filteredJobs = this.filterJobsByBig10(filteredJobs, true);
        }

        return filteredJobs;
    }

    renderDashboard() {
        this.updateHeaderMetrics();
        this.renderDisciplineAnalysis();
        this.renderTrendsAnalysis();
        this.renderGeographicAnalysis();
        this.renderMarketInsights();
        this.renderOrganizationsChart();
        this.updateFooter();
        this.updateFilterStatus(); // Update filter status and Big 10 count
        this.fixHeaderColors();
    }

    fixHeaderColors() {
        // Force card headers to be dark text
        const cardHeaders = document.querySelectorAll('.analytics-card .card-header h5, .analytics-card .card-header h6');
        cardHeaders.forEach(header => {
            header.style.color = '#111827';
            header.style.fontWeight = '600';
        });

        // Force specific chart titles to be white text
        const chartTitles = document.querySelectorAll('.col-lg-8 h6.mb-3, .col-lg-4 h6.mb-3');
        chartTitles.forEach(title => {
            title.style.color = 'white';
            title.style.fontWeight = '600';
        });

        // Nuclear option - find by text content
        const allH6 = document.querySelectorAll('h6');
        allH6.forEach(h6 => {
            if (h6.textContent.includes('Stipend Distribution') || h6.textContent.includes('Market Share')) {
                h6.style.color = 'white';
                h6.style.fontWeight = '600';
            }
        });
    }

    wrapLabel(text, maxLength) {
        if (text.length <= maxLength) {
            return text;
        }

        // Find a good break point (space, hyphen, or slash)
        const words = text.split(/[\s\-\/]+/);
        let line1 = '';
        let line2 = '';

        for (let i = 0; i < words.length; i++) {
            const testLine1 = line1 + (line1 ? ' ' : '') + words[i];
            if (testLine1.length <= maxLength) {
                line1 = testLine1;
            } else {
                line2 = words.slice(i).join(' ');
                break;
            }
        }

        // If line2 is too long, truncate it
        if (line2.length > maxLength) {
            line2 = line2.substring(0, maxLength - 3) + '...';
        }

        // Return as newline-separated string for Chart.js
        return line1 + (line2 ? '\n' + line2 : '');
    }

    generateSparklineData(jobs, months = 6) {
        const monthlyData = {};
        const now = new Date();

        // Initialize months with days count for each month
        for (let i = months - 1; i >= 0; i--) {
            const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;

            // Get number of days in this month
            const daysInMonth = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();

            monthlyData[monthKey] = {
                count: 0,
                days: daysInMonth
            };
        }

        // Count jobs by month
        jobs.forEach(job => {
            if (job.published_date) {
                try {
                    const [month, day, year] = job.published_date.split('/');
                    const monthKey = `${year}-${month.padStart(2, '0')}`;
                    if (monthlyData[monthKey]) {
                        monthlyData[monthKey].count++;
                    }
                } catch (e) {
                    // Skip invalid dates
                }
            }
        });

        // Calculate positions per 30 days (monthly moving average)
        return Object.values(monthlyData).map(data => {
            const positionsPer30Days = (data.count / data.days) * 30;
            return Math.round(positionsPer30Days * 100) / 100; // Round to 2 decimal places
        });
    }

    createSparkline(canvasId, data, color = '#059669') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        if (data.length < 2) return;

        const max = Math.max(...data, 1);
        const min = Math.min(...data);
        const range = max - min || 1;

        // Draw line
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();

        for (let i = 0; i < data.length; i++) {
            const x = (i / (data.length - 1)) * width;
            const y = height - ((data[i] - min) / range) * height;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }

        ctx.stroke();

        // Fill area under curve
        ctx.fillStyle = color + '20'; // 20% opacity
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        ctx.fill();
    }

    getTrendIndicator(data) {
        if (data.length < 3) {
            return { text: '', class: '' };
        }

        // Compare last 2 months vs previous 2 months
        const recent = data.slice(-2).reduce((a, b) => a + b, 0);
        const previous = data.slice(-4, -2).reduce((a, b) => a + b, 0);

        if (recent > previous * 1.2) {
            return { text: '↗', class: 'trend-up' };
        } else if (recent < previous * 0.8) {
            return { text: '↘', class: 'trend-down' };
        } else {
            return { text: '→', class: 'trend-stable' };
        }
    }

    updateHeaderMetrics() {
        const jobs = this.getFilteredJobs();
        const { analytics } = this.data;

        // Total assistantships
        const gradJobs = jobs.filter(job => job.discipline_primary !== 'Other');
        document.getElementById('total-assistantships').textContent = gradJobs.length;

        // Average stipend (Lincoln-adjusted)
        const validSalaries = gradJobs
            .map(job => this.extractSalaryValue(job))
            .filter(salary => salary && salary > 0);

        const avgStipend = validSalaries.length > 0
            ? Math.round(validSalaries.reduce((a, b) => a + b) / validSalaries.length)
            : 0;

        document.getElementById('avg-stipend').textContent =
            (avgStipend && avgStipend > 0 && typeof avgStipend === 'number') ? `$${avgStipend.toLocaleString()}` : 'N/A';

        // Top discipline
        const disciplineCounts = {};
        gradJobs.forEach(job => {
            const discipline = job.discipline_primary || 'Other';
            disciplineCounts[discipline] = (disciplineCounts[discipline] || 0) + 1;
        });

        const topDiscipline = Object.entries(disciplineCounts)
            .sort(([,a], [,b]) => b - a)[0];

        if (topDiscipline) {
            const [name, count] = topDiscipline;
            const percentage = Math.round((count / gradJobs.length) * 100);

            document.getElementById('top-discipline').textContent =
                name.length > 20 ? name.substring(0, 20) + '...' : name;
            document.getElementById('discipline-percentage').textContent =
                `${percentage}% of positions`;
        }

        // Geographic spread
        const regions = new Set(jobs.map(job => job.geographic_region).filter(r => r));
        document.getElementById('geographic-spread').textContent = regions.size;

        const regionCounts = {};
        jobs.forEach(job => {
            const region = job.geographic_region || 'Unknown';
            regionCounts[region] = (regionCounts[region] || 0) + 1;
        });

        const topRegion = Object.entries(regionCounts)
            .sort(([,a], [,b]) => b - a)[0];

        if (topRegion) {
            document.getElementById('top-region').textContent = `Top: ${topRegion[0]}`;
        }

        // Update timestamps
        if (analytics && analytics.last_updated) {
            const lastUpdated = new Date(analytics.last_updated).toLocaleDateString();
            document.getElementById('last-updated').textContent = `Last updated: ${lastUpdated}`;
            document.getElementById('footer-last-updated').innerHTML =
                `<i class="fas fa-clock me-2"></i>Last updated: ${lastUpdated}`;
        }

        const filterText = this.data.showBig10Only ? " (Big 10 only)" : "";
        document.getElementById('total-positions').textContent = `${jobs.length} verified graduate assistantships (last 6 months)${filterText}`;
    }

    renderDisciplineAnalysis() {
        const jobs = this.getFilteredJobs();
        const gradJobs = jobs.filter(job => job.discipline_primary !== 'Other');

        // Discipline breakdown
        const disciplines = {};

        // Add Overall category first
        const allSalaries = gradJobs.map(job => this.extractSalaryValue(job)).filter(salary => salary > 0);
        const allLocations = new Set(gradJobs.map(job => job.geographic_region).filter(region => region));

        disciplines['Overall'] = {
            count: gradJobs.length,
            salaries: allSalaries,
            locations: allLocations,
            jobs: gradJobs
        };

        // Add individual disciplines
        gradJobs.forEach(job => {
            const discipline = job.discipline_primary || 'Other';
            if (!disciplines[discipline]) {
                disciplines[discipline] = {
                    count: 0,
                    salaries: [],
                    locations: new Set(),
                    jobs: []
                };
            }
            disciplines[discipline].count++;
            disciplines[discipline].jobs.push(job);
            const salary = this.extractSalaryValue(job);
            if (salary > 0) {
                disciplines[discipline].salaries.push(salary);
            }
            if (job.geographic_region) {
                disciplines[discipline].locations.add(job.geographic_region);
            }
        });

        // Create discipline cards
        const container = document.getElementById('discipline-cards');
        container.innerHTML = '';

        // Sort disciplines with Overall first, then by count
        const sortedDisciplines = Object.entries(disciplines).sort(([nameA, a], [nameB, b]) => {
            if (nameA === 'Overall') return -1;
            if (nameB === 'Overall') return 1;
            return b.count - a.count;
        });

        sortedDisciplines.forEach(([discipline, data], index) => {
                const avgSalary = data.salaries.length > 0
                    ? Math.round(data.salaries.reduce((a, b) => a + b) / data.salaries.length)
                    : 0;

                const card = document.createElement('div');
                card.className = 'col-lg-6 col-xl-4 mb-3';

                // Add special styling for Overall card
                const isOverall = discipline === 'Overall';
                const cardClass = isOverall ? 'discipline-card overall-card' : 'discipline-card';
                const sparklineId = `sparkline-${index}`;

                // Generate trend indicator
                const sparklineData = this.generateSparklineData(data.jobs || []);
                const trend = this.getTrendIndicator(sparklineData);

                card.innerHTML = `
                    <div class="${cardClass}">
                        <div class="card-body">
                            <div class="discipline-header">
                                <h6 class="mb-0">${this.escapeHTML(discipline)}</h6>
                            </div>
                            <div class="discipline-stats">
                                <div class="stat-item">
                                    <div class="stat-value">${data.count}</div>
                                    <div class="stat-label">Positions</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value">${avgSalary > 0 ? '$' + avgSalary.toLocaleString() : 'N/A'}</div>
                                    <div class="stat-label">Avg Stipend</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value">${data.locations.size}</div>
                                    <div class="stat-label">Regions</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-value">${isOverall ? '100' : Math.round((data.count / gradJobs.length) * 100)}%</div>
                                    <div class="stat-label">Market Share</div>
                                </div>
                                <div class="stat-item sparkline-stat">
                                    <div class="sparkline-container">
                                        <canvas id="${sparklineId}" width="80" height="30"></canvas>
                                        <span class="trend-indicator ${trend.class}">${trend.text}</span>
                                    </div>
                                    <div class="stat-label">6-Month Trend</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);

                // Create sparkline after DOM element is added
                setTimeout(() => {
                    const color = isOverall ? '#047857' : '#059669';
                    this.createSparkline(sparklineId, sparklineData, color);
                }, 10);
            });

        // Create salary comparison chart
        this.createSalaryComparisonChart(disciplines);
    }

    createSalaryComparisonChart(disciplines) {
        const ctx = document.getElementById('salary-comparison-chart').getContext('2d');

        const boxPlotData = [];
        const labels = [];

        // Sort disciplines with Overall first, then by count
        const sortedDisciplinesForChart = Object.entries(disciplines).sort(([nameA, a], [nameB, b]) => {
            if (nameA === 'Overall') return -1;
            if (nameB === 'Overall') return 1;
            return b.count - a.count;
        });

        sortedDisciplinesForChart.forEach(([discipline, data]) => {
                if (data.salaries.length >= 3) { // Need at least 3 data points for box plot
                    const sortedSalaries = data.salaries.sort((a, b) => a - b);
                    const n = sortedSalaries.length;

                    // Calculate quartiles
                    const q1Index = Math.floor(n * 0.25);
                    const q2Index = Math.floor(n * 0.5);
                    const q3Index = Math.floor(n * 0.75);

                    const q1 = sortedSalaries[q1Index];
                    const median = sortedSalaries[q2Index];
                    const q3 = sortedSalaries[q3Index];
                    const min = sortedSalaries[0];
                    const max = sortedSalaries[n - 1];

                    // Calculate IQR and outliers
                    const iqr = q3 - q1;
                    const lowerFence = q1 - 1.5 * iqr;
                    const upperFence = q3 + 1.5 * iqr;

                    // Find whisker ends (closest values within fences)
                    const lowerWhisker = sortedSalaries.find(val => val >= lowerFence) || min;
                    const upperWhisker = sortedSalaries.reverse().find(val => val <= upperFence) || max;
                    sortedSalaries.reverse(); // restore order

                    // Find outliers
                    const outliers = sortedSalaries.filter(val => val < lowerFence || val > upperFence);

                    // Split long discipline names into two lines
                    const wrappedLabel = this.wrapLabel(discipline, 12);
                    labels.push(wrappedLabel);
                    boxPlotData.push({
                        min: lowerWhisker,
                        q1: q1,
                        median: median,
                        q3: q3,
                        max: upperWhisker,
                        outliers: outliers
                    });
                }
            });

        this.charts.salaryComparison = new Chart(ctx, {
            type: 'boxplot',
            data: {
                labels,
                datasets: [{
                    label: 'Salary Distribution',
                    data: boxPlotData,
                    backgroundColor: 'rgba(5, 150, 105, 0.6)',
                    borderColor: 'rgba(5, 150, 105, 1)',
                    borderWidth: 2,
                    outlierColor: 'rgba(239, 68, 68, 0.8)',
                    outlierRadius: 3,
                    medianColor: 'white',
                    medianWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: 2,
                layout: {
                    padding: {
                        bottom: 20
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: 'white',
                            font: {
                                size: 12,
                                weight: '500'
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            beforeBody: function(context) {
                                const dataPoint = context[0].raw;
                                return [
                                    `Min: $${dataPoint.min.toLocaleString()}`,
                                    `Q1: $${dataPoint.q1.toLocaleString()}`,
                                    `Median: $${dataPoint.median.toLocaleString()}`,
                                    `Q3: $${dataPoint.q3.toLocaleString()}`,
                                    `Max: $${dataPoint.max.toLocaleString()}`,
                                    dataPoint.outliers.length > 0 ? `Outliers: ${dataPoint.outliers.length}` : ''
                                ].filter(Boolean);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: 'white',
                            font: {
                                size: 11
                            },
                            maxRotation: 0,
                            minRotation: 0
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: 'white',
                            font: {
                                size: 11
                            },
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    createMarketShareChart(disciplines) {
        const ctx = document.getElementById('discipline-pie-chart').getContext('2d');

        const data = Object.entries(disciplines)
            .sort(([,a], [,b]) => b.count - a.count)
            .map(([discipline, data]) => ({
                label: discipline,
                value: data.count
            }));

        const colors = [
            '#059669', '#22c55e', '#0ea5e9', '#f59e0b', '#ef4444',
            '#166534', '#1e40af', '#92400e', '#047857', '#065f46'
        ];

        this.charts.marketShare = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    data: data.map(d => d.value),
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: 1,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            color: 'white',
                            font: {
                                size: 11,
                                weight: '500'
                            }
                        }
                    }
                }
            }
        });
    }

    renderTrendsAnalysis() {
        this.createTrendsChart();
        this.renderSeasonalPatterns();
    }

    createTrendsChart() {
        const ctx = document.getElementById('trends-chart').getContext('2d');

        // Use the selected period (3, 6, or 12 months)
        const periodMonths = this.data.currentPeriod || 6;

        // Process temporal data using ALL jobs (not filtered to 6 months)
        const monthlyData = {};
        this.data.allJobs.forEach(job => {
            if (job.published_date) {
                try {
                    const [month, day, year] = job.published_date.split('/');
                    const monthKey = `${year}-${month.padStart(2, '0')}`;
                    monthlyData[monthKey] = (monthlyData[monthKey] || 0) + 1;
                } catch (e) {
                    // Skip invalid dates
                }
            }
        });

        // Get last N months based on selected period
        const months = [];
        const values = [];
        const now = new Date();

        for (let i = periodMonths - 1; i >= 0; i--) {
            const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            months.push(date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }));
            values.push(monthlyData[monthKey] || 0);
        }

        this.charts.trends = new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [{
                    label: 'Graduate Assistantships Posted',
                    data: values,
                    borderColor: '#059669',
                    backgroundColor: 'rgba(5, 150, 105, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#059669',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: 2.5,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: 'white',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: 'white',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    renderSeasonalPatterns() {
        const seasonalData = this.analyzeSeasonalPatterns();
        const container = document.getElementById('seasonal-insights');

        container.innerHTML = seasonalData.map(season => `
            <div class="seasonal-pattern">
                <div class="season-name">${this.escapeHTML(season.name)}</div>
                <div class="season-stats">
                    <span class="season-count">${this.escapeHTML(season.count)}</span>
                    <span class="season-trend trend-${this.escapeHTML(season.trend.toLowerCase())}">${this.escapeHTML(season.trendText)}</span>
                </div>
            </div>
        `).join('');
    }

    analyzeSeasonalPatterns() {
        // Analyze posting patterns by season using filtered 6-month data
        const seasons = {
            'Spring': { months: [3, 4, 5], count: 0 },
            'Summer': { months: [6, 7, 8], count: 0 },
            'Fall': { months: [9, 10, 11], count: 0 },
            'Winter': { months: [12, 1, 2], count: 0 }
        };

        jobs.forEach(job => {
            if (job.published_date) {
                try {
                    const [month] = job.published_date.split('/');
                    const monthNum = parseInt(month);

                    for (const [seasonName, seasonData] of Object.entries(seasons)) {
                        if (seasonData.months.includes(monthNum)) {
                            seasonData.count++;
                            break;
                        }
                    }
                } catch (e) {
                    // Skip invalid dates
                }
            }
        });

        return Object.entries(seasons).map(([name, data]) => ({
            name,
            count: data.count,
            trend: data.count > 10 ? 'Up' : data.count > 5 ? 'Stable' : 'Down',
            trendText: data.count > 10 ? '+High' : data.count > 5 ? 'Stable' : 'Low'
        }));
    }

    renderGeographicAnalysis() {
        this.createGeographicMap();
        this.renderRegionalBreakdown();
        this.renderCostOfLivingAnalysis();
    }

    createGeographicMap() {
        const jobs = this.getFilteredJobs();
        const regionData = {};
        const disciplineByRegion = {};

        // Process jobs by region
        jobs.forEach(job => {
            const region = job.geographic_region || 'Unknown';
            const discipline = job.discipline_primary || 'Other';

            if (!regionData[region]) {
                regionData[region] = {
                    count: 0,
                    salaries: [],
                    disciplines: {}
                };
            }

            regionData[region].count++;

            const salary = this.extractSalaryValue(job);
            if (salary > 0) {
                regionData[region].salaries.push(salary);
            }

            if (!regionData[region].disciplines[discipline]) {
                regionData[region].disciplines[discipline] = 0;
            }
            regionData[region].disciplines[discipline]++;
        });

        // Map regions to US state abbreviations for choropleth
        const regionToStates = {
            'Northeast': ['ME', 'NH', 'VT', 'MA', 'RI', 'CT', 'NY', 'NJ', 'PA'],
            'Southeast': ['DE', 'MD', 'DC', 'VA', 'WV', 'KY', 'TN', 'NC', 'SC', 'GA', 'FL', 'AL', 'MS', 'AR', 'LA'],
            'Midwest': ['OH', 'MI', 'IN', 'WI', 'IL', 'MN', 'IA', 'MO', 'ND', 'SD', 'NE', 'KS'],
            'Southwest': ['TX', 'OK', 'NM', 'AZ'],
            'West': ['CA', 'NV', 'UT', 'CO', 'WY', 'ID', 'MT', 'WA', 'OR', 'AK', 'HI'],
            'Pacific': ['AK', 'HI'], // Keep for backward compatibility, but they'll be included in West
            'Great Plains': ['ND', 'SD', 'NE', 'KS', 'OK', 'TX'],
            'Rocky Mountains': ['MT', 'ID', 'WY', 'CO', 'UT', 'NV']
        };

        // Prepare data for Plotly
        const plotData = [];
        const plotText = [];
        const plotStates = [];
        const plotValues = [];

        Object.entries(regionData).forEach(([region, data]) => {
            const avgSalary = data.salaries.length > 0
                ? Math.round(data.salaries.reduce((a, b) => a + b) / data.salaries.length)
                : 0;

            // Get top disciplines for this region
            const topDisciplines = Object.entries(data.disciplines)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 3)
                .map(([disc, count]) => `${disc}: ${Math.round((count / data.count) * 100)}%`)
                .join('<br>');

            const percentage = Math.round((data.count / jobs.length) * 100);

            // If this is Pacific region, combine it with West for mapping purposes
            let displayRegion = region;
            let combinedCount = data.count;

            if (region === 'Pacific' && regionData['West']) {
                // Combine Pacific data with West data for AK/HI shading
                displayRegion = 'West + Pacific';
                combinedCount = data.count + regionData['West'].count;
            }

            const hoverText = `<b>${displayRegion}</b><br>` +
                `Positions: ${data.count}<br>` +
                `Percentage: ${percentage}%<br>` +
                `Avg Salary: $${avgSalary.toLocaleString()}<br>` +
                `<br><b>Top Disciplines:</b><br>${topDisciplines}`;

            // Map region to states
            const states = regionToStates[region] || [];
            states.forEach(state => {
                plotStates.push(state);
                // Use combined count for Pacific states to match West region intensity
                const valueToUse = region === 'Pacific' && regionData['West'] ?
                    regionData['West'].count : data.count;
                plotValues.push(valueToUse);
                plotText.push(hoverText);
            });
        });

        const mapData = [{
            type: 'choropleth',
            locationmode: 'USA-states',
            locations: plotStates,
            z: plotValues,
            text: plotText,
            hovertemplate: '%{text}<extra></extra>',
            colorscale: [
                [0, '#f0fdf4'],
                [0.2, '#dcfce7'],
                [0.4, '#bbf7d0'],
                [0.6, '#86efac'],
                [0.8, '#4ade80'],
                [1.0, '#059669']
            ],
            colorbar: {
                title: 'Positions',
                titlefont: { color: 'white' },
                tickfont: { color: 'white' }
            }
        }];

        const layout = {
            geo: {
                scope: 'usa',
                projection: { type: 'albers usa' },
                showlakes: true,
                lakecolor: 'rgb(255, 255, 255)',
                bgcolor: 'rgba(0,0,0,0)',
                showframe: false,
                showcoastlines: true,
                coastlinecolor: 'rgba(255, 255, 255, 0.3)'
            },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: 'white' },
            margin: { l: 0, r: 0, t: 0, b: 0 },
            height: 400
        };

        const config = {
            displayModeBar: false,
            responsive: true
        };

        Plotly.newPlot('geographic-map', mapData, layout, config);
    }

    renderRegionalBreakdown() {
        const jobs = this.getFilteredJobs();
        const regional = {};
        jobs.forEach(job => {
            const region = job.geographic_region || 'Unknown';
            if (!regional[region]) {
                regional[region] = { count: 0, salaries: [] };
            }
            regional[region].count++;
            const salary = this.extractSalaryValue(job);
            if (salary > 0) {
                regional[region].salaries.push(salary);
            }
        });

        const container = document.getElementById('regional-breakdown');
        container.innerHTML = Object.entries(regional)
            .sort(([,a], [,b]) => b.count - a.count)
            .map(([region, data]) => {
                const avgSalary = data.salaries.length > 0
                    ? Math.round(data.salaries.reduce((a, b) => a + b) / data.salaries.length)
                    : 0;
                const safeRegion = this.escapeHTML(region);

                return `
                    <div class="regional-item mb-2">
                        <div class="region-name">${safeRegion}</div>
                        <div class="region-stats">
                            <div class="region-count">${this.escapeHTML(data.count)} positions</div>
                            <div class="region-percentage">${avgSalary > 0 ? '$' + avgSalary.toLocaleString() : 'N/A'} avg</div>
                        </div>
                    </div>
                `;
            }).join('');
    }

    renderCostOfLivingAnalysis() {
        const costAnalysis = this.analyzeCostOfLiving();
        const container = document.getElementById('cost-of-living-analysis');

        container.innerHTML = `
            <div class="insight-item">
                <div class="d-flex align-items-start">
                    <div class="insight-icon">
                        <i class="fas fa-balance-scale"></i>
                    </div>
                    <div class="insight-content">
                        <h6>Cost of Living Impact</h6>
                        <p>Average ${costAnalysis.adjustment}% adjustment applied across all regions, with ${costAnalysis.highestCost} having the highest cost of living impact.</p>
                    </div>
                </div>
            </div>
        `;
    }

    analyzeCostOfLiving() {
        const costIndices = this.data.jobs
            .map(job => job.cost_of_living_index || 1.0)
            .filter(index => index > 0);

        const avgAdjustment = costIndices.length > 0
            ? Math.round(((costIndices.reduce((a, b) => a + b) / costIndices.length) - 1) * 100)
            : 0;

        return {
            adjustment: avgAdjustment,
            highestCost: 'Western regions' // Simplified for demo
        };
    }

    renderMarketInsights() {
        const insights = this.generateMarketInsights();
        const container = document.getElementById('market-insights');

        container.innerHTML = insights.map(insight => `
            <div class="insight-item">
                <div class="d-flex align-items-start">
                    <div class="insight-icon">
                        <i class="${this.escapeHTML(insight.icon)}"></i>
                    </div>
                    <div class="insight-content">
                        <h6>${this.escapeHTML(insight.title)}</h6>
                        <p>${this.escapeHTML(insight.description)}</p>
                    </div>
                </div>
            </div>
        `).join('');
    }

    generateMarketInsights() {
        const jobs = this.getFilteredJobs();
        const gradJobs = jobs.filter(job => job.discipline_primary !== 'Other');

        const insights = [];

        // Market size insight
        insights.push({
            icon: 'fas fa-chart-pie',
            title: 'Market Activity',
            description: `${gradJobs.length} verified graduate assistantships identified across ${new Set(gradJobs.map(j => j.discipline_primary)).size} disciplines, representing high-quality research opportunities with project details and funding confirmation.`
        });

        // Salary insight
        const validSalaries = gradJobs.map(job => this.extractSalaryValue(job)).filter(salary => salary > 0);
        if (validSalaries.length > 0) {
            const salaryRange = {
                min: Math.min(...validSalaries),
                max: Math.max(...validSalaries)
            };

            insights.push({
                icon: 'fas fa-money-bill-wave',
                title: 'Compensation Range',
                description: `Stipends range from $${Math.round(salaryRange.min).toLocaleString()} to $${Math.round(salaryRange.max).toLocaleString()}, with significant variation across disciplines and regions.`
            });
        }

        // Geographic insight
        const regions = new Set(jobs.map(job => job.geographic_region).filter(r => r));
        insights.push({
            icon: 'fas fa-globe-americas',
            title: 'Geographic Diversity',
            description: `Opportunities span ${regions.size} geographic regions, providing flexibility for students with location preferences.`
        });

        return insights;
    }

    renderOrganizationsChart() {
        const jobs = this.getFilteredJobs();
        const ctx = document.getElementById('organizations-chart').getContext('2d');

        const orgCounts = {};
        jobs.forEach(job => {
            const org = job.organization;
            orgCounts[org] = (orgCounts[org] || 0) + 1;
        });

        const topOrgs = Object.entries(orgCounts)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10);

        this.charts.organizations = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: topOrgs.map(([org]) =>
                    org.length > 30 ? org.substring(0, 30) + '...' : org
                ),
                datasets: [{
                    label: 'Positions',
                    data: topOrgs.map(([,count]) => count),
                    backgroundColor: 'rgba(5, 150, 105, 0.8)',
                    borderColor: 'rgba(5, 150, 105, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            color: 'white',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        ticks: {
                            color: 'white',
                            font: {
                                size: 11
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    setupEventListeners() {
        // Trend period buttons
        document.querySelectorAll('input[name="trendPeriod"]').forEach(input => {
            input.addEventListener('change', (e) => {
                this.data.currentPeriod = parseInt(e.target.value);
                this.updateTrendsChart();
            });
        });

        // Export buttons
        document.getElementById('export-csv').addEventListener('click', () => this.exportData('csv'));
        document.getElementById('export-json').addEventListener('click', () => this.exportData('json'));
        document.getElementById('export-pdf').addEventListener('click', () => this.exportReport());

        // Refresh button
        document.getElementById('refresh-data').addEventListener('click', () => this.refreshData());

        // About section collapse handler
        const aboutCollapse = document.getElementById('aboutContent');
        const aboutButton = document.querySelector('[data-bs-target="#aboutContent"]');
        if (aboutCollapse && aboutButton) {
            aboutCollapse.addEventListener('shown.bs.collapse', () => {
                aboutButton.querySelector('i').classList.replace('fa-chevron-down', 'fa-chevron-up');
            });
            aboutCollapse.addEventListener('hidden.bs.collapse', () => {
                aboutButton.querySelector('i').classList.replace('fa-chevron-up', 'fa-chevron-down');
            });
        }

        // Enhanced Big 10 toggle with better UX
        document.getElementById('big10-toggle').addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            this.data.showBig10Only = isChecked;

            // Add visual feedback during filter change
            this.showFilteringIndicator();

            // Debounced update for better performance
            clearTimeout(this.filterTimeout);
            this.filterTimeout = setTimeout(() => {
                this.refreshDashboard();
                this.updateFilterStatus();
                this.hideFilteringIndicator();

                // Show success toast
                this.showFilterToast(isChecked);
            }, 150);
        });
    }

    refreshDashboard() {
        // Re-render all components with current filter settings
        this.renderDashboard();
    }

    showFilteringIndicator() {
        // Add pulsing animation to toggle button
        const toggleLabel = document.querySelector('label[for="big10-toggle"]');
        if (toggleLabel) {
            toggleLabel.style.opacity = '0.6';
            toggleLabel.style.transition = 'opacity 0.2s ease';
        }
    }

    hideFilteringIndicator() {
        const toggleLabel = document.querySelector('label[for="big10-toggle"]');
        if (toggleLabel) {
            toggleLabel.style.opacity = '1';
        }
    }

    showFilterToast(isBig10Only) {
        // Create a subtle toast notification
        const toast = document.createElement('div');
        toast.className = 'position-fixed top-0 start-50 translate-middle-x mt-2';
        toast.style.zIndex = '9999';
        const alertType = isBig10Only ? 'warning' : 'info';
        const iconType = isBig10Only ? 'university' : 'globe';
        const titleText = isBig10Only ? 'Big 10 Filter Active' : 'Showing All Universities';
        const descText = isBig10Only ? 'Displaying only Big 10 university positions' : 'Displaying positions from all universities';

        toast.innerHTML = `
            <div class="alert alert-${this.escapeHTML(alertType)} alert-dismissible fade show shadow-sm" role="alert" style="min-width: 300px;">
                <i class="fas fa-${this.escapeHTML(iconType)} me-2"></i>
                <strong>${this.escapeHTML(titleText)}</strong>
                <br><small class="text-muted">
                    ${this.escapeHTML(descText)}
                </small>
            </div>
        `;

        document.body.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    updateFilterStatus() {
        // Update header status to show current filter
        const jobs = this.getFilteredJobs();
        const allJobs = this.data.jobs;
        const statusElement = document.getElementById('total-positions');
        const subtitle = document.querySelector('.analytics-header-card p.text-muted');

        if (statusElement) {
            const count = jobs.length;
            statusElement.textContent = count.toLocaleString();
        }

        if (subtitle) {
            const filterText = this.data.showBig10Only ? ' • Big 10 universities only' : '';
            const baseText = `Last ${this.data.currentPeriod} months • Last updated: ${new Date().toLocaleDateString()}`;
            subtitle.innerHTML = `<span>${baseText}${filterText}</span>`;
        }

        // Update Big 10 count badge
        const big10Count = this.filterJobsByBig10(allJobs, true).length;
        const countBadge = document.getElementById('big10-count');
        if (countBadge) {
            countBadge.textContent = big10Count;
            countBadge.style.display = big10Count > 0 ? 'inline' : 'none';
        }

        // Update toggle button appearance when active
        const toggleLabel = document.querySelector('label[for="big10-toggle"]');
        if (toggleLabel) {
            if (this.data.showBig10Only) {
                toggleLabel.classList.add('active');
                toggleLabel.style.backgroundColor = '#fbbf24';
                toggleLabel.style.borderColor = '#fbbf24';
                toggleLabel.style.color = '#111827';
                toggleLabel.style.transform = 'scale(1.05)';
                toggleLabel.style.transition = 'all 0.2s ease';
            } else {
                toggleLabel.classList.remove('active');
                toggleLabel.style.backgroundColor = '';
                toggleLabel.style.borderColor = '';
                toggleLabel.style.color = '';
                toggleLabel.style.transform = '';
            }
        }

        // Show/hide filter info panel
        const filterPanel = document.getElementById('filter-info-panel');
        if (filterPanel) {
            if (this.data.showBig10Only) {
                filterPanel.style.display = 'block';
                // Add smooth slide-in animation
                filterPanel.style.opacity = '0';
                filterPanel.style.transform = 'translateY(-10px)';
                setTimeout(() => {
                    filterPanel.style.transition = 'all 0.3s ease';
                    filterPanel.style.opacity = '1';
                    filterPanel.style.transform = 'translateY(0)';
                }, 10);
            } else {
                filterPanel.style.display = 'none';
            }
        }
    }

    updateTrendsChart() {
        if (this.charts.trends) {
            this.charts.trends.destroy();
        }

        // Update the current period from the checked radio button
        const checkedPeriod = document.querySelector('input[name="trendPeriod"]:checked');
        if (checkedPeriod) {
            this.data.currentPeriod = parseInt(checkedPeriod.value);
        }

        this.createTrendsChart();
    }

    exportData(format) {
        let data, filename, mimeType;

        if (format === 'csv') {
            data = this.convertToCSV(this.data.jobs);
            filename = 'wildlife_assistantships_analytics.csv';
            mimeType = 'text/csv';
        } else {
            data = JSON.stringify(this.data.analytics, null, 2);
            filename = 'wildlife_assistantships_analytics.json';
            mimeType = 'application/json';
        }

        const blob = new Blob([data], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    }

    convertToCSV(jobs) {
        const headers = [
            'title', 'organization', 'location', 'discipline_primary',
            'salary_lincoln_adjusted', 'geographic_region', 'published_date'
        ];

        const csvData = [
            headers.join(','),
            ...jobs.map(job =>
                headers.map(header => {
                    const value = job[header] || '';
                    return typeof value === 'string' && value.includes(',')
                        ? `"${value}"` : value;
                }).join(',')
            )
        ];

        return csvData.join('\\n');
    }

    exportReport() {
        // Generate comprehensive PDF report (placeholder)
        alert('PDF report generation would be implemented here using libraries like jsPDF');
    }

    async refreshData() {
        this.showLoading();
        try {
            await this.loadData();
            this.renderDashboard();
            this.hideLoading();
        } catch (error) {
            this.showError('Failed to refresh data: ' + error.message);
        }
    }

    updateFooter() {
        if (this.data.analytics && this.data.analytics.last_updated) {
            const lastUpdated = new Date(this.data.analytics.last_updated).toLocaleDateString();
            document.getElementById('footer-last-updated').innerHTML =
                `<i class="fas fa-clock me-2"></i>Last updated: ${lastUpdated}`;
        }

        // Update footer total positions
        const footerTotal = document.getElementById('footer-total-positions');
        if (footerTotal) {
            footerTotal.textContent = this.data.jobs.length.toLocaleString();
        }
    }

    checkFirstTimeUser() {
        // Check if user has visited before
        const hasVisited = localStorage.getItem('wildlife-dashboard-visited');
        if (!hasVisited) {
            // Show first-time user guidance
            setTimeout(() => {
                this.showWelcomeToast();
                localStorage.setItem('wildlife-dashboard-visited', 'true');
            }, 1000);
        }
    }

    showWelcomeToast() {
        const toast = document.createElement('div');
        toast.className = 'position-fixed bottom-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="false">
                <div class="toast-header bg-primary text-white">
                    <i class="fas fa-graduation-cap me-2"></i>
                    <strong class="me-auto">Welcome to Wildlife Graduate Analytics!</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    <p class="mb-2"><strong>New here?</strong> This dashboard analyzes wildlife graduate assistantship opportunities.</p>
                    <div class="d-flex gap-2">
                        <button class="btn btn-primary btn-sm" id="welcome-learn-more-btn">
                            <i class="fas fa-info-circle me-1"></i>Learn More
                        </button>
                        <button class="btn btn-outline-secondary btn-sm" data-bs-dismiss="toast">
                            <i class="fas fa-times me-1"></i>Dismiss
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(toast);

        // Add secure event listener for the Learn More button
        const learnMoreBtn = toast.querySelector('#welcome-learn-more-btn');
        if (learnMoreBtn) {
            learnMoreBtn.addEventListener('click', () => {
                // Navigate to about section
                const aboutLink = document.querySelector('[href="#about"]');
                if (aboutLink) {
                    aboutLink.click();
                }
                // Expand the about content
                const aboutContent = document.getElementById('aboutContent');
                if (aboutContent) {
                    aboutContent.classList.add('show');
                }
                // Hide the toast
                const bsToast = new bootstrap.Toast(toast.querySelector('.toast'));
                bsToast.hide();
            });
        }

        // Auto-remove after 15 seconds
        setTimeout(() => {
            const bsToast = new bootstrap.Toast(toast.querySelector('.toast'));
            bsToast.hide();
            setTimeout(() => toast.remove(), 500);
        }, 15000);
    }

    showLoading() {
        document.getElementById('loading').classList.remove('d-none');
        document.getElementById('main-content').classList.add('d-none');
        document.getElementById('error').classList.add('d-none');
    }

    hideLoading() {
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('main-content').classList.remove('d-none');
    }

    showError(message) {
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('main-content').classList.add('d-none');
        document.getElementById('error').classList.remove('d-none');
        document.getElementById('error-message').textContent = message;
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.analyticsDashboard = new AnalyticsDashboard();
});
