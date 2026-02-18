/*
  Step 1: Data adapter only.
  - Fetch source JSON files.
  - Normalize to one frontend schema.
  - Expose normalized payload for next implementation steps.
  UI cards/charts intentionally remain blank in this step.
*/

(function () {
  // Always expose debug globals so console inspection works even on load failure.
  window.WGD_ADAPTER = null;
  window.WGD_ADAPTER_STATUS = 'booting';
  window.WGD_ADAPTER_ERROR = null;
  const EMPTY_VALUE = '—';

  const refs = {
    loading: document.getElementById('loading'),
    error: document.getElementById('error'),
    errorMessage: document.getElementById('error-message'),
    main: document.getElementById('main-content'),
    statusText: document.getElementById('status-text'),
    statusIcon: document.getElementById('status-icon'),
    updatedDate: document.getElementById('last-updated-date'),
    noDataBanner: document.getElementById('no-data-banner'),
    jobsTable: document.getElementById('jobs-table'),
    topLocations: document.getElementById('top-locations-list')
  };

  const chartState = {
    trend: null,
    discipline: null,
    salary: null
  };

  const SOURCE_PATHS = {
    analytics: 'data/dashboard_analytics.json',
    verified: 'data/verified_graduate_assistantships.json',
    enhanced: 'data/enhanced_data.json',
    export: 'data/export_data.json'
  };

  function setState(kind, message) {
    if (refs.loading) refs.loading.classList.add('is-hidden');
    if (refs.error) refs.error.classList.add('is-hidden');
    if (refs.main) refs.main.classList.remove('is-hidden');

    if (kind === 'error') {
      window.WGD_ADAPTER_STATUS = 'error';
      window.WGD_ADAPTER_ERROR = message || 'Unknown adapter error';
      if (refs.error) refs.error.classList.remove('is-hidden');
      if (refs.errorMessage) refs.errorMessage.textContent = message || 'Dashboard failed to load.';
      if (refs.main) refs.main.classList.add('is-hidden');
      return;
    }

    window.WGD_ADAPTER_STATUS = 'ready';
    window.WGD_ADAPTER_ERROR = null;
    if (refs.statusText) refs.statusText.textContent = message || 'Ready';
    if (refs.statusIcon) refs.statusIcon.className = 'fas fa-circle';
  }

  async function fetchJsonWithFallback(path) {
    const candidates = [path, `./${path}`, `../${path}`];
    for (const candidate of candidates) {
      const response = await fetch(candidate).catch(() => null);
      if (!response || !response.ok) continue;
      try {
        return await response.json();
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  function asNumber(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  function parseSalaryValue(value) {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value !== 'string' || !value.trim()) return null;

    const text = value.replace(/[,$]/g, '');
    const match = text.match(/(\d+(?:\.\d+)?)/);
    if (!match) return null;

    let n = Number(match[1]);
    if (!Number.isFinite(n) || n <= 0) return null;
    if (/hour|hr/i.test(text)) n *= 2000;
    return n;
  }

  function isLocationParsed(location) {
    if (typeof location !== 'string') return false;
    const normalized = location.trim().toLowerCase();
    if (!normalized) return false;
    return !['unknown', 'n/a', 'na', 'multiple'].includes(normalized);
  }

  function normalizeGeographicSummary(input) {
    const out = {};
    if (!input || typeof input !== 'object') return out;

    Object.entries(input).forEach(([key, rawCount]) => {
      const cleanedKey = String(key || '')
        .replace(/[)\]]+$/g, '')
        .trim();
      if (!cleanedKey) return;
      const count = asNumber(rawCount);
      if (count <= 0) return;
      out[cleanedKey] = (out[cleanedKey] || 0) + count;
    });

    return out;
  }

  function parseFlexibleDate(value) {
    if (!value) return null;
    const text = String(value).trim();
    if (!text) return null;

    // Try native parse first (ISO and many common formats).
    const native = Date.parse(text);
    if (Number.isFinite(native)) return new Date(native);

    // Fallback for mm/dd/yyyy embedded in text blocks.
    const m = text.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
    if (!m) return null;
    const month = Number(m[1]) - 1;
    const day = Number(m[2]);
    const year = Number(m[3]);
    const dt = new Date(year, month, day);
    return Number.isFinite(dt.getTime()) ? dt : null;
  }

  function normalizeDayStart(dt) {
    return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
  }

  function isCurrentPosting(job, now) {
    const today = normalizeDayStart(now);
    const cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - 120);

    const deadline = parseFlexibleDate(job?.application_deadline);
    if (deadline) return normalizeDayStart(deadline) >= today;

    const pub = parseFlexibleDate(job?.published_date);
    if (pub) return pub >= cutoff;

    const scraped = parseFlexibleDate(job?.scraped_at);
    if (scraped) return scraped >= cutoff;

    return false;
  }

  function isGraduatePosting(job) {
    const tags = String(job?.tags || '').toLowerCase();
    const title = String(job?.title || '').toLowerCase();
    const desc = String(job?.description || '').toLowerCase();
    const positionType = String(job?.position_type || '').toLowerCase();

    const hardExclude = [
      'veterinarian',
      'veterinary',
      'technician',
      'field technician',
      'environmental specialist',
      'specialist (rapid responder)',
      'specialist',
      'archaeologist',
      'certificate',
      'field assistant',
      'biologist i',
      'biologist ii',
      'crew lead',
      'crew leader',
      'assistant professor',
      'associate professor',
      'postdoctoral',
      'post-doc',
      'internship'
    ];
    if (hardExclude.some((kw) => title.includes(kw))) return false;
    if (hardExclude.some((kw) => positionType.includes(kw))) return false;

    const explicitGraduateTag =
      tags.includes('graduate opportunities') ||
      positionType.includes('graduate');

    const explicitGraduateTitle =
      title.includes('phd') ||
      title.includes('m.s.') ||
      title.includes('msc') ||
      title.includes('master') ||
      title.includes('graduate assistantship') ||
      title.includes('research assistantship');

    const explicitGraduateBody =
      desc.includes('graduate assistantship') ||
      desc.includes('phd') ||
      desc.includes('masters');

    // Require explicit graduate intent, not just a classifier boolean.
    return explicitGraduateTag || explicitGraduateTitle || explicitGraduateBody;
  }

  function dedupeJobs(rows) {
    const map = new Map();
    rows.forEach((row) => {
      const url = String(row?.url || '').trim().toLowerCase();
      const title = String(row?.title || '').trim().toLowerCase();
      const org = String(row?.organization || '').trim().toLowerCase();
      const key = url || `${title}__${org}`;
      if (!key) return;
      if (!map.has(key)) map.set(key, row);
    });
    return Array.from(map.values());
  }

  function extractJobs(verifiedData, exportData, enhancedData) {
    const verifiedRows = Array.isArray(verifiedData)
      ? verifiedData
      : (Array.isArray(verifiedData?.positions) ? verifiedData.positions : []);
    const exportRows = Array.isArray(exportData) ? exportData : [];
    const enhancedRows = Array.isArray(enhancedData)
      ? enhancedData
      : (Array.isArray(enhancedData?.positions) ? enhancedData.positions : (Array.isArray(enhancedData?.jobs) ? enhancedData.jobs : []));

    const now = new Date();

    // Verified feed is already the graduate-curated source. Use it as primary.
    if (verifiedRows.length) {
      const verified = dedupeJobs(verifiedRows);
      const currentVerified = verified.filter((job) => isCurrentPosting(job, now));
      return currentVerified.length ? currentVerified : verified;
    }

    // Fallback only when verified feed is unavailable.
    const merged = dedupeJobs([...exportRows, ...enhancedRows]);
    const graduateOnly = merged.filter((job) => isGraduatePosting(job));
    return graduateOnly.filter((job) => isCurrentPosting(job, now));
  }

  function normalizeData({ analytics, enhanced, jobs }) {
    const summary = analytics?.summary_stats || analytics?.summary || {};
    const topDisciplines = analytics?.top_disciplines || {};
    const geography = normalizeGeographicSummary(analytics?.geographic_summary || analytics?.geography || {});

    const totalPositions = asNumber(summary.total_positions || summary.total_scraped_positions);
    const graduatePositions = asNumber(summary.graduate_positions);
    const positionsWithSalary = asNumber(summary.positions_with_salary || summary.graduate_positions_with_salary);

    const salaries = jobs
      .map((job) => parseSalaryValue(job.salary ?? job.salary_min))
      .filter((n) => n !== null);

    const salaryParsedPct = jobs.length ? Number(((salaries.length / jobs.length) * 100).toFixed(1)) : 0;
    const locationParsedCount = jobs.filter((job) => isLocationParsed(job.location)).length;
    const locationParsedPct = jobs.length ? Number(((locationParsedCount / jobs.length) * 100).toFixed(1)) : 0;

    const topDiscipline = Object.entries(topDisciplines)
      .sort((a, b) => asNumber(b[1]?.grad_positions || b[1]?.total_positions) - asNumber(a[1]?.grad_positions || a[1]?.total_positions))[0]?.[0] || null;

    const topLocations = Object.entries(geography)
      .sort((a, b) => asNumber(b[1]) - asNumber(a[1]))
      .slice(0, 10);

    return {
      meta: {
        generatedAt: analytics?.metadata?.generated_at || null,
        lastUpdated: analytics?.metadata?.last_updated || analytics?.last_updated || null,
        sourceFiles: SOURCE_PATHS
      },
      overview: {
        totalPositions,
        graduatePositions,
        disciplineCount: Object.keys(topDisciplines).length,
        topDiscipline
      },
      disciplines: {
        topDisciplines,
        timeSeries: analytics?.time_series || {},
        availableTimeframes: Object.keys(analytics?.time_series || {})
      },
      compensation: {
        positionsWithSalary,
        totalJobs: jobs.length,
        salaryParsedPct,
        salarySampleSize: salaries.length,
        salaryValues: salaries
      },
      geography: {
        summary: geography,
        topLocations,
        totalJobs: jobs.length,
        locationParsedCount,
        distinctLocationCount: Object.keys(geography).length,
        locationParsedPct
      },
      quality: {
        totalJobs: jobs.length,
        salaryParsedPct,
        locationParsedPct,
        lastUpdated: analytics?.last_updated || analytics?.metadata?.last_updated || null
      },
      jobs,
      raw: {
        analytics,
        enhanced
      }
    };
  }

  function renderScaffoldPlaceholders() {
    if (refs.jobsTable) {
      refs.jobsTable.innerHTML = '<tr><td colspan="5">No data for current filters</td></tr>';
    }
    if (refs.topLocations) {
      refs.topLocations.innerHTML = '<li>No data for current filters</li>';
    }
  }

  function showNoDataBanner(isVisible) {
    if (!refs.noDataBanner) return;
    refs.noDataBanner.classList.toggle('is-hidden', !isVisible);
  }

  function setCardValue(id, value, reasonId, reason) {
    const valueEl = document.getElementById(id);
    const reasonEl = document.getElementById(reasonId);
    if (valueEl) valueEl.textContent = value;
    if (reasonEl) reasonEl.textContent = reason;
  }

  function renderOverviewCards(adapter) {
    const overview = adapter?.overview || {};
    const total = asNumber(overview.totalPositions);
    const grad = asNumber(overview.graduatePositions);
    const discCount = asNumber(overview.disciplineCount);
    const topDisc = overview.topDiscipline;

    setCardValue(
      'kpi-grad-positions',
      grad > 0 ? grad.toLocaleString() : EMPTY_VALUE,
      'kpi-grad-positions-reason',
      grad > 0 ? 'Graduate postings in current dataset' : 'No rows after filters'
    );

    setCardValue(
      'kpi-total-positions',
      total > 0 ? total.toLocaleString() : EMPTY_VALUE,
      'kpi-total-positions-reason',
      total > 0 ? 'All analyzed postings in current dataset' : 'No rows after filters'
    );

    setCardValue(
      'kpi-disciplines',
      discCount > 0 ? discCount.toLocaleString() : EMPTY_VALUE,
      'kpi-disciplines-reason',
      discCount > 0 ? 'Distinct disciplines represented' : 'No rows after filters'
    );

    setCardValue(
      'kpi-top-discipline',
      topDisc ? topDisc : EMPTY_VALUE,
      'kpi-top-discipline-reason',
      topDisc ? 'Highest posting share' : 'No rows after filters'
    );
  }

  function formatCurrency(n) {
    return `$${Math.round(n).toLocaleString()}`;
  }

  function median(values) {
    if (!Array.isArray(values) || values.length === 0) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    if (sorted.length % 2 === 0) return (sorted[mid - 1] + sorted[mid]) / 2;
    return sorted[mid];
  }

  function renderCompensationCards(adapter) {
    const comp = adapter?.compensation || {};
    const totalJobs = asNumber(comp.totalJobs);
    const pct = asNumber(comp.salaryParsedPct);
    const sampleN = asNumber(comp.salarySampleSize);
    const salaryValues = Array.isArray(comp.salaryValues) ? comp.salaryValues : [];
    const med = median(salaryValues);

    setCardValue(
      'kpi-salary-parsed-pct',
      totalJobs > 0 ? `${pct}%` : EMPTY_VALUE,
      'kpi-salary-parsed-pct-reason',
      totalJobs > 0 ? 'Share of postings with parseable salary' : 'No rows after filters'
    );

    setCardValue(
      'kpi-salary-n',
      totalJobs > 0 ? sampleN.toLocaleString() : EMPTY_VALUE,
      'kpi-salary-n-reason',
      totalJobs > 0 ? 'Salary-parsed subset size' : 'No rows after filters'
    );

    if (sampleN < 5 || med === null) {
      setCardValue(
        'kpi-salary-median',
        EMPTY_VALUE,
        'kpi-salary-median-reason',
        totalJobs === 0
          ? 'No rows after filters'
          : (sampleN === 0 ? 'No salary-parsed rows after filters' : `Suppressed when N < 5 (N=${sampleN})`)
      );
      return;
    }

    setCardValue(
      'kpi-salary-median',
      formatCurrency(med),
      'kpi-salary-median-reason',
      `Median from salary-parsed subset (N=${sampleN})`
    );
  }

  function renderGeographyCards(adapter) {
    const geo = adapter?.geography || {};
    const totalJobs = asNumber(geo.totalJobs);
    const locationPct = asNumber(geo.locationParsedPct);
    const distinctCount = asNumber(geo.distinctLocationCount);
    const topLocations = Array.isArray(geo.topLocations) ? geo.topLocations : [];
    const top = topLocations[0] || null;

    setCardValue(
      'kpi-location-parsed-pct',
      totalJobs > 0 ? `${locationPct}%` : EMPTY_VALUE,
      'kpi-location-parsed-pct-reason',
      totalJobs > 0 ? 'Share of postings with usable location' : 'No rows after filters'
    );

    setCardValue(
      'kpi-top-location',
      top ? String(top[0]) : EMPTY_VALUE,
      'kpi-top-location-reason',
      top ? `${asNumber(top[1]).toLocaleString()} postings` : 'No rows after filters'
    );

    setCardValue(
      'kpi-location-count',
      distinctCount > 0 ? distinctCount.toLocaleString() : EMPTY_VALUE,
      'kpi-location-count-reason',
      distinctCount > 0 ? 'Distinct cleaned location keys' : 'No rows after filters'
    );

    if (refs.topLocations) {
      if (!topLocations.length) {
        refs.topLocations.innerHTML = '<li>No data for current filters</li>';
      } else {
        refs.topLocations.innerHTML = topLocations
          .slice(0, 10)
          .map(([name, count]) => `<li>${escapeHtml(String(name))}: ${asNumber(count).toLocaleString()}</li>`)
          .join('');
      }
    }
  }

  function renderQualityCards(adapter) {
    const quality = adapter?.quality || {};
    const totalJobs = asNumber(quality.totalJobs);
    const salaryPct = asNumber(quality.salaryParsedPct);
    const locationPct = asNumber(quality.locationParsedPct);
    const updated = quality.lastUpdated;

    setCardValue(
      'kpi-quality-salary',
      totalJobs > 0 ? `${salaryPct}%` : EMPTY_VALUE,
      'kpi-quality-salary-reason',
      totalJobs > 0 ? 'Share of postings with parseable salary' : 'No rows after filters'
    );

    setCardValue(
      'kpi-quality-location',
      totalJobs > 0 ? `${locationPct}%` : EMPTY_VALUE,
      'kpi-quality-location-reason',
      totalJobs > 0 ? 'Share of postings with parseable location' : 'No rows after filters'
    );

    setCardValue(
      'kpi-quality-updated',
      updated ? String(updated) : EMPTY_VALUE,
      'kpi-quality-updated-reason',
      updated ? 'From analytics output' : 'No timestamp available'
    );
  }

  function formatSalaryDisplay(value) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return formatCurrency(value);
    }
    if (typeof value === 'string' && value.trim()) return value;
    return EMPTY_VALUE;
  }

  function renderListings(adapter) {
    const jobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    if (!refs.jobsTable) return;

    if (!jobs.length) {
      refs.jobsTable.innerHTML = '<tr><td colspan=\"5\">No data for current filters</td></tr>';
      return;
    }

    const sorted = [...jobs].sort((a, b) => {
      const da = Date.parse(a?.published_date || a?.scraped_at || '') || 0;
      const db = Date.parse(b?.published_date || b?.scraped_at || '') || 0;
      return db - da;
    });

    const rows = sorted.slice(0, 50).map((job) => {
      const title = escapeHtml(String(job?.title || 'Untitled Position'));
      const org = escapeHtml(String(job?.organization || 'Unknown Organization'));
      const discipline = escapeHtml(String(job?.discipline || 'Unknown'));
      const location = escapeHtml(String(job?.location || 'Unknown'));
      const salary = escapeHtml(formatSalaryDisplay(job?.salary ?? job?.salary_min));
      const url = normalizeJobUrl(String(job?.url || '').trim());
      const action = url
        ? `<a href=\"${escapeHtml(url)}\" target=\"_blank\" rel=\"noopener noreferrer\">View</a>`
        : EMPTY_VALUE;

      return `<tr>\n<td><strong>${title}</strong><br><span>${org}</span></td>\n<td>${discipline}</td>\n<td>${location}</td>\n<td>${salary}</td>\n<td>${action}</td>\n</tr>`;
    });

    refs.jobsTable.innerHTML = rows.join('');
  }

  function normalizeJobUrl(rawUrl) {
    if (!rawUrl) return '';
    try {
      const u = new URL(rawUrl);
      const isRwfm = /jobs\.rwfm\.tamu\.edu$/i.test(u.hostname);
      if (!isRwfm) return rawUrl;

      // Canonicalize all RWFM posting links to:
      // https://jobs.rwfm.tamu.edu/view-job/?id=<id>
      // Supports:
      // - /view-job/?id=12345
      // - /view/12345/
      // - /view/12345
      const directId = (u.searchParams.get('id') || '').trim();
      if (/^\d+$/.test(directId)) {
        return `${u.origin}/view-job/?id=${directId}`;
      }

      const pathMatch = u.pathname.match(/^\/view\/(\d+)\/?$/);
      if (pathMatch) {
        return `${u.origin}/view-job/?id=${pathMatch[1]}`;
      }

      return rawUrl;
    } catch (_) {
      return rawUrl;
    }
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function bindSidebarActive() {
    const links = Array.from(document.querySelectorAll('.sidebar-nav__link'));
    links.forEach((link) => {
      link.addEventListener('click', () => {
        links.forEach((x) => x.classList.remove('is-active'));
        link.classList.add('is-active');
      });
    });
  }

  function setPanelEmpty(panelId, message) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.innerHTML = `<div class="panel-empty">${escapeHtml(message)}</div>`;
  }

  function resolveTimeframeKey(timeSeries, selected) {
    if (selected === '1_year' && timeSeries['12_month']) return '12_month';
    if (selected === 'all_time' && timeSeries.all_time) return 'all_time';
    if (selected === 'all_time' && timeSeries['12_month']) return '12_month';
    return Object.keys(timeSeries)[0] || null;
  }

  function ensureChartJs() {
    return typeof Chart !== 'undefined';
  }

  function destroyChart(name) {
    if (chartState[name]) {
      chartState[name].destroy();
      chartState[name] = null;
    }
  }

  function buildSalaryByDiscipline(jobs) {
    const groups = new Map();
    jobs.forEach((job) => {
      const discipline = String(job?.discipline_primary || job?.discipline || 'Other').trim() || 'Other';
      const nominal = parseSalaryValue(job?.salary ?? job?.salary_min);
      const adjusted = parseSalaryValue(job?.salary_lincoln_adjusted);
      const row = groups.get(discipline) || { nominal: [], adjusted: [] };
      if (nominal !== null) row.nominal.push(nominal);
      if (adjusted !== null) row.adjusted.push(adjusted);
      groups.set(discipline, row);
    });

    return Array.from(groups.entries())
      .map(([discipline, values]) => {
        const avgNominal = values.nominal.length
          ? values.nominal.reduce((a, b) => a + b, 0) / values.nominal.length
          : null;
        const avgAdjusted = values.adjusted.length
          ? values.adjusted.reduce((a, b) => a + b, 0) / values.adjusted.length
          : null;
        return { discipline, avgNominal, avgAdjusted };
      })
      .filter((row) => row.avgNominal !== null || row.avgAdjusted !== null)
      .sort((a, b) => {
        const av = a.avgAdjusted ?? a.avgNominal ?? 0;
        const bv = b.avgAdjusted ?? b.avgNominal ?? 0;
        return bv - av;
      });
  }

  function renderCharts(adapter) {
    const jobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    const topDisciplines = adapter?.disciplines?.topDisciplines || {};
    const timeSeries = adapter?.disciplines?.timeSeries || {};
    const geographySummary = adapter?.geography?.summary || {};

    if (!jobs.length) {
      destroyChart('trend');
      destroyChart('discipline');
      destroyChart('salary');
      setPanelEmpty('trend-panel', 'No data for current filters');
      setPanelEmpty('discipline-panel', 'No data for current filters');
      setPanelEmpty('salary-panel', 'No data for current filters');
      setPanelEmpty('map-panel', 'No data for current filters');
      return;
    }

    if (!ensureChartJs()) {
      setPanelEmpty('trend-panel', 'Chart library unavailable');
      setPanelEmpty('discipline-panel', 'Chart library unavailable');
      setPanelEmpty('salary-panel', 'Chart library unavailable');
      return;
    }

    const selected = document.querySelector('input[name="timeframe"]:checked')?.value || '1_year';
    const key = resolveTimeframeKey(timeSeries, selected);
    const monthly = key ? (timeSeries[key]?.total_monthly || {}) : {};
    const monthLabels = Object.keys(monthly).sort();
    const monthValues = monthLabels.map((k) => asNumber(monthly[k]));

    if (!monthLabels.length) {
      destroyChart('trend');
      setPanelEmpty('trend-panel', 'No data for current filters');
    } else {
      const trendPanel = document.getElementById('trend-panel');
      if (trendPanel) trendPanel.innerHTML = '<canvas id="trend-chart"></canvas>';
      destroyChart('trend');
      const trendCtx = document.getElementById('trend-chart');
      if (trendCtx) {
        chartState.trend = new Chart(trendCtx, {
          type: 'line',
          data: {
            labels: monthLabels,
            datasets: [{
              label: 'Postings',
              data: monthValues,
              borderColor: '#0f766e',
              backgroundColor: 'rgba(15, 118, 110, 0.2)',
              tension: 0.25,
              fill: true
            }]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }
    }

    const disciplineRows = Object.entries(topDisciplines)
      .map(([name, stats]) => [name, asNumber(stats?.grad_positions || stats?.total_positions)])
      .filter(([, n]) => n > 0)
      .sort((a, b) => b[1] - a[1]);

    if (!disciplineRows.length) {
      destroyChart('discipline');
      setPanelEmpty('discipline-panel', 'No data for current filters');
    } else {
      const panel = document.getElementById('discipline-panel');
      if (panel) panel.innerHTML = '<canvas id="discipline-chart"></canvas>';
      destroyChart('discipline');
      const ctx = document.getElementById('discipline-chart');
      if (ctx) {
        chartState.discipline = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: disciplineRows.map((r) => r[0]),
            datasets: [{
              data: disciplineRows.map((r) => r[1]),
              backgroundColor: ['#0f766e', '#0284c7', '#f59e0b', '#16a34a', '#8b5cf6', '#ef4444']
            }]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }
    }

    const salaryRows = buildSalaryByDiscipline(jobs);
    if (!salaryRows.length) {
      destroyChart('salary');
      setPanelEmpty('salary-panel', 'No salary-parsed rows after filters');
    } else {
      const panel = document.getElementById('salary-panel');
      if (panel) panel.innerHTML = '<canvas id="salary-chart"></canvas>';
      destroyChart('salary');
      const ctx = document.getElementById('salary-chart');
      if (ctx) {
        chartState.salary = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: salaryRows.map((r) => r.discipline),
            datasets: [{
              label: 'Nominal Avg Salary',
              data: salaryRows.map((r) => r.avgNominal),
              backgroundColor: '#0284c7'
            }, {
              label: 'COL-Adjusted Avg Salary',
              data: salaryRows.map((r) => r.avgAdjusted),
              backgroundColor: '#0f766e'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                ticks: {
                  callback: (value) => `$${Number(value).toLocaleString()}`
                }
              }
            }
          }
        });
      }
    }

    renderMap(geographySummary);
  }

  function renderMap(geographicData) {
    const mapPanel = document.getElementById('map-panel');
    if (!mapPanel) return;
    const entries = Object.entries(geographicData || {}).filter(([, count]) => asNumber(count) > 0);
    if (!entries.length) {
      mapPanel.innerHTML = '<div class="panel-empty">No data for current filters</div>';
      return;
    }

    if (typeof L === 'undefined') {
      mapPanel.innerHTML = '<div class="panel-empty">Map library unavailable</div>';
      return;
    }

    mapPanel.innerHTML = '<div id="leaflet-map" style="height: 100%; width: 100%; border-radius: 8px;"></div>';
    const map = L.map('leaflet-map').setView([37.8, -96], 4);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(map);

    const stateCoords = {
      Alabama: [32.806671, -86.791130], Alaska: [61.370716, -152.404419], Arizona: [33.729759, -111.431221],
      Arkansas: [34.969704, -92.373123], California: [36.116203, -119.681564], Colorado: [39.059811, -105.311104],
      Connecticut: [41.597782, -72.755371], Delaware: [39.318523, -75.507141], Florida: [27.766279, -81.686783],
      Georgia: [33.040619, -83.643074], Hawaii: [21.094318, -157.498337], Idaho: [44.240459, -114.478828],
      Illinois: [40.349457, -88.986137], Indiana: [39.849426, -86.258278], Iowa: [42.011539, -93.210526],
      Kansas: [38.526600, -96.726486], Kentucky: [37.668140, -84.670067], Louisiana: [31.169546, -91.867805],
      Maine: [44.693947, -69.381927], Maryland: [39.063946, -76.802101], Massachusetts: [42.230171, -71.530106],
      Michigan: [43.326618, -84.536095], Minnesota: [45.694454, -93.900192], Mississippi: [32.741646, -89.678696],
      Missouri: [38.456085, -92.288368], Montana: [46.921925, -110.454353], Nebraska: [41.125370, -98.268082],
      Nevada: [38.313515, -117.055374], NewHampshire: [43.452492, -71.563896], NewJersey: [40.298904, -74.521011],
      NewMexico: [34.840515, -106.248482], NewYork: [42.165726, -74.948051], NorthCarolina: [35.630066, -79.806419],
      NorthDakota: [47.528912, -99.784012], Ohio: [40.388783, -82.764915], Oklahoma: [35.565342, -96.928917],
      Oregon: [44.572021, -122.070938], Pennsylvania: [40.590752, -77.209755], RhodeIsland: [41.680893, -71.511780],
      SouthCarolina: [33.856892, -80.945007], SouthDakota: [44.299782, -99.438828], Tennessee: [35.747845, -86.692345],
      Texas: [31.054487, -97.563461], Utah: [40.150032, -111.862434], Vermont: [44.045876, -72.710686],
      Virginia: [37.769337, -78.169968], Washington: [47.400902, -121.490494], WestVirginia: [38.491226, -80.954453],
      Wisconsin: [44.268543, -89.616508], Wyoming: [42.755966, -107.302490]
    };

    entries.forEach(([rawLocation, count]) => {
      const location = String(rawLocation).replace(/[)\]]+$/g, '').trim();
      const compact = location.replace(/\s+/g, '');
      let coords = stateCoords[location] || stateCoords[compact];
      if (!coords) {
        const foundKey = Object.keys(stateCoords).find((k) => location.includes(k) || location.includes(k.replace(/([A-Z])/g, ' $1').trim()));
        if (foundKey) coords = stateCoords[foundKey];
      }
      if (!coords) return;
      L.circleMarker(coords, {
        radius: Math.max(5, Math.min(16, Math.sqrt(asNumber(count)) * 2.8)),
        fillColor: '#0f766e',
        color: '#ffffff',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.75
      }).bindPopup(`<strong>${escapeHtml(location)}</strong><br>${asNumber(count)} postings`).addTo(map);
    });
  }

  let bootStarted = false;

  async function boot() {
    if (bootStarted) return;
    bootStarted = true;

    try {
      bindSidebarActive();
      renderScaffoldPlaceholders();

      const [analytics, verifiedData, enhanced, exportData] = await Promise.all([
        fetchJsonWithFallback(SOURCE_PATHS.analytics),
        fetchJsonWithFallback(SOURCE_PATHS.verified),
        fetchJsonWithFallback(SOURCE_PATHS.enhanced),
        fetchJsonWithFallback(SOURCE_PATHS.export)
      ]);

      if (!analytics) {
        setState('error', `Could not load ${SOURCE_PATHS.analytics}`);
        return;
      }

      const jobs = extractJobs(verifiedData, exportData, enhanced);
      const normalized = normalizeData({ analytics, enhanced, jobs });

      // Expose for inspection in dev tools.
      window.WGD_ADAPTER = normalized;

      if (refs.updatedDate) {
        refs.updatedDate.textContent = normalized.meta.lastUpdated || EMPTY_VALUE;
      }

      renderOverviewCards(normalized);
      renderCompensationCards(normalized);
      renderGeographyCards(normalized);
      renderQualityCards(normalized);
      renderListings(normalized);
      renderCharts(normalized);
      showNoDataBanner(!jobs.length);
      bindTimeframeToggle(normalized);

      setState('ok', `Adapter ready (${jobs.length} jobs)`);
    } catch (err) {
      const msg = err && err.message ? err.message : String(err || 'Unknown error');
      console.error('Dashboard boot failed:', err);
      setState('error', `Dashboard boot failed: ${msg}`);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  function bindTimeframeToggle(adapter) {
    const toggles = Array.from(document.querySelectorAll('input[name="timeframe"]'));
    toggles.forEach((input) => {
      input.addEventListener('change', () => renderCharts(adapter));
    });
  }
})();
