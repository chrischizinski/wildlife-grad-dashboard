const { test, expect } = require('@playwright/test');

test('dashboard loads and exits loading state', async ({ page }) => {
  await page.goto('/wildlife_dashboard.html');

  await expect(page.locator('#overview')).toBeVisible();
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
    await expect(page.locator('#jobs-table')).toContainText('No data for current filters');
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
});
