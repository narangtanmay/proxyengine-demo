import { test, expect } from '@playwright/test';

test.describe('ProxyEngine Frontend SML Verification Suite', () => {
  test('should successfully render the live SML dynamic chart on Step 3', async ({ page }) => {
    // Register console and network listeners
    page.on('console', msg => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.log(`[BROWSER ERROR] ${err.message}`);
    });
    page.on('response', async response => {
      if (response.url().includes('chart.png') || response.url().includes('upload-pdf')) {
        console.log(`[NETWORK RESP] ${response.url()} status: ${response.status()}`);
        if (response.status() === 500) {
          try {
            const text = await response.text();
            console.log(`[NETWORK 500 BODY]: ${text}`);
          } catch (e) {
            console.log(`[NETWORK 500 BODY READ FAILED]: ${e.message}`);
          }
        }
      }
    });

    // 1. Visit the home page
    await page.goto('/');

    // 2. Verify Page 1
    await expect(page.locator('h2').first()).toContainText('Page 1: Data Entry & First Impression');

    // 3. Fill in the corporation input field
    const searchInput = page.locator('input[placeholder*="Search German corporations"]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Volkswagen');

    // 4. Select Volkswagen from the dropdown suggestions list
    await page.locator('div', { hasText: 'Volkswagen' }).last().click();

    // 5. Click "Proceed to Criteria" to navigate to Step 2
    const proceedBtn = page.locator('button', { hasText: 'Proceed to Criteria' });
    await proceedBtn.click();

    // 6. Verify we are on Step 2: Evaluation Criteria
    await expect(page.locator('h2').first()).toContainText('Page 2: Specify Query & Checklist Requirements');

    // 7. Click "Submit Evaluation Criteria ⚙️" to run final analysis and navigate to Step 3
    const submitBtn = page.locator('button', { hasText: 'Submit Evaluation Criteria' });
    await submitBtn.click();

    // Wait for the Progress overlay loading container to finish and transition to Step 3
    await page.waitForSelector('text=Running SML Regression Computations', { state: 'detached', timeout: 15000 });

    // 8. Verify we successfully landed on Step 3: Analytical Report
    await expect(page.locator('h2').first()).toContainText('Page 3: Automated Strategic Evaluation Report');

    // 9. Verify SML Card title is visible
    const cardTitle = page.locator('text=SML Quantile Regression Frontier & Peers');
    await expect(cardTitle).toBeVisible();

    // 10. Assert that the offline fallback banner is NOT visible (proves live image loaded with 200 OK)
    const offlineBanner = page.locator('text=Dynamic Graph Rendering Offline');
    await expect(offlineBanner).not.toBeVisible();

    // 11. Assert that the live image is visible on the screen
    const liveChartImage = page.locator('img[alt="SML Regression Scatterplot"]');
    await expect(liveChartImage).toBeVisible();

    // 12. Capture full screenshot of Page 3 showing successful render
    await page.screenshot({ path: 'playwright-artifacts/page3-sml-live-render.png', fullPage: true });
  });
});
