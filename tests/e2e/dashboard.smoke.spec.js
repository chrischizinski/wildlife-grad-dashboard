const { test, expect } = require('@playwright/test');

test('dashboard loads and exits loading state', async ({ page }) => {
  await page.goto('/wildlife_dashboard.html');

  await expect(page.locator('#overview')).toBeVisible();
  await expect(page.locator('#temporal-trends')).toBeVisible();
  await expect(page.locator('#disciplines')).toBeVisible();
  await expect(page.locator('#compensation')).toBeVisible();
  await expect(page.locator('#geography')).toBeVisible();
  await expect(page.locator('#quality')).toBeVisible();

  await page.waitForFunction(() => {
    return window.WGD_ADAPTER_STATUS === 'ready' || window.WGD_ADAPTER_STATUS === 'error';
  });

  const adapterStatus = await page.evaluate(() => window.WGD_ADAPTER_STATUS);
  const adapterError = await page.evaluate(() => window.WGD_ADAPTER_ERROR);

  expect(adapterStatus, `adapter error: ${adapterError || 'unknown'}`).toBe('ready');
  await expect(page.locator('#loading')).toHaveClass(/is-hidden/);
  await expect(page.locator('#error')).toHaveClass(/is-hidden/);
  await expect(page.locator('#main-content')).toBeVisible();

  const jobsCount = await page.evaluate(() => window.WGD_ADAPTER?.jobs?.length ?? 0);
  const noDataHidden = await page
    .locator('#no-data-banner')
    .evaluate((el) => el.classList.contains('is-hidden'));

  if (jobsCount > 0) {
    expect(noDataHidden).toBe(true);
  } else {
    expect(noDataHidden).toBe(false);
    await expect(page.locator('#weekly-spotlight')).toContainText('No data for current filters');
  }
});

test('dashboard uses relative data paths and shows data quality labels', async ({ page }) => {
  await page.goto('/wildlife_dashboard.html');
  await page.waitForFunction(() => window.WGD_ADAPTER_STATUS === 'ready');

  const sourcePaths = await page.evaluate(() => window.WGD_ADAPTER?.meta?.sourceFiles || {});
  for (const p of Object.values(sourcePaths)) {
    expect(p.startsWith('/')).toBe(false);
    expect(p.startsWith('http://') || p.startsWith('https://')).toBe(false);
  }

  await expect(page.locator('#kpi-quality-salary-reason')).toContainText('parseable salary');
  await expect(page.locator('#kpi-quality-location-reason')).toContainText('U.S.-mappable location');
  await expect(page.locator('#kpi-quality-updated-reason')).toContainText('analytics metadata');
  await expect(page.locator('#kpi-quality-updated')).not.toHaveText('—');
  await expect(page.locator('#kpi-quality-capture-reason')).toContainText('source-data capture');
  await expect(page.locator('#kpi-quality-capture')).not.toHaveText('—');
  const period = await page.evaluate(() => ({
    text: document.querySelector('#data-period-range')?.textContent?.trim(),
    start: window.WGD_ADAPTER?.meta?.postingPeriodStart,
    end: window.WGD_ADAPTER?.meta?.postingPeriodEnd
  }));
  const formatYmd = (ymd) => {
    const [year, month, day] = ymd.split('-').map(Number);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }).format(new Date(year, month - 1, day));
  };
  expect(period.text).toContain(`${formatYmd(period.start)} to ${formatYmd(period.end)}`);
  await expect(page.locator('#kpi-quality-salary')).toContainText('/');
  await expect(page.locator('#kpi-quality-location')).toContainText('/');

  await expect(page.locator('#trend-title')).toContainText('Posted by Date');
  await page.click('input[name="trend-date-basis"][value="captured"]');
  await expect(page.locator('#trend-title')).toContainText('Captured by Date');
  await page.click('input[name="trend-date-basis"][value="posted"]');
  await expect(page.locator('#trend-title')).toContainText('Posted by Date');
});

test('suppresses salary median when salary sample is less than 5', async ({ page }) => {
  const mockAnalytics = {
    metadata: {
      generated_at: '2026-02-18T00:00:00Z',
      freshness: {
        analytics_generated_at: '2026-02-18T00:00:00Z',
        latest_capture_at: '2026-02-17T23:00:00Z',
        latest_capture_source: 'scraped_at',
        posting_period_start: '2026-02-10',
        posting_period_end: '2026-02-10',
        row_count: 4
      }
    },
    summary_stats: { total_positions: 4, graduate_positions: 4, positions_with_salary: 4 },
    top_disciplines: {
      Fisheries: { total_positions: 4, grad_positions: 4, salary_stats: { count: 4 } }
    },
    geographic_summary: { Texas: 4 },
    time_series: { '12_month': { total_monthly: { '2026-02': 4 }, discipline_monthly: {} } },
    last_updated: '2026-02-18 00:00:00'
  };

  const mockVerified = [
    { title: 'Grad A', organization: 'Org', location: 'Texas', salary: '$20000', discipline: 'Fisheries', published_date: '2026-02-10' },
    { title: 'Grad B', organization: 'Org', location: 'Texas', salary: '$22000', discipline: 'Fisheries', published_date: '2026-02-10' },
    { title: 'Grad C', organization: 'Org', location: 'Texas', salary: '$24000', discipline: 'Fisheries', published_date: '2026-02-10' },
    { title: 'Grad D', organization: 'Org', location: 'Texas', salary: '$26000', discipline: 'Fisheries', published_date: '2026-02-10' }
  ];

  await page.route(/\/data\/dashboard_analytics\.json$/, async (route) => {
    await route.fulfill({ json: mockAnalytics });
  });
  await page.route(/\/data\/dashboard_positions\.json$/, async (route) => {
    await route.fulfill({ json: mockVerified });
  });
  await page.route(/\/data\/verified_graduate_assistantships\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route(/\/data\/enhanced_data\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route(/\/data\/export_data\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.goto('/wildlife_dashboard.html');
  await page.waitForFunction(() => window.WGD_ADAPTER_STATUS === 'ready');

  await expect(page.locator('#kpi-salary-n')).toHaveText('4');
  await expect(page.locator('#kpi-salary-median')).toHaveText('—');
  await expect(page.locator('#kpi-salary-median-reason')).toContainText('Suppressed when N < 5 (N=4)');
});

test('shows explicit no-data states when dataset is empty', async ({ page }) => {
  const mockAnalytics = {
    metadata: {
      generated_at: '2026-02-18T00:00:00Z',
      freshness: {
        analytics_generated_at: '2026-02-18T00:00:00Z',
        latest_capture_at: null,
        latest_capture_source: null,
        posting_period_start: null,
        posting_period_end: null,
        row_count: 0
      }
    },
    summary_stats: { total_positions: 0, graduate_positions: 0, positions_with_salary: 0 },
    top_disciplines: {},
    geographic_summary: {},
    time_series: { '12_month': { total_monthly: {}, discipline_monthly: {} } },
    last_updated: '2026-02-18 00:00:00'
  };

  await page.route(/\/data\/dashboard_analytics\.json$/, async (route) => {
    await route.fulfill({ json: mockAnalytics });
  });
  await page.route(/\/data\/dashboard_positions\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route(/\/data\/verified_graduate_assistantships\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route(/\/data\/enhanced_data\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route(/\/data\/export_data\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.goto('/wildlife_dashboard.html');
  await page.waitForFunction(() => window.WGD_ADAPTER_STATUS === 'ready');

  await expect(page.locator('#no-data-banner')).toBeVisible();
  await expect(page.locator('#kpi-grad-positions')).toHaveText('—');
  await expect(page.locator('#kpi-grad-positions-reason')).toContainText('No rows after filters');
  await expect(page.locator('#kpi-salary-median')).toHaveText('—');
  await expect(page.locator('#kpi-salary-median-reason')).toContainText('No rows after filters');
  await expect(page.locator('#weekly-spotlight')).toContainText('No data for current filters');
  await expect(page.locator('#trend-panel')).toContainText('No data for current filters');
  await expect(page.locator('#seasonality-panel')).toContainText('No data for current filters');
  await expect(page.locator('#discipline-latest-panel')).toContainText('No data for current filters');
  await expect(page.locator('#discipline-overall-panel')).toContainText('No data for current filters');
  await expect(page.locator('#salary-panel')).toContainText('No data for current filters');
  await expect(page.locator('#map-panel')).toContainText('No data for current filters');
});

test('weekly spotlight excludes professional roles even if they are flagged graduate', async ({ page }) => {
  const mockAnalytics = {
    metadata: {
      generated_at: '2026-04-24T18:43:24Z',
      freshness: {
        analytics_generated_at: '2026-04-24T18:43:24Z',
        latest_capture_at: '2026-03-23T17:34:12Z',
        latest_capture_source: 'scraped_at',
        posting_period_start: '2026-03-20',
        posting_period_end: '2026-03-20',
        row_count: 2
      }
    },
    summary_stats: { total_positions: 2, graduate_positions: 2, positions_with_salary: 2 },
    top_disciplines: {
      Wildlife: { total_positions: 2, grad_positions: 2, salary_stats: { count: 2 } }
    },
    geographic_summary: { Florida: 1, Nebraska: 1 },
    time_series: { '12_month': { total_monthly: { '2026-03': 2 }, discipline_monthly: {} } },
    last_updated: '2026-04-24T18:43:24Z'
  };

  const mockPositions = [
    {
      title: 'Database Engineer/OPS Scientific/Engineering Programmer',
      organization: 'Florida Fish and Wildlife Conservation Commission (State)',
      location: 'St. Petersburg, Florida',
      salary: '$25 per hour',
      discipline: 'Wildlife',
      published_date: '03/20/2026',
      scraped_at: '2026-03-23T17:34:12Z',
      tags: 'N/A',
      description: 'Professional engineering and programming role supporting agency data systems.',
      is_graduate_position: true
    },
    {
      title: 'M.S. Graduate Research Assistantship in Wildlife Ecology',
      organization: 'Example University',
      location: 'Lincoln, Nebraska',
      salary: '$24,000 per year',
      discipline: 'Wildlife',
      published_date: '03/20/2026',
      scraped_at: '2026-03-23T17:34:10Z',
      tags: 'Graduate Opportunities',
      description: 'Student will enroll in an M.S. graduate program and receive a research assistantship.',
      is_graduate_position: true
    }
  ];

  await page.route(/\/data\/dashboard_analytics\.json$/, async (route) => {
    await route.fulfill({ json: mockAnalytics });
  });
  await page.route(/\/data\/dashboard_positions\.json$/, async (route) => {
    await route.fulfill({ json: mockPositions });
  });
  await page.route(/\/data\/verified_graduate_assistantships\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route(/\/data\/enhanced_data\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route(/\/data\/export_data\.json$/, async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.goto('/wildlife_dashboard.html');
  await page.waitForFunction(() => window.WGD_ADAPTER_STATUS === 'ready');

  await expect(page.locator('#weekly-spotlight')).toContainText('M.S. Graduate Research Assistantship');
  await expect(page.locator('#weekly-spotlight')).not.toContainText('Database Engineer');
});
