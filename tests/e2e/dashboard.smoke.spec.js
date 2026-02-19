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

  const sourcePaths = await page.evaluate(() => window.WGD_ADAPTER?.meta?.sourceFiles || {});
  for (const p of Object.values(sourcePaths)) {
    expect(p.startsWith('/')).toBe(false);
    expect(p.startsWith('http://') || p.startsWith('https://')).toBe(false);
  }

  await expect(page.locator('#kpi-quality-salary-reason')).toContainText('parseable salary');
  await expect(page.locator('#kpi-quality-location-reason')).toContainText('parseable location');
  await expect(page.locator('#kpi-quality-updated-reason')).toContainText('analytics output');
  await expect(page.locator('#kpi-quality-updated')).not.toHaveText('—');
  await expect(page.locator('#kpi-quality-salary')).toContainText('/');
  await expect(page.locator('#kpi-quality-location')).toContainText('/');
});

test('suppresses salary median when salary sample is less than 5', async ({ page }) => {
  const mockAnalytics = {
    metadata: { generated_at: '2026-02-18T00:00:00Z' },
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
    metadata: { generated_at: '2026-02-18T00:00:00Z' },
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
