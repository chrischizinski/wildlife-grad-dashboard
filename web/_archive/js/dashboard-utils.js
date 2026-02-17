/**
 * Wildlife Dashboard Utilities
 * Common utility functions used across the dashboard
 */

// Create namespace to avoid global pollution
window.WildlifeDashboard = window.WildlifeDashboard || {};

(function(WD) {
    'use strict';

    /**
     * Debug logging utilities
     */
    const DEBUG = (() => {
        try {
            const fromQs = new URLSearchParams(window.location.search).has('debug');
            const fromStorage = (window.localStorage && localStorage.getItem('WGD_DEBUG') === '1');
            return fromQs || fromStorage;
        } catch (_) { return false; }
    })();

    WD.dlog = (...args) => { if (DEBUG) console.log('[WD]', ...args); };
    WD.dwarn = (...args) => { if (DEBUG) console.warn('[WD]', ...args); };
    WD.derror = (...args) => { if (DEBUG) console.error('[WD]', ...args); };

    /**
     * Sanitize HTML content to prevent XSS attacks
     * @param {string} str - String to sanitize
     * @returns {string} Sanitized string
     */
    WD.escapeHTML = function(str) {
        if (typeof str !== 'string') return String(str);
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    };

    /**
     * Format a number as currency
     * @param {number} value - Value to format
     * @param {string} currency - Currency symbol (default: $)
     * @returns {string} Formatted currency string
     */
    WD.formatCurrency = function(value, currency = '$') {
        if (typeof value !== 'number' || isNaN(value)) return 'N/A';
        return currency + Math.round(value).toLocaleString();
    };

    /**
     * Format a date string for display
     * @param {string} dateStr - Date string to format
     * @param {object} options - Intl.DateTimeFormat options
     * @returns {string} Formatted date string
     */
    WD.formatDate = function(dateStr, options = {}) {
        if (!dateStr) return 'Unknown';
        try {
            const date = new Date(dateStr);
            const defaultOptions = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            };
            return date.toLocaleDateString('en-US', { ...defaultOptions, ...options });
        } catch (_) {
            return dateStr;
        }
    };

    /**
     * Parse salary from text string
     * @param {string} text - Salary text to parse
     * @returns {number} Parsed salary value or 0
     */
    WD.parseSalaryFromText = function(text) {
        if (!text || typeof text !== 'string') return 0;
        const nums = text.match(/\$?\s*([0-9][0-9,]*)/g);
        if (!nums) return 0;
        const values = nums.map(n => parseInt(n.replace(/[$,\s]/g, ''), 10)).filter(v => !isNaN(v));
        if (!values.length) return 0;
        // If a range, average; otherwise single value
        const sum = values.reduce((a, b) => a + b, 0);
        return Math.round(sum / values.length);
    };

    /**
     * Normalize organization name for matching
     * @param {string} name - Organization name
     * @returns {string} Normalized name
     */
    WD.normalizeOrgName = function(name) {
        return String(name || '')
            .toLowerCase()
            .replace(/\([^)]*\)/g, ' ') // remove parenthetical descriptors
            .replace(/[.,]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    };

    /**
     * Normalize timeframe values across controls
     * @param {string} val - Timeframe value
     * @returns {string} Normalized timeframe
     */
    WD.normalizeTimeframe = function(val) {
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
    };

    /**
     * Calculate percentage change between first and last values
     * @param {number[]} data - Array of values
     * @returns {number} Percentage change
     */
    WD.calculatePercentageChange = function(data) {
        if (data.length < 2) return 0;
        const firstValue = data.find(val => val > 0) || 0;
        const lastValue = data[data.length - 1] || 0;
        if (firstValue === 0) return lastValue > 0 ? 100 : 0;
        return Math.round(((lastValue - firstValue) / firstValue) * 100);
    };

    /**
     * Debounce function to limit rate of execution
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    WD.debounce = function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    };

    /**
     * Get month key from date string
     * @param {string} dateStr - Date string
     * @returns {string|null} Month key in YYYY-MM format
     */
    WD.monthKeyFromDate = function(dateStr) {
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
    };

    // Big Ten Universities patterns for classification
    WD.BIG_TEN_PATTERNS = [
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

    /**
     * Check if a university is Big Ten
     * @param {string} organizationName - Organization name
     * @returns {boolean} True if Big Ten university
     */
    WD.isBigTenUniversity = function(organizationName) {
        if (!organizationName) return false;
        const org = WD.normalizeOrgName(organizationName);
        return WD.BIG_TEN_PATTERNS.some(rx => rx.test(org));
    };

    // Modern, accessible color palette for charts
    WD.CHART_PALETTE = [
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

    // Discipline-specific colors
    WD.DISCIPLINE_COLORS = {
        'Fisheries Management and Conservation': '#4682B4',
        'Wildlife Management and Conservation': '#2E8B57',
        'Human Dimensions': '#CD853F',
        'Environmental Science': '#9932CC',
        'Other': '#708090'
    };

    WD.dlog('Dashboard utilities loaded');

})(window.WildlifeDashboard);
