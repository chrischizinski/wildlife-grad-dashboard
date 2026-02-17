/**
 * Wildlife Dashboard - Chart Configuration
 * Centralized chart settings and utilities
 */

window.WildlifeDashboard = window.WildlifeDashboard || {};

(function(WD) {
    'use strict';

    // Discipline colors mapping (expanded)
    WD.disciplineColorMap = {};

    /**
     * Build color map from current top disciplines
     * @param {object} topDisciplines - Top disciplines data
     */
    WD.buildDisciplineColorMap = function(topDisciplines) {
        WD.disciplineColorMap = {};
        const entries = Object.entries(topDisciplines || {});
        entries.forEach(([name], idx) => {
            WD.disciplineColorMap[name] = WD.CHART_PALETTE[idx % WD.CHART_PALETTE.length];
        });
        // Add static discipline colors as fallbacks
        Object.entries(WD.DISCIPLINE_COLORS).forEach(([k, v]) => {
            if (!WD.disciplineColorMap[k]) WD.disciplineColorMap[k] = v;
        });
    };

    /**
     * Get color for a discipline
     * @param {string} discipline - Discipline name
     * @returns {string} Color hex code
     */
    WD.getDisciplineColor = function(discipline) {
        return WD.disciplineColorMap[discipline] ||
               WD.DISCIPLINE_COLORS[discipline] ||
               WD.CHART_PALETTE[Math.abs(hashCode(discipline)) % WD.CHART_PALETTE.length];
    };

    /**
     * Simple hash code for consistent color assignment
     * @param {string} str - String to hash
     * @returns {number} Hash code
     */
    function hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) - hash) + str.charCodeAt(i);
            hash |= 0; // Convert to 32bit int
        }
        return hash;
    }

    /**
     * Default Chart.js options for accessibility and consistency
     */
    WD.chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    font: {
                        family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                    },
                    color: '#334155'
                }
            },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                borderColor: 'rgba(148, 163, 184, 0.3)',
                borderWidth: 1
            }
        }
    };

    /**
     * Apply modern defaults to Chart.js
     */
    WD.applyChartDefaults = function() {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
        Chart.defaults.color = '#334155';
        Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.3)';
        Chart.defaults.plugins.legend.labels.color = '#334155';
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
        Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
        Chart.defaults.plugins.tooltip.bodyColor = '#ffffff';
    };

    /**
     * Render custom legend for a chart with top-N and toggle
     * @param {Chart} chart - Chart.js instance
     * @param {HTMLElement} container - Container element
     * @param {object} options - Legend options
     */
    WD.renderCustomLegend = function(chart, container, options = {}) {
        const { topN = 5 } = options;
        let existingLegend = container.querySelector('.custom-legend');
        if (existingLegend) existingLegend.remove();

        const datasets = chart.data.datasets;
        if (datasets.length <= topN) return; // No need for custom legend

        const legendDiv = document.createElement('div');
        legendDiv.className = 'custom-legend d-flex flex-wrap align-items-center mt-2 gap-2';
        legendDiv.setAttribute('role', 'list');
        legendDiv.setAttribute('aria-label', 'Chart legend');

        let showAll = false;

        const render = () => {
            legendDiv.innerHTML = '';
            const toShow = showAll ? datasets : datasets.slice(0, topN);

            toShow.forEach((ds, idx) => {
                const item = document.createElement('span');
                item.className = 'badge d-flex align-items-center gap-1';
                item.style.backgroundColor = ds.borderColor || ds.backgroundColor;
                item.style.color = '#fff';
                item.style.cursor = 'pointer';
                item.setAttribute('role', 'listitem');
                item.setAttribute('tabindex', '0');
                item.setAttribute('aria-label', `Toggle ${ds.label} visibility`);
                item.innerHTML = WD.escapeHTML(ds.label);

                const toggleVisibility = () => {
                    const meta = chart.getDatasetMeta(idx);
                    meta.hidden = !meta.hidden;
                    chart.update();
                    item.style.opacity = meta.hidden ? '0.5' : '1';
                };

                item.addEventListener('click', toggleVisibility);
                item.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleVisibility();
                    }
                });

                legendDiv.appendChild(item);
            });

            if (datasets.length > topN) {
                const toggle = document.createElement('button');
                toggle.className = 'btn btn-link btn-sm p-0 ms-2';
                toggle.style.fontSize = '0.75rem';
                toggle.textContent = showAll ? 'Show less' : `+${datasets.length - topN} more`;
                toggle.setAttribute('aria-expanded', showAll);
                toggle.addEventListener('click', () => {
                    showAll = !showAll;
                    render();
                });
                legendDiv.appendChild(toggle);
            }
        };

        render();
        container.appendChild(legendDiv);
    };

    /**
     * Add export button to chart container
     * @param {HTMLElement} container - Chart container
     * @param {Chart} chart - Chart instance
     * @param {string} filename - Export filename
     */
    WD.addChartExportButton = function(container, chart, filename) {
        if (!container || !chart) return;

        let exportBtn = container.querySelector('.chart-export-btn');
        if (exportBtn) return; // Already added

        exportBtn = document.createElement('button');
        exportBtn.className = 'chart-export-btn btn btn-sm btn-outline-secondary';
        exportBtn.style.cssText = 'position:absolute;top:8px;right:8px;z-index:10;font-size:0.75rem;';
        exportBtn.innerHTML = '<i class="fas fa-download" aria-hidden="true"></i><span class="sr-only">Export chart</span>';
        exportBtn.setAttribute('title', 'Export chart as PNG');
        exportBtn.setAttribute('aria-label', `Export ${filename} chart as PNG image`);

        exportBtn.addEventListener('click', () => {
            const link = document.createElement('a');
            link.download = `${filename}.png`;
            link.href = chart.toBase64Image();
            link.click();
        });

        container.style.position = container.style.position || 'relative';
        container.appendChild(exportBtn);
    };

    WD.dlog && WD.dlog('Chart configuration loaded');

})(window.WildlifeDashboard);
