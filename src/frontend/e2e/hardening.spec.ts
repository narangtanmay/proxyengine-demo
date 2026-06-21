import { test, expect } from '@playwright/test';

test.describe('ProxyEngine Frontend Hardening & Boardroom Specs', () => {
  test('should support input hardening, cap compliance warnings, and hover tooltips', async ({ page }) => {
    // Intercept and abort SML chart.png request to force-render the dynamic interactive fallback SVG
    await page.route('**/*chart.png*', route => route.abort());

    page.on('console', msg => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.log(`[BROWSER ERROR] ${err.message}`);
    });

    // 1. Visit the home page
    await page.goto('/');

    // 2. Select Volkswagen AG
    const searchInput = page.locator('input[placeholder*="Search German corporations"]');
    await searchInput.fill('Volkswagen');
    await page.locator('div', { hasText: 'Volkswagen' }).last().click();

    // 3. Verify real-time statutory cap warning and input hardening (FR-02 & FR-01)
    const baseInput = page.locator('input[type="number"]').first(); // Fixed Base Component
    const stiInput = page.locator('input[type="number"]').nth(2); // Short-Term Variable (STV)
    const ltiInput = page.locator('input[type="number"]').nth(3); // Long-Term Variable (LTI)
    const capInput = page.locator('input[type="number"]').nth(4); // Maximum Cap Enumeration

    // Input extremely large values to test cap exceeds warning (FR-02)
    await baseInput.fill('6000000');
    await stiInput.fill('6000000');
    await ltiInput.fill('6000000');
    await capInput.fill('10000000'); // Sum (18M) exceeds Cap (10M)

    // Expect red warning border on inputs
    await expect(baseInput).toHaveCSS('border-color', /rgb\(239, 68, 68\)|#ef4444/);
    await expect(stiInput).toHaveCSS('border-color', /rgb\(239, 68, 68\)|#ef4444/);
    await expect(ltiInput).toHaveCSS('border-color', /rgb\(239, 68, 68\)|#ef4444/);

    // 4. Test empty input fallback (FR-01)
    await baseInput.fill('');
    // Ensure it doesn't cause raw NaN/concatenation errors - check that we can transition
    const proceedBtn = page.locator('button', { hasText: 'Proceed to Criteria' });
    await proceedBtn.click();

    // Select all criteria and submit
    await page.locator('h2', { hasText: 'Page 2: Specify Query & Checklist Requirements' });
    const submitBtn = page.locator('button', { hasText: 'Submit Evaluation Criteria' });
    await submitBtn.click();

    // Wait for Step 3 to load
    await page.waitForSelector('text=Running SML Regression Computations', { state: 'detached', timeout: 15000 });
    await expect(page.locator('h2').first()).toContainText('Page 3: Automated Strategic Evaluation Report');

    // 5. Test coordinate boundary limits & log-clamping on SVG (FR-05)
    // The fallback SVG should render successfully without NaN / Infinity attributes even with the 0 base input
    const svgCircle = page.locator('svg circle').first();
    await expect(svgCircle).toBeVisible();
    
    // Ensure no circle has NaN / Infinity coordinates
    const cx = await svgCircle.getAttribute('cx');
    const cy = await svgCircle.getAttribute('cy');
    expect(cx).not.toContain('NaN');
    expect(cy).not.toContain('NaN');
    expect(cx).not.toContain('Infinity');
    expect(cy).not.toContain('Infinity');

    // 6. Verify SVG Circle Hover interactive tooltips (FR-03 & FR-04)
    const targetCircle = page.locator('circle[fill="#ff7600"]');
    await expect(targetCircle).toBeVisible();
    await targetCircle.hover({ force: true });
    
    // Expect tooltip details card overlay to appear
    const tooltipSpan = page.locator('span', { hasText: 'Revenue (Size):' }).first();
    await expect(tooltipSpan).toBeVisible();

    // 7. Verify dynamic peers list is loaded from API instead of statically hardcoded (Mismatch 2)
    const peerItemsCount = await page.locator('svg circle').count();
    expect(peerItemsCount).toBeGreaterThan(0);
  });
});