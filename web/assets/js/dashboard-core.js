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
    dataPeriod: document.getElementById('data-period-range'),
    geographyDiscipline: document.getElementById('geography-discipline-filter'),
    compensationInstitution: document.getElementById('compensation-institution-filter'),
    noDataBanner: document.getElementById('no-data-banner'),
    weeklySpotlight: document.getElementById('weekly-spotlight'),
    topLocations: document.getElementById('top-locations-list')
  };

  const chartState = {
    trend: null,
    disciplineLatest: null,
    disciplineOverall: null,
    salary: null,
    seasonality: null
  };

  const SOURCE_PATHS = {
    analytics: 'data/dashboard_analytics.json',
    positions: 'data/dashboard_positions.json',
    verified: 'data/verified_graduate_assistantships.json',
    enhanced: 'data/enhanced_data.json',
    export: 'data/export_data.json'
  };
  const DISCIPLINE_COLOR_MAP = {
    'Environmental Sciences': '#0f766e',
    'Fisheries and Aquatic': '#0284c7',
    Wildlife: '#16a34a',
    Entomology: '#f59e0b',
    'Forestry and Habitat': '#a16207',
    Agriculture: '#ca8a04',
    'Human Dimensions': '#8b5cf6',
    Other: '#475569'
  };
  const DISCIPLINE_COLOR_FALLBACK = '#475569';
  const DISCIPLINE_LEGEND_ORDER = [
    'Environmental Sciences',
    'Fisheries and Aquatic',
    'Wildlife',
    'Entomology',
    'Forestry and Habitat',
    'Agriculture',
    'Human Dimensions',
    'Other'
  ];
  const GEOGRAPHY_DISCIPLINE_ALL = '__all__';
  const COMPENSATION_INSTITUTION_ALL = '__all__';
  const COMPENSATION_INSTITUTION_BIG10 = 'big10';
  const COMPENSATION_INSTITUTION_NON_BIG10 = 'non_big10';
  const BIG10_MATCHERS = [
    /\buniversity of illinois\b/i,
    /\billinois\s+urbana[-\s]?champaign\b/i,
    /\bindiana university\b/i,
    /\buniversity of iowa\b/i,
    /\buniversity of maryland\b/i,
    /\buniversity of michigan\b/i,
    /\bmichigan state university\b/i,
    /\buniversity of minnesota\b/i,
    /\buniversity of nebraska\b/i,
    /\bnorthwestern university\b/i,
    /\bohio state university\b/i,
    /\buniversity of oregon\b/i,
    /\bpennsylvania state university\b/i,
    /\bpenn state\b/i,
    /\bpurdue university\b/i,
    /\brutgers university\b/i,
    /\buniversity of california,\s*los angeles\b/i,
    /\bucla\b/i,
    /\buniversity of southern california\b/i,
    /\busc\b.*\blos angeles\b/i,
    /\buniversity of washington\b/i,
    /\buniversity of wisconsin\b/i
  ];
  const US_STATE_COORDS = {
    Alabama: [32.806671, -86.791130],
    Alaska: [61.370716, -152.404419],
    Arizona: [33.729759, -111.431221],
    Arkansas: [34.969704, -92.373123],
    California: [36.116203, -119.681564],
    Colorado: [39.059811, -105.311104],
    Connecticut: [41.597782, -72.755371],
    Delaware: [39.318523, -75.507141],
    Florida: [27.766279, -81.686783],
    Georgia: [33.040619, -83.643074],
    Hawaii: [21.094318, -157.498337],
    Idaho: [44.240459, -114.478828],
    Illinois: [40.349457, -88.986137],
    Indiana: [39.849426, -86.258278],
    Iowa: [42.011539, -93.210526],
    Kansas: [38.526600, -96.726486],
    Kentucky: [37.668140, -84.670067],
    Louisiana: [31.169546, -91.867805],
    Maine: [44.693947, -69.381927],
    Maryland: [39.063946, -76.802101],
    Massachusetts: [42.230171, -71.530106],
    Michigan: [43.326618, -84.536095],
    Minnesota: [45.694454, -93.900192],
    Mississippi: [32.741646, -89.678696],
    Missouri: [38.456085, -92.288368],
    Montana: [46.921925, -110.454353],
    Nebraska: [41.125370, -98.268082],
    Nevada: [38.313515, -117.055374],
    'New Hampshire': [43.452492, -71.563896],
    'New Jersey': [40.298904, -74.521011],
    'New Mexico': [34.840515, -106.248482],
    'New York': [42.165726, -74.948051],
    'North Carolina': [35.630066, -79.806419],
    'North Dakota': [47.528912, -99.784012],
    Ohio: [40.388783, -82.764915],
    Oklahoma: [35.565342, -96.928917],
    Oregon: [44.572021, -122.070938],
    Pennsylvania: [40.590752, -77.209755],
    'Rhode Island': [41.680893, -71.511780],
    'South Carolina': [33.856892, -80.945007],
    'South Dakota': [44.299782, -99.438828],
    Tennessee: [35.747845, -86.692345],
    Texas: [31.054487, -97.563461],
    Utah: [40.150032, -111.862434],
    Vermont: [44.045876, -72.710686],
    Virginia: [37.769337, -78.169968],
    Washington: [47.400902, -121.490494],
    'West Virginia': [38.491226, -80.954453],
    Wisconsin: [44.268543, -89.616508],
    Wyoming: [42.755966, -107.302490]
  };
  const US_STATE_ABBREV = {
    AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
    CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
    HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa',
    KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland',
    MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri',
    MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey',
    NM: 'New Mexico', NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio',
    OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
    SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont',
    VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming'
  };
  const US_STATES_BY_LENGTH = Object.keys(US_STATE_COORDS).sort((a, b) => b.length - a.length);
  const US_NON_CONTIGUOUS_STATES = new Set(['Alaska', 'Hawaii']);
  const US_INSET_COORDS = {
    Alaska: [26.2, -124.8],
    Hawaii: [24.0, -117.8]
  };
  const DOUGHNUT_PCT_PLUGIN =
    typeof ChartDataLabels !== 'undefined' ? ChartDataLabels : null;

  function doughnutPercent(context) {
    const data = (context?.dataset?.data || []).map((v) => asNumber(v));
    const total = data.reduce((sum, v) => sum + v, 0);
    if (!total) return 0;
    return (asNumber(context?.dataset?.data?.[context.dataIndex]) / total) * 100;
  }

  function doughnutLabelText(value, context) {
    const pct = doughnutPercent(context);
    if (pct < 1) return null;
    return pct >= 10 ? `${pct.toFixed(0)}%` : `${pct.toFixed(1)}%`;
  }

  function doughnutLabelIsLarge(context) {
    return doughnutPercent(context) >= 8;
  }

  function disciplineSortKey(label) {
    const normalized = normalizeDisciplineLabel(label);
    if (normalized === 'Other') return [2, 0, 'Other'];
    const idx = DISCIPLINE_LEGEND_ORDER.indexOf(normalized);
    if (idx >= 0) return [0, idx, normalized];
    return [1, 0, normalized];
  }

  function compareDisciplines(a, b) {
    const ak = disciplineSortKey(a);
    const bk = disciplineSortKey(b);
    if (ak[0] !== bk[0]) return ak[0] - bk[0];
    if (ak[1] !== bk[1]) return ak[1] - bk[1];
    return String(ak[2]).localeCompare(String(bk[2]));
  }

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
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value > 0 ? value : null;
    }
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

  function extractRows(input) {
    if (Array.isArray(input)) return input;
    if (Array.isArray(input?.positions)) return input.positions;
    if (Array.isArray(input?.jobs)) return input.jobs;
    return [];
  }

  function isExplicitGraduateRow(job) {
    if (job?.is_graduate_position === false) return false;
    const disciplinePrimary = String(job?.discipline_primary || '').trim().toLowerCase();
    if (disciplinePrimary === 'non-graduate') return false;
    return true;
  }

  function extractJobs(positionsData, verifiedData, exportData, enhancedData) {
    const positionsRows = extractRows(positionsData).filter((job) => isExplicitGraduateRow(job));
    if (positionsRows.length) {
      return dedupeJobs(positionsRows);
    }

    const verifiedRows = extractRows(verifiedData).filter((job) => isExplicitGraduateRow(job));
    const exportRows = Array.isArray(exportData) ? exportData : [];
    const enhancedRows = extractRows(enhancedData);

    // Backward-compatible fallback if dashboard_positions.json is unavailable.
    if (verifiedRows.length) {
      return dedupeJobs(verifiedRows);
    }

    // Last fallback path only when unified/verified datasets are unavailable.
    const merged = dedupeJobs([...exportRows, ...enhancedRows]);
    const graduateOnly = merged.filter((job) => isGraduatePosting(job));
    return graduateOnly;
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
      .slice(0, 5);

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
        snapshotAvailability: analytics?.snapshot_availability || {},
        availableTimeframes: Object.keys(analytics?.time_series || {})
      },
      compensation: {
        positionsWithSalary,
        totalJobs: jobs.length,
        salaryParsedPct,
        salaryParsedCount: salaries.length,
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
        salaryParsedCount: salaries.length,
        locationParsedCount,
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
    if (refs.weeklySpotlight) {
      refs.weeklySpotlight.innerHTML = '<div class="panel-empty">No data for current filters</div>';
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

  function formatRatio(numerator, denominator) {
    if (!Number.isFinite(denominator) || denominator <= 0) return EMPTY_VALUE;
    const n = Number.isFinite(numerator) ? Math.max(0, Math.round(numerator)) : 0;
    const d = Math.max(0, Math.round(denominator));
    return `${n.toLocaleString()} / ${d.toLocaleString()}`;
  }

  function formatPercent(value) {
    const n = asNumber(value);
    return `${n.toFixed(1)}%`;
  }

  function formatDisplayTimestamp(value) {
    if (!value) return null;
    const raw = String(value).trim();
    if (!raw) return null;
    const parsed = parseFlexibleDate(raw) || new Date(raw.replace(' ', 'T'));
    if (!parsed || Number.isNaN(parsed.getTime())) return raw;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }).format(parsed);
  }

  function formatDateOnly(value) {
    if (!(value instanceof Date) || Number.isNaN(value.getTime())) return EMPTY_VALUE;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }).format(value);
  }

  function getJobPeriodDate(job) {
    return (
      parseFlexibleDate(job?.published_date)
      || parseFlexibleDate(job?.first_seen)
      || parseFlexibleDate(job?.scraped_at)
      || parseFlexibleDate(job?.last_updated)
    );
  }

  function computeDataPeriodRange(jobs) {
    const dates = (Array.isArray(jobs) ? jobs : [])
      .map((job) => getJobPeriodDate(job))
      .filter((dt) => dt instanceof Date && !Number.isNaN(dt.getTime()))
      .sort((a, b) => a.getTime() - b.getTime());

    if (!dates.length) return null;
    return { start: dates[0], end: dates[dates.length - 1] };
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function extractUsStateFromText(rawText) {
    if (typeof rawText !== 'string') return null;
    const text = rawText
      .replace(/[)\]]+$/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    if (!text) return null;

    const lowered = text.toLowerCase();
    if (lowered.includes('remote work allowed') || lowered.includes('multiple')) return null;

    for (const state of US_STATES_BY_LENGTH) {
      const rx = new RegExp(`\\b${escapeRegExp(state)}\\b`, 'i');
      if (rx.test(text)) return state;
    }

    const abbrevs = text.toUpperCase().match(/\b[A-Z]{2}\b/g) || [];
    for (const abbr of abbrevs) {
      const state = US_STATE_ABBREV[abbr];
      if (state) return state;
    }

    return null;
  }

  function buildUsStateCounts(geographicData, jobs) {
    const counts = {};

    const rows = Array.isArray(jobs) ? jobs : [];
    rows.forEach((job) => {
      const state = extractUsStateFromText(String(job?.location || ''));
      if (!state) return;
      counts[state] = (counts[state] || 0) + 1;
    });
    if (Object.keys(counts).length) return counts;

    Object.entries(geographicData || {}).forEach(([rawLocation, rawCount]) => {
      const state = extractUsStateFromText(String(rawLocation || ''));
      if (!state) return;
      counts[state] = (counts[state] || 0) + asNumber(rawCount);
    });
    return counts;
  }

  function getDisciplineCounts(jobs) {
    const counts = {};
    (Array.isArray(jobs) ? jobs : []).forEach((job) => {
      const discipline = normalizeDisciplineLabel(
        String(job?.discipline_primary || job?.discipline || 'Other')
      );
      counts[discipline] = (counts[discipline] || 0) + 1;
    });
    return counts;
  }

  function populateGeographyDisciplineFilter(adapter) {
    const select = refs.geographyDiscipline;
    if (!select) return;

    const jobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    const counts = getDisciplineCounts(jobs);
    const extras = Object.keys(counts)
      .filter((name) => !DISCIPLINE_LEGEND_ORDER.includes(name))
      .sort((a, b) => compareDisciplines(a, b));
    const orderedDisciplines = [...DISCIPLINE_LEGEND_ORDER, ...extras];

    const prior = select.value || GEOGRAPHY_DISCIPLINE_ALL;
    select.innerHTML = '';

    const overallOpt = document.createElement('option');
    overallOpt.value = GEOGRAPHY_DISCIPLINE_ALL;
    overallOpt.textContent = `Overall (${jobs.length.toLocaleString()})`;
    select.appendChild(overallOpt);

    orderedDisciplines.forEach((discipline) => {
      const opt = document.createElement('option');
      opt.value = discipline;
      opt.textContent = `${discipline} (${asNumber(counts[discipline]).toLocaleString()})`;
      select.appendChild(opt);
    });

    const hasPrior = Array.from(select.options).some((opt) => opt.value === prior);
    select.value = hasPrior ? prior : GEOGRAPHY_DISCIPLINE_ALL;
  }

  function getSelectedGeographyDiscipline() {
    const value = String(refs.geographyDiscipline?.value || GEOGRAPHY_DISCIPLINE_ALL);
    return value || GEOGRAPHY_DISCIPLINE_ALL;
  }

  function filterJobsByDiscipline(jobs, selectedDiscipline) {
    const rows = Array.isArray(jobs) ? jobs : [];
    if (!selectedDiscipline || selectedDiscipline === GEOGRAPHY_DISCIPLINE_ALL) return rows;
    return rows.filter((job) => (
      normalizeDisciplineLabel(
        String(job?.discipline_primary || job?.discipline || 'Other')
      ) === selectedDiscipline
    ));
  }

  function getFilteredJobsForActiveGeography(adapter) {
    const allJobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    const selectedDiscipline = getSelectedGeographyDiscipline();
    const filteredJobs = filterJobsByDiscipline(allJobs, selectedDiscipline);
    return { allJobs, selectedDiscipline, filteredJobs };
  }

  function updateNoDataBannerForFilters(adapter) {
    const { allJobs, selectedDiscipline, filteredJobs } = getFilteredJobsForActiveGeography(adapter);
    const hasBaseRows = allJobs.length > 0;
    const hasFilteredRows = filteredJobs.length > 0;
    const hasActiveDisciplineFilter =
      selectedDiscipline && selectedDiscipline !== GEOGRAPHY_DISCIPLINE_ALL;
    showNoDataBanner(!hasBaseRows || (hasActiveDisciplineFilter && !hasFilteredRows));
  }

  function parseBooleanLike(value) {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') return value !== 0;
    if (typeof value !== 'string') return null;
    const normalized = value.trim().toLowerCase();
    if (!normalized) return null;
    if (['true', '1', 'yes', 'y'].includes(normalized)) return true;
    if (['false', '0', 'no', 'n'].includes(normalized)) return false;
    return null;
  }

  function inferBig10Institution(job) {
    const text = [
      String(job?.organization || ''),
      String(job?.title || ''),
      String(job?.url || ''),
      String(job?.description || '')
    ].join(' ');

    return BIG10_MATCHERS.some((rx) => rx.test(text));
  }

  function isBig10Institution(job) {
    const explicit = parseBooleanLike(job?.is_big10_university);
    if (explicit === true) return true;
    if (explicit === false) return false;
    return inferBig10Institution(job);
  }

  function getBig10CoverageStats(jobs) {
    const rows = Array.isArray(jobs) ? jobs : [];
    const total = rows.length;

    let explicitTaggedCount = 0;
    let inferredBig10Count = 0;

    rows.forEach((job) => {
      const explicit = parseBooleanLike(job?.is_big10_university);
      if (explicit !== null) {
        explicitTaggedCount += 1;
        return;
      }
      if (inferBig10Institution(job)) inferredBig10Count += 1;
    });

    const classifiedCount = explicitTaggedCount + inferredBig10Count;
    const unknownCount = Math.max(0, total - classifiedCount);
    const coveragePct = total ? Number(((classifiedCount / total) * 100).toFixed(1)) : 0;

    return {
      total,
      explicitTaggedCount,
      inferredBig10Count,
      classifiedCount,
      unknownCount,
      coveragePct
    };
  }

  function filterJobsByCompensationInstitution(jobs, selectedInstitution) {
    const rows = Array.isArray(jobs) ? jobs : [];
    if (!selectedInstitution || selectedInstitution === COMPENSATION_INSTITUTION_ALL) return rows;
    if (selectedInstitution === COMPENSATION_INSTITUTION_BIG10) {
      return rows.filter((job) => isBig10Institution(job));
    }
    if (selectedInstitution === COMPENSATION_INSTITUTION_NON_BIG10) {
      return rows.filter((job) => !isBig10Institution(job));
    }
    return rows;
  }

  function getSelectedCompensationInstitution() {
    const value = String(
      refs.compensationInstitution?.value || COMPENSATION_INSTITUTION_ALL
    );
    return value || COMPENSATION_INSTITUTION_ALL;
  }

  function getCompensationSelectionLabel(selectedInstitution) {
    if (selectedInstitution === COMPENSATION_INSTITUTION_BIG10) return 'Big Ten rows';
    if (selectedInstitution === COMPENSATION_INSTITUTION_NON_BIG10) return 'Non-Big Ten / Unknown rows';
    return 'overall dataset';
  }

  function populateCompensationInstitutionFilter(adapter) {
    const select = refs.compensationInstitution;
    if (!select) return;

    const allJobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    const big10Jobs = filterJobsByCompensationInstitution(
      allJobs,
      COMPENSATION_INSTITUTION_BIG10
    );
    const nonBig10Jobs = filterJobsByCompensationInstitution(
      allJobs,
      COMPENSATION_INSTITUTION_NON_BIG10
    );

    const prior = select.value || COMPENSATION_INSTITUTION_ALL;
    select.innerHTML = '';

    const options = [
      {
        value: COMPENSATION_INSTITUTION_ALL,
        label: `Overall (${allJobs.length.toLocaleString()})`
      },
      {
        value: COMPENSATION_INSTITUTION_BIG10,
        label: `Big Ten (${big10Jobs.length.toLocaleString()})`
      },
      {
        value: COMPENSATION_INSTITUTION_NON_BIG10,
        label: `Non-Big Ten / Unknown (${nonBig10Jobs.length.toLocaleString()})`
      }
    ];

    options.forEach((optData) => {
      const opt = document.createElement('option');
      opt.value = optData.value;
      opt.textContent = optData.label;
      select.appendChild(opt);
    });

    const hasPrior = Array.from(select.options).some((opt) => opt.value === prior);
    select.value = hasPrior ? prior : COMPENSATION_INSTITUTION_ALL;
  }

  function computeGeographyStats(jobs) {
    const rows = Array.isArray(jobs) ? jobs : [];
    const totalJobs = rows.length;
    const stateCounts = buildUsStateCounts({}, rows);
    const locationParsedCount = Object.values(stateCounts).reduce((sum, n) => sum + asNumber(n), 0);
    const locationParsedPct = totalJobs
      ? Number(((locationParsedCount / totalJobs) * 100).toFixed(1))
      : 0;
    const topLocations = Object.entries(stateCounts)
      .sort((a, b) => asNumber(b[1]) - asNumber(a[1]))
      .slice(0, 5);

    return {
      totalJobs,
      locationParsedCount,
      locationParsedPct,
      distinctLocationCount: Object.keys(stateCounts).length,
      topLocations,
      stateCounts
    };
  }

  function renderOverviewCards(adapter) {
    const overview = adapter?.overview || {};
    const total = asNumber(adapter?.compensation?.totalJobs || overview.totalPositions);
    const grad = asNumber(overview.graduatePositions);
    const discCount = asNumber(overview.disciplineCount);
    const topDisc = overview.topDiscipline;
    const salaryParsedN = asNumber(adapter?.compensation?.salaryParsedCount);
    const salaryParsedPct = asNumber(adapter?.compensation?.salaryParsedPct);

    setCardValue(
      'kpi-grad-positions',
      grad > 0 ? grad.toLocaleString() : EMPTY_VALUE,
      'kpi-grad-positions-reason',
      grad > 0 ? 'Graduate rows in unified dashboard dataset' : 'No rows after filters'
    );

    setCardValue(
      'kpi-salary-coverage',
      total > 0 ? formatRatio(salaryParsedN, total) : EMPTY_VALUE,
      'kpi-salary-coverage-reason',
      total > 0 ? `${formatPercent(salaryParsedPct)} of unified dataset has parseable salary` : 'No rows after filters'
    );

    setCardValue(
      'kpi-disciplines',
      discCount > 0 ? discCount.toLocaleString() : EMPTY_VALUE,
      'kpi-disciplines-reason',
      discCount > 0 ? 'Distinct discipline categories in unified dataset' : 'No rows after filters'
    );

    setCardValue(
      'kpi-top-discipline',
      topDisc ? topDisc : EMPTY_VALUE,
      'kpi-top-discipline-reason',
      topDisc ? 'Largest discipline by posting count in unified dataset' : 'No rows after filters'
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
    const allJobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    const selectedInstitution = getSelectedCompensationInstitution();
    const selectionLabel = getCompensationSelectionLabel(selectedInstitution);
    const filteredJobs = filterJobsByCompensationInstitution(allJobs, selectedInstitution);
    const coverageStats = getBig10CoverageStats(allJobs);

    const totalJobs = filteredJobs.length;
    const salaryValues = filteredJobs
      .map((job) => parseSalaryValue(job.salary ?? job.salary_min))
      .filter((n) => n !== null);
    const parsedCount = salaryValues.length;
    const sampleN = salaryValues.length;
    const pct = totalJobs ? Number(((parsedCount / totalJobs) * 100).toFixed(1)) : 0;
    const med = median(salaryValues);

    setCardValue(
      'kpi-salary-parsed-pct',
      totalJobs > 0 ? formatRatio(parsedCount, totalJobs) : EMPTY_VALUE,
      'kpi-salary-parsed-pct-reason',
      totalJobs > 0
        ? `${formatPercent(pct)} of ${selectionLabel} has parseable salary`
        : 'No rows for selected institution group'
    );

    setCardValue(
      'kpi-salary-n',
      totalJobs > 0 ? sampleN.toLocaleString() : EMPTY_VALUE,
      'kpi-salary-n-reason',
      totalJobs > 0
        ? `Rows in salary-parsed subset from ${selectionLabel}`
        : 'No rows for selected institution group'
    );

    setCardValue(
      'kpi-big10-coverage',
      coverageStats.total > 0
        ? formatRatio(coverageStats.classifiedCount, coverageStats.total)
        : EMPTY_VALUE,
      'kpi-big10-coverage-reason',
      coverageStats.total > 0
        ? (
          `${formatPercent(coverageStats.coveragePct)} usable for Big Ten split `
          + `(${coverageStats.explicitTaggedCount} explicit, `
          + `${coverageStats.inferredBig10Count} inferred Big Ten, `
          + `${coverageStats.unknownCount} unknown)`
        )
        : 'No rows after filters'
    );

    if (sampleN < 5 || med === null) {
      setCardValue(
        'kpi-salary-median',
        EMPTY_VALUE,
        'kpi-salary-median-reason',
        totalJobs === 0
          ? 'No rows after filters'
          : (
            sampleN === 0
              ? 'No salary-parsed rows for selected institution group'
              : `Suppressed when N < 5 (N=${sampleN})`
          )
      );
      return;
    }

    setCardValue(
      'kpi-salary-median',
      formatCurrency(med),
      'kpi-salary-median-reason',
      `Median annualized salary from salary-parsed ${selectionLabel} (N=${sampleN})`
    );
  }

  function renderGeographyCards(adapter) {
    const { selectedDiscipline, filteredJobs } = getFilteredJobsForActiveGeography(adapter);
    const geo = computeGeographyStats(filteredJobs);

    const totalJobs = asNumber(geo.totalJobs);
    const locationPct = asNumber(geo.locationParsedPct);
    const locationParsedCount = asNumber(geo.locationParsedCount);
    const distinctCount = asNumber(geo.distinctLocationCount);
    const topLocations = Array.isArray(geo.topLocations) ? geo.topLocations : [];
    const top = topLocations[0] || null;
    const selectionLabel = selectedDiscipline === GEOGRAPHY_DISCIPLINE_ALL
      ? 'overall dataset'
      : `${selectedDiscipline} rows`;

    setCardValue(
      'kpi-location-parsed-pct',
      totalJobs > 0 ? formatRatio(locationParsedCount, totalJobs) : EMPTY_VALUE,
      'kpi-location-parsed-pct-reason',
      totalJobs > 0 ? `${formatPercent(locationPct)} of ${selectionLabel} mapped to U.S. states` : 'No rows for selected discipline'
    );

    setCardValue(
      'kpi-top-location',
      top ? String(top[0]) : EMPTY_VALUE,
      'kpi-top-location-reason',
      top ? `${asNumber(top[1]).toLocaleString()} rows in selected discipline` : 'No rows for selected discipline'
    );

    setCardValue(
      'kpi-location-count',
      distinctCount > 0 ? distinctCount.toLocaleString() : EMPTY_VALUE,
      'kpi-location-count-reason',
      distinctCount > 0 ? 'Distinct U.S. states in map view' : 'No rows for selected discipline'
    );

    if (refs.topLocations) {
      if (!topLocations.length) {
        refs.topLocations.innerHTML = '<li>No data for selected discipline</li>';
      } else {
        refs.topLocations.innerHTML = topLocations
          .map(([name, count]) => `<li>${escapeHtml(String(name))}: ${asNumber(count).toLocaleString()}</li>`)
          .join('');
      }
    }

    renderMap(geo.stateCounts, selectedDiscipline);
  }

  function renderQualityCards(adapter) {
    const quality = adapter?.quality || {};
    const totalJobs = asNumber(quality.totalJobs);
    const salaryParsedCount = asNumber(quality.salaryParsedCount);
    const locationParsedCount = asNumber(quality.locationParsedCount);
    const salaryPct = asNumber(quality.salaryParsedPct);
    const locationPct = asNumber(quality.locationParsedPct);
    const updated = quality.lastUpdated;

    setCardValue(
      'kpi-quality-salary',
      totalJobs > 0 ? formatRatio(salaryParsedCount, totalJobs) : EMPTY_VALUE,
      'kpi-quality-salary-reason',
      totalJobs > 0 ? `${formatPercent(salaryPct)} parseable salary in unified dataset` : 'No rows after filters'
    );

    setCardValue(
      'kpi-quality-location',
      totalJobs > 0 ? formatRatio(locationParsedCount, totalJobs) : EMPTY_VALUE,
      'kpi-quality-location-reason',
      totalJobs > 0 ? `${formatPercent(locationPct)} parseable location in unified dataset` : 'No rows after filters'
    );

    setCardValue(
      'kpi-quality-updated',
      updated ? formatDisplayTimestamp(updated) : EMPTY_VALUE,
      'kpi-quality-updated-reason',
      updated ? 'From analytics output (dashboard_analytics.json)' : 'No timestamp available'
    );
  }

  function formatSalaryDisplay(value) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return formatCurrency(value);
    }
    if (typeof value === 'string' && value.trim()) return value;
    return EMPTY_VALUE;
  }

  function getIsoWeekId(now = new Date()) {
    const dt = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
    const weekday = dt.getUTCDay() || 7;
    dt.setUTCDate(dt.getUTCDate() + 4 - weekday);
    const yearStart = new Date(Date.UTC(dt.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil((((dt - yearStart) / 86400000) + 1) / 7);
    return `${dt.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`;
  }

  function hashString32(input) {
    const text = String(input || '');
    let hash = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function spotlightSortKey(job) {
    const url = String(job?.url || '').trim().toLowerCase();
    if (url) return `url::${url}`;
    const title = String(job?.title || '').trim().toLowerCase();
    const org = String(job?.organization || '').trim().toLowerCase();
    return `title_org::${title}::${org}`;
  }

  function getMostRecentScrapePool(jobs) {
    const rows = Array.isArray(jobs) ? jobs : [];
    const withRunId = rows.filter((job) => String(job?.scrape_run_id || '').trim());
    if (withRunId.length) {
      const latestByRun = new Map();
      withRunId.forEach((job) => {
        const runId = String(job?.scrape_run_id || '').trim();
        const dt = (
          parseFlexibleDate(job?.scraped_at)
          || parseFlexibleDate(job?.last_updated)
          || parseFlexibleDate(job?.first_seen)
          || parseFlexibleDate(job?.published_date)
          || new Date(0)
        );
        const current = latestByRun.get(runId);
        if (!current || dt > current) latestByRun.set(runId, dt);
      });

      let latestRunId = '';
      let latestRunTime = new Date(0);
      latestByRun.forEach((dt, runId) => {
        if (!latestRunId || dt > latestRunTime) {
          latestRunId = runId;
          latestRunTime = dt;
        }
      });

      const pool = withRunId.filter((job) => String(job?.scrape_run_id || '').trim() === latestRunId);
      return {
        pool,
        sourceLabel: 'the most recent capture cycle',
        sourceKey: `run:${latestRunId}`
      };
    }

    const withScrapedAt = rows.filter((job) => parseFlexibleDate(job?.scraped_at));
    if (withScrapedAt.length) {
      let latest = null;
      withScrapedAt.forEach((job) => {
        const dt = parseFlexibleDate(job?.scraped_at);
        if (dt && (!latest || dt > latest)) latest = dt;
      });
      if (latest) {
        const latestDay = `${latest.getFullYear()}-${String(latest.getMonth() + 1).padStart(2, '0')}-${String(latest.getDate()).padStart(2, '0')}`;
        const pool = withScrapedAt.filter((job) => {
          const dt = parseFlexibleDate(job?.scraped_at);
          if (!dt) return false;
          const day = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
          return day === latestDay;
        });
        return {
          pool,
          sourceLabel: 'the latest capture day',
          sourceKey: `day:${latestDay}`
        };
      }
    }

    const dated = rows
      .map((job) => ({ job, dt: getJobPeriodDate(job) }))
      .filter((item) => item.dt)
      .sort((a, b) => b.dt.getTime() - a.dt.getTime());
    if (dated.length) {
      const latest = dated[0].dt;
      const cutoff = new Date(latest);
      cutoff.setDate(cutoff.getDate() - 7);
      const pool = dated
        .filter((item) => item.dt >= cutoff)
        .map((item) => item.job);
      return {
        pool,
        sourceLabel: 'the most recent posting week',
        sourceKey: `week:${latest.toISOString().slice(0, 10)}`
      };
    }

    return {
      pool: rows,
      sourceLabel: 'the current dataset',
      sourceKey: 'all'
    };
  }

  function selectWeeklySpotlight(jobs) {
    const poolInfo = getMostRecentScrapePool(jobs);
    const pool = Array.isArray(poolInfo.pool) ? poolInfo.pool : [];
    if (!pool.length) return null;

    const ordered = [...pool].sort((a, b) => spotlightSortKey(a).localeCompare(spotlightSortKey(b)));
    const weekId = getIsoWeekId();
    const seed = `${weekId}|${poolInfo.sourceKey}|${ordered.length}`;
    const index = hashString32(seed) % ordered.length;

    return {
      job: ordered[index],
      poolSize: ordered.length,
      weekId,
      sourceLabel: poolInfo.sourceLabel
    };
  }

  function renderWeeklySpotlight(adapter) {
    const jobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    if (!refs.weeklySpotlight) return;

    const selected = selectWeeklySpotlight(jobs);
    if (!selected) {
      refs.weeklySpotlight.innerHTML = '<div class="panel-empty">No data for current filters</div>';
      return;
    }

    const job = selected.job;
    const title = escapeHtml(String(job?.title || 'Untitled Position'));
    const org = escapeHtml(String(job?.organization || 'Unknown Organization'));
    const discipline = escapeHtml(
      normalizeDisciplineLabel(
        String(job?.discipline_primary || job?.discipline || 'Unknown')
      )
    );
    const location = escapeHtml(String(job?.location || 'Unknown'));
    const salary = escapeHtml(formatSalaryDisplay(job?.salary ?? job?.salary_min));
    const posted = formatDateOnly(
      parseFlexibleDate(job?.published_date) || parseFlexibleDate(job?.first_seen)
    );
    const captured = formatDateOnly(
      parseFlexibleDate(job?.scraped_at) || parseFlexibleDate(job?.last_updated)
    );
    const sourceLabel = escapeHtml(selected.sourceLabel);

    refs.weeklySpotlight.innerHTML = `
      <article class="spotlight-card">
        <p class="spotlight-card__eyebrow">Weekly Random Spotlight</p>
        <h4 class="spotlight-card__title">${title}</h4>
        <p class="spotlight-card__org">${org}</p>
        <dl class="spotlight-card__meta">
          <div><dt>Discipline</dt><dd>${discipline}</dd></div>
          <div><dt>Location</dt><dd>${location}</dd></div>
          <div><dt>Salary</dt><dd>${salary}</dd></div>
          <div><dt>Posted</dt><dd>${escapeHtml(posted)}</dd></div>
          <div><dt>Captured</dt><dd>${escapeHtml(captured)}</dd></div>
          <div><dt>Week Key</dt><dd>${escapeHtml(selected.weekId)}</dd></div>
        </dl>
        <p class="spotlight-card__footnote">
          Selected once per week from ${selected.poolSize.toLocaleString()} postings in ${sourceLabel}.
          For complete and current opportunities, use the source jobs board.
        </p>
      </article>
    `;
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
      const discipline = normalizeDisciplineLabel(
        String(job?.discipline_primary || job?.discipline || 'Other').trim() || 'Other'
      );
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
      .sort((a, b) => compareDisciplines(a.discipline, b.discipline));
  }

  function formatDisciplineAxisLabel(label) {
    const normalized = normalizeDisciplineLabel(label);
    const wrapped = {
      'Environmental Sciences': ['Environmental', 'Sciences'],
      'Fisheries and Aquatic': ['Fisheries and', 'Aquatic'],
      'Forestry and Habitat': ['Forestry and', 'Habitat'],
      'Human Dimensions': ['Human', 'Dimensions']
    };
    return wrapped[normalized] || normalized;
  }

  function filterMonthLabels(labels, selected) {
    if (selected !== '1_year') return labels;
    return labels.slice(-12);
  }

  function parseMonthKey(key) {
    const text = String(key || '').trim();
    const m = text.match(/^(\d{4})-(\d{2})$/);
    if (!m) return null;
    const year = Number(m[1]);
    const month = Number(m[2]);
    if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) return null;
    return { year, month };
  }

  function monthKeyToIndex(key) {
    const parsed = parseMonthKey(key);
    if (!parsed) return null;
    return parsed.year * 12 + (parsed.month - 1);
  }

  function indexToMonthKey(index) {
    if (!Number.isFinite(index)) return null;
    const year = Math.floor(index / 12);
    const month = (index % 12) + 1;
    return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`;
  }

  function buildContinuousMonthKeys(keys) {
    const indices = keys
      .map((k) => monthKeyToIndex(k))
      .filter((n) => Number.isFinite(n))
      .sort((a, b) => a - b);
    if (!indices.length) return [];

    const out = [];
    for (let idx = indices[0]; idx <= indices[indices.length - 1]; idx += 1) {
      const key = indexToMonthKey(idx);
      if (key) out.push(key);
    }
    return out;
  }

  function parseDayKey(key) {
    const text = String(key || '').trim();
    const m = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return null;
    const year = Number(m[1]);
    const month = Number(m[2]);
    const day = Number(m[3]);
    if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;
    if (month < 1 || month > 12 || day < 1 || day > 31) return null;
    return { year, month, day };
  }

  function dayKeyToTimestamp(key) {
    const parsed = parseDayKey(key);
    if (!parsed) return null;
    return new Date(parsed.year, parsed.month - 1, parsed.day).getTime();
  }

  function filterDayKeys(keys, selected) {
    if (selected !== '1_year') return keys;
    if (!keys.length) return keys;

    const latestTs = dayKeyToTimestamp(keys[keys.length - 1]);
    if (!Number.isFinite(latestTs)) return keys;
    const oneYearMs = 365 * 24 * 60 * 60 * 1000;
    const cutoffTs = latestTs - oneYearMs;
    return keys.filter((k) => {
      const ts = dayKeyToTimestamp(k);
      return Number.isFinite(ts) && ts >= cutoffTs;
    });
  }

  function normalizeDisciplineLabel(value) {
    const raw = String(value || '').trim();
    if (!raw) return 'Other';

    const disciplineMap = {
      'Environmental Science': 'Environmental Sciences',
      'Environmental Sciences': 'Environmental Sciences',
      Ecology: 'Environmental Sciences',
      'Wildlife Management and Conservation': 'Wildlife',
      'Wildlife Management': 'Wildlife',
      'Wildlife & Natural Resources': 'Wildlife',
      Conservation: 'Wildlife',
      Fisheries: 'Fisheries and Aquatic',
      'Fisheries and Aquatic': 'Fisheries and Aquatic',
      'Fisheries & Aquatic Science': 'Fisheries and Aquatic',
      'Fisheries Management and Conservation': 'Fisheries and Aquatic',
      'Marine Science': 'Fisheries and Aquatic',
      Entomology: 'Entomology',
      Forestry: 'Forestry and Habitat',
      'Forestry and Habitat': 'Forestry and Habitat',
      'Natural Resource Management': 'Forestry and Habitat',
      Agriculture: 'Agriculture',
      'Agricultural Science': 'Agriculture',
      'Animal Science': 'Agriculture',
      Agronomy: 'Agriculture',
      'Range Management': 'Agriculture',
      'Human Dimensions': 'Human Dimensions',
      'Non-Graduate': 'Other',
      Other: 'Other',
      Unknown: 'Other'
    };

    return disciplineMap[raw] || raw;
  }

  function buildDisciplineRowsFromMap(countMap) {
    return Object.entries(countMap || {})
      .map(([name, count]) => [name, asNumber(count)])
      .filter(([, count]) => count > 0)
      .sort((a, b) => compareDisciplines(a[0], b[0]));
  }

  function getDisciplineColor(label) {
    const normalized = normalizeDisciplineLabel(label);
    return DISCIPLINE_COLOR_MAP[normalized] || DISCIPLINE_COLOR_FALLBACK;
  }

  function renderDisciplineSharedLegend(latestRows, overallRows) {
    const el = document.getElementById('discipline-shared-legend');
    if (!el) return;

    const names = new Set();
    [...latestRows, ...overallRows].forEach(([name]) => {
      const normalized = normalizeDisciplineLabel(name);
      if (normalized) names.add(normalized);
    });

    const ordered = [
      ...DISCIPLINE_LEGEND_ORDER,
      ...Array.from(names)
        .filter((name) => !DISCIPLINE_LEGEND_ORDER.includes(name))
        .sort((a, b) => compareDisciplines(a, b))
    ];

    if (!ordered.length) {
      el.innerHTML = '';
      el.classList.add('is-hidden');
      return;
    }

    el.classList.remove('is-hidden');
    el.innerHTML = ordered
      .map((name) => (
        `<span class="shared-legend__item"><span class="shared-legend__swatch" style="background:${getDisciplineColor(name)}"></span>${escapeHtml(name)}</span>`
      ))
      .join('');
  }

  function buildLatestCaptureDisciplineMap(jobs, snapshotAvailability) {
    const fromAnalytics = snapshotAvailability?.latest_run_discipline_breakdown;
    if (fromAnalytics && typeof fromAnalytics === 'object' && Object.keys(fromAnalytics).length) {
      return fromAnalytics;
    }

    const withRunId = jobs.filter((job) => String(job?.scrape_run_id || '').trim());
    if (withRunId.length) {
      const latestByRun = new Map();
      withRunId.forEach((job) => {
        const runId = String(job?.scrape_run_id || '').trim();
        const dt = parseFlexibleDate(job?.scraped_at)
          || parseFlexibleDate(job?.last_updated)
          || parseFlexibleDate(job?.first_seen)
          || parseFlexibleDate(job?.published_date);
        const current = latestByRun.get(runId);
        if (!current || (dt && dt > current)) {
          latestByRun.set(runId, dt || new Date(0));
        }
      });

      let latestRunId = null;
      let latestRunTime = new Date(0);
      latestByRun.forEach((dt, runId) => {
        if (!latestRunId || dt > latestRunTime) {
          latestRunId = runId;
          latestRunTime = dt;
        }
      });

      if (latestRunId) {
        const counts = {};
        withRunId
          .filter((job) => String(job?.scrape_run_id || '').trim() === latestRunId)
          .forEach((job) => {
            const key = normalizeDisciplineLabel(
              job?.discipline_primary || job?.discipline || job?.discipline_secondary || 'Other'
            );
            counts[key] = (counts[key] || 0) + 1;
          });
        return counts;
      }
    }

    const withScrapedAt = jobs.filter((job) => parseFlexibleDate(job?.scraped_at));
    if (!withScrapedAt.length) return {};

    let latestDate = null;
    withScrapedAt.forEach((job) => {
      const dt = parseFlexibleDate(job?.scraped_at);
      if (!latestDate || dt > latestDate) latestDate = dt;
    });
    if (!latestDate) return {};

    const latestDay = `${latestDate.getFullYear()}-${String(latestDate.getMonth() + 1).padStart(2, '0')}-${String(latestDate.getDate()).padStart(2, '0')}`;
    const counts = {};
    withScrapedAt.forEach((job) => {
      const dt = parseFlexibleDate(job?.scraped_at);
      if (!dt) return;
      const day = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
      if (day !== latestDay) return;
      const key = normalizeDisciplineLabel(
        job?.discipline_primary || job?.discipline || job?.discipline_secondary || 'Other'
      );
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }

  function buildPostingSeasonality(jobs) {
    const monthLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const totalsByMonth = new Array(12).fill(0);
    const yearSet = new Set();

    jobs.forEach((job) => {
      const dt = parseFlexibleDate(job?.published_date) || parseFlexibleDate(job?.first_seen);
      if (!dt) return;
      totalsByMonth[dt.getMonth()] += 1;
      yearSet.add(dt.getFullYear());
    });

    const totalPosted = totalsByMonth.reduce((sum, n) => sum + n, 0);
    const yearsCount = yearSet.size || 0;
    const avgByMonth = yearsCount
      ? totalsByMonth.map((n) => Number((n / yearsCount).toFixed(2)))
      : totalsByMonth.map(() => 0);

    return {
      monthLabels,
      totalsByMonth,
      avgByMonth,
      totalPosted,
      yearsCount
    };
  }

  function renderCharts(adapter) {
    const jobs = Array.isArray(adapter?.jobs) ? adapter.jobs : [];
    const topDisciplines = adapter?.disciplines?.topDisciplines || {};
    const timeSeries = adapter?.disciplines?.timeSeries || {};
    const snapshotAvailability = adapter?.disciplines?.snapshotAvailability || {};

    if (!jobs.length) {
      destroyChart('trend');
      destroyChart('disciplineLatest');
      destroyChart('disciplineOverall');
      destroyChart('salary');
      destroyChart('seasonality');
      renderDisciplineSharedLegend([], []);
      setPanelEmpty('trend-panel', 'No data for current filters');
      setPanelEmpty('discipline-latest-panel', 'No data for current filters');
      setPanelEmpty('discipline-overall-panel', 'No data for current filters');
      setPanelEmpty('salary-panel', 'No data for current filters');
      setPanelEmpty('seasonality-panel', 'No data for current filters');
      setPanelEmpty('map-panel', 'No data for current filters');
      return;
    }

    if (!ensureChartJs()) {
      renderDisciplineSharedLegend([], []);
      setPanelEmpty('trend-panel', 'Chart library unavailable');
      setPanelEmpty('discipline-latest-panel', 'Chart library unavailable');
      setPanelEmpty('discipline-overall-panel', 'Chart library unavailable');
      setPanelEmpty('salary-panel', 'Chart library unavailable');
      setPanelEmpty('seasonality-panel', 'Chart library unavailable');
      return;
    }

    const selected = document.querySelector('input[name="timeframe"]:checked')?.value || '1_year';
    const snapshotDaily = snapshotAvailability?.daily_avg_active_grad_positions || {};
    const snapshotMonthly = snapshotAvailability?.monthly_avg_active_grad_positions || {};
    const snapshotSource = String(snapshotAvailability?.source || '');

    let trendMode = 'daily';
    let dateKeys = Object.keys(snapshotDaily)
      .filter((k) => dayKeyToTimestamp(k) !== null)
      .sort();
    dateKeys = filterDayKeys(dateKeys, selected);

    let monthMap = snapshotMonthly;
    if (!dateKeys.length && !Object.keys(monthMap).length) {
      const key = resolveTimeframeKey(timeSeries, selected);
      monthMap = key ? (timeSeries[key]?.total_monthly || {}) : {};
    }

    let trendValues = [];
    if (dateKeys.length) {
      trendValues = dateKeys.map((k) => ({
        x: dayKeyToTimestamp(k),
        y: Object.prototype.hasOwnProperty.call(snapshotDaily, k) ? asNumber(snapshotDaily[k]) : null
      }));
    } else {
      trendMode = 'monthly';
      const allMonthLabels = buildContinuousMonthKeys(Object.keys(monthMap));
      const monthLabels = filterMonthLabels(allMonthLabels, selected);
      trendValues = monthLabels.map((k) => {
        const parsed = parseMonthKey(k);
        if (!parsed) return null;
        return {
          x: new Date(parsed.year, parsed.month - 1, 1).getTime(),
          y: Object.prototype.hasOwnProperty.call(monthMap, k) ? asNumber(monthMap[k]) : null
        };
      }).filter(Boolean);
    }

    if (!trendValues.length) {
      destroyChart('trend');
      setPanelEmpty('trend-panel', 'No data for current filters');
    } else {
      const trendPanel = document.getElementById('trend-panel');
      if (trendPanel) trendPanel.innerHTML = '<canvas id="trend-chart"></canvas>';
      destroyChart('trend');
      const trendCtx = document.getElementById('trend-chart');
      if (trendCtx) {
        const xDateFormatter = new Intl.DateTimeFormat('en-US', trendMode === 'daily'
          ? { month: 'short', day: 'numeric', year: 'numeric' }
          : { month: 'short', year: 'numeric' });
        chartState.trend = new Chart(trendCtx, {
          type: 'line',
          data: {
            datasets: [{
              label: snapshotSource
                ? 'Unique Graduate Positions Captured by Date'
                : 'Postings',
              data: trendValues,
              parsing: false,
              borderColor: '#0f766e',
              backgroundColor: 'rgba(15, 118, 110, 0.2)',
              tension: 0.25,
              spanGaps: true,
              fill: true
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
              padding: { left: 10, right: 6 }
            },
            scales: {
              x: {
                type: 'linear',
                title: { display: true, text: trendMode === 'daily' ? 'Capture Date' : 'Month' },
                ticks: {
                  maxRotation: 0,
                  autoSkip: true,
                  maxTicksLimit: 8,
                  callback: (value) => xDateFormatter.format(new Date(Number(value)))
                }
              },
              y: {
                beginAtZero: true,
                title: {
                  display: true,
                  text: snapshotSource
                    ? 'Unique Graduate Positions (count)'
                    : 'Postings (count)'
                }
              }
            },
            plugins: {
              tooltip: {
                callbacks: {
                  title: (items) => {
                    const ts = items?.[0]?.parsed?.x;
                    return Number.isFinite(ts) ? xDateFormatter.format(new Date(ts)) : '';
                  }
                }
              }
            }
          }
        });
      }
    }

    const overallDisciplineMap = Object.fromEntries(
      Object.entries(topDisciplines).map(([name, stats]) => [
        name,
        asNumber(stats?.grad_positions || stats?.total_positions)
      ])
    );
    const overallDisciplineRows = buildDisciplineRowsFromMap(overallDisciplineMap);
    const latestDisciplineRows = buildDisciplineRowsFromMap(
      buildLatestCaptureDisciplineMap(jobs, snapshotAvailability)
    );
    renderDisciplineSharedLegend(latestDisciplineRows, overallDisciplineRows);

    if (!latestDisciplineRows.length) {
      destroyChart('disciplineLatest');
      setPanelEmpty('discipline-latest-panel', 'No last-capture snapshot available');
    } else {
      const panel = document.getElementById('discipline-latest-panel');
      if (panel) panel.innerHTML = '<canvas id="discipline-latest-chart"></canvas>';
      destroyChart('disciplineLatest');
      const ctx = document.getElementById('discipline-latest-chart');
      if (ctx) {
        chartState.disciplineLatest = new Chart(ctx, {
          type: 'doughnut',
          plugins: DOUGHNUT_PCT_PLUGIN ? [DOUGHNUT_PCT_PLUGIN] : [],
          data: {
            labels: latestDisciplineRows.map((r) => r[0]),
            datasets: [{
              data: latestDisciplineRows.map((r) => r[1]),
              backgroundColor: latestDisciplineRows.map((r) => getDisciplineColor(r[0])),
              borderColor: '#000000',
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
              padding: { top: 18, right: 26, bottom: 18, left: 26 }
            },
            plugins: {
              legend: { display: false },
              datalabels: {
                display: 'auto',
                formatter: doughnutLabelText,
                anchor: (context) => (doughnutLabelIsLarge(context) ? 'center' : 'end'),
                align: (context) => (doughnutLabelIsLarge(context) ? 'center' : 'end'),
                offset: (context) => (doughnutLabelIsLarge(context) ? 0 : 8),
                clamp: true,
                clip: false,
                color: (context) => (doughnutLabelIsLarge(context) ? '#ffffff' : '#111111'),
                font: {
                  weight: '600',
                  size: 11
                }
              }
            }
          }
        });
      }
    }

    if (!overallDisciplineRows.length) {
      destroyChart('disciplineOverall');
      setPanelEmpty('discipline-overall-panel', 'No data for current filters');
    } else {
      const panel = document.getElementById('discipline-overall-panel');
      if (panel) panel.innerHTML = '<canvas id="discipline-overall-chart"></canvas>';
      destroyChart('disciplineOverall');
      const ctx = document.getElementById('discipline-overall-chart');
      if (ctx) {
        chartState.disciplineOverall = new Chart(ctx, {
          type: 'doughnut',
          plugins: DOUGHNUT_PCT_PLUGIN ? [DOUGHNUT_PCT_PLUGIN] : [],
          data: {
            labels: overallDisciplineRows.map((r) => r[0]),
            datasets: [{
              data: overallDisciplineRows.map((r) => r[1]),
              backgroundColor: overallDisciplineRows.map((r) => getDisciplineColor(r[0])),
              borderColor: '#000000',
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
              padding: { top: 18, right: 26, bottom: 18, left: 26 }
            },
            plugins: {
              legend: { display: false },
              datalabels: {
                display: 'auto',
                formatter: doughnutLabelText,
                anchor: (context) => (doughnutLabelIsLarge(context) ? 'center' : 'end'),
                align: (context) => (doughnutLabelIsLarge(context) ? 'center' : 'end'),
                offset: (context) => (doughnutLabelIsLarge(context) ? 0 : 8),
                clamp: true,
                clip: false,
                color: (context) => (doughnutLabelIsLarge(context) ? '#ffffff' : '#111111'),
                font: {
                  weight: '600',
                  size: 11
                }
              }
            }
          }
        });
      }
    }

    const selectedInstitution = getSelectedCompensationInstitution();
    const compensationJobs = filterJobsByCompensationInstitution(jobs, selectedInstitution);
    const salaryRows = buildSalaryByDiscipline(compensationJobs);
    if (!salaryRows.length) {
      destroyChart('salary');
      setPanelEmpty('salary-panel', 'No salary-parsed rows for selected institution group');
    } else {
      const panel = document.getElementById('salary-panel');
      if (panel) panel.innerHTML = '<canvas id="salary-chart"></canvas>';
      destroyChart('salary');
      const ctx = document.getElementById('salary-chart');
      if (ctx) {
        chartState.salary = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: salaryRows.map((r) => formatDisciplineAxisLabel(r.discipline)),
            datasets: [{
              label: 'Nominal Avg Salary',
              data: salaryRows.map((r) => r.avgNominal),
              backgroundColor: '#0284c7',
              borderColor: '#000000',
              borderWidth: 1,
              borderSkipped: false
            }, {
              label: 'COL-Adjusted Avg Salary (Nebraska baseline)',
              data: salaryRows.map((r) => r.avgAdjusted),
              backgroundColor: '#0f766e',
              borderColor: '#000000',
              borderWidth: 1,
              borderSkipped: false
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                ticks: {
                  autoSkip: false,
                  maxRotation: 0,
                  minRotation: 0
                }
              },
              y: {
                ticks: {
                  callback: (value) => `$${Number(value).toLocaleString()}`
                }
              }
            },
            plugins: {
              subtitle: {
                display: true,
                text: 'COL-adjusted bars display only when salary and location/COL inputs are available.'
              }
            }
          }
        });
      }
    }

    const seasonality = buildPostingSeasonality(jobs);
    if (!seasonality.totalPosted || !seasonality.yearsCount) {
      destroyChart('seasonality');
      setPanelEmpty('seasonality-panel', 'No publish-date data for current dataset');
    } else {
      const panel = document.getElementById('seasonality-panel');
      if (panel) panel.innerHTML = '<canvas id="seasonality-chart"></canvas>';
      destroyChart('seasonality');
      const ctx = document.getElementById('seasonality-chart');
      if (ctx) {
        chartState.seasonality = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: seasonality.monthLabels,
            datasets: [{
              label: `Avg Posted Positions / Month (${seasonality.yearsCount} years)`,
              data: seasonality.avgByMonth,
              backgroundColor: '#0f766e',
              borderColor: '#000000',
              borderWidth: 1,
              borderSkipped: false
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                title: { display: true, text: 'Average Posted Positions' }
              }
            }
          }
        });
      }
    }

  }

  function renderMap(stateCounts, selectedDiscipline) {
    const mapPanel = document.getElementById('map-panel');
    if (!mapPanel) return;
    const entries = Object.entries(stateCounts || {}).filter(([, count]) => asNumber(count) > 0);
    if (!entries.length) {
      mapPanel.innerHTML = '<div class="panel-empty">No mappable U.S. locations for current filters</div>';
      return;
    }

    if (typeof L === 'undefined') {
      mapPanel.innerHTML = '<div class="panel-empty">Map library unavailable</div>';
      return;
    }

    mapPanel.innerHTML = '<div id="leaflet-map" style="height: 100%; width: 100%; border-radius: 8px;"></div>';
    const map = L.map('leaflet-map').setView([37.8, -96], 4);
    const markerColor = selectedDiscipline && selectedDiscipline !== GEOGRAPHY_DISCIPLINE_ALL
      ? getDisciplineColor(selectedDiscipline)
      : '#0f766e';
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map);

    entries.forEach(([state, count]) => {
      const coords = US_INSET_COORDS[state] || US_STATE_COORDS[state];
      if (!coords) return;
      L.circleMarker(coords, {
        radius: Math.max(5, Math.min(16, Math.sqrt(asNumber(count)) * 2.8)),
        fillColor: markerColor,
        color: '#000000',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8
      }).bindPopup(
        `<strong>${escapeHtml(state)}${US_NON_CONTIGUOUS_STATES.has(state) ? ' (inset)' : ''}</strong><br>${asNumber(count)} postings`
      ).addTo(map);
    });

    // Leaflet can render gray tiles when initialized in a hidden container.
    // Trigger a resize pass once layout is visible.
    const refreshMapSize = () => {
      try {
        map.invalidateSize(true);
      } catch (_) {
        // no-op
      }
    };
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(refreshMapSize);
    }
    setTimeout(refreshMapSize, 120);
  }

  let bootStarted = false;

  async function boot() {
    if (bootStarted) return;
    bootStarted = true;

    try {
      bindSidebarActive();
      renderScaffoldPlaceholders();

      const [analytics, positionsData, verifiedData, enhanced, exportData] = await Promise.all([
        fetchJsonWithFallback(SOURCE_PATHS.analytics),
        fetchJsonWithFallback(SOURCE_PATHS.positions),
        fetchJsonWithFallback(SOURCE_PATHS.verified),
        fetchJsonWithFallback(SOURCE_PATHS.enhanced),
        fetchJsonWithFallback(SOURCE_PATHS.export)
      ]);

      if (!analytics) {
        setState('error', `Could not load ${SOURCE_PATHS.analytics}`);
        return;
      }

      const jobs = extractJobs(positionsData, verifiedData, exportData, enhanced);
      const normalized = normalizeData({ analytics, enhanced, jobs });

      // Expose for inspection in dev tools.
      window.WGD_ADAPTER = normalized;

      // Make panels visible before first chart/map render.
      setState('ok', `Adapter ready (${jobs.length} jobs)`);

      if (refs.updatedDate) {
        refs.updatedDate.textContent = formatDisplayTimestamp(normalized.meta.lastUpdated) || EMPTY_VALUE;
      }
      if (refs.dataPeriod) {
        const period = computeDataPeriodRange(normalized.jobs);
        refs.dataPeriod.textContent = period
          ? `${formatDateOnly(period.start)} to ${formatDateOnly(period.end)}`
          : EMPTY_VALUE;
      }

      populateGeographyDisciplineFilter(normalized);
      populateCompensationInstitutionFilter(normalized);
      updateNoDataBannerForFilters(normalized);
      renderOverviewCards(normalized);
      renderCompensationCards(normalized);
      renderGeographyCards(normalized);
      renderQualityCards(normalized);
      renderWeeklySpotlight(normalized);
      renderCharts(normalized);
      bindTimeframeToggle(normalized);
      bindGeographyDisciplineToggle(normalized);
      bindCompensationInstitutionToggle(normalized);
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

  function bindGeographyDisciplineToggle(adapter) {
    const select = refs.geographyDiscipline;
    if (!select) return;
    select.addEventListener('change', () => {
      renderGeographyCards(adapter);
      updateNoDataBannerForFilters(adapter);
    });
  }

  function bindCompensationInstitutionToggle(adapter) {
    const select = refs.compensationInstitution;
    if (!select) return;
    select.addEventListener('change', () => {
      renderCompensationCards(adapter);
      renderCharts(adapter);
    });
  }
})();
