const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8080',
    trace: 'retain-on-failure'
  },
  webServer: {
    command: 'python3 -m http.server 8080',
    cwd: './web',
    url: 'http://127.0.0.1:8080/wildlife_dashboard.html',
    reuseExistingServer: true,
    timeout: 30_000
  }
});
