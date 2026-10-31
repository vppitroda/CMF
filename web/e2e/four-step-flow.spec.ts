import { expect, test } from '@playwright/test';

// AT-1 (ordering) and AT-4 (viewer opens on the right page with the matched cell highlighted) in the browser.
test('category -> property -> value -> nearest match -> viewer highlight', async ({ page }) => {
  await page.goto('/');

  // 1 Category (auto-selected) and 2 Property
  await expect(page.locator('#cat')).toContainText('Hydraulic circuit');
  await page.locator('#prop').selectOption({ label: 'Design pressure' });

  // 3 Values actually found, with counts
  const chip230 = page.getByRole('button', { name: /^230 Bar/ });
  await expect(chip230).toContainText('· 3');
  await expect(page.getByRole('button', { name: /^250\/300 Bar/ })).toBeVisible();

  // chip fills the box (first number of the value)
  await chip230.click();
  await expect(page.locator('#val')).toHaveValue('230');

  // 4 Search nearest to 223
  await page.locator('#val').fill('223');
  await page.getByRole('button', { name: 'Go', exact: true }).click();
  const rows = page.locator('.row-result');
  await expect(rows.first()).toContainText('230 Bar');
  await expect(rows.first()).toContainText('Δ 7');
  await expect(rows.nth(3)).toContainText('250/300 Bar');
  await expect(rows.nth(3)).toContainText('DWG');                    // editable CAD source is offered
  await expect(page.locator('.row-result', { hasText: 'Copy' })).toHaveCount(0);

  if (process.env['SHOT_RESULTS']) await page.screenshot({ path: process.env['SHOT_RESULTS'] });

  // viewer: PDF at the matched page, highlight overlay on the page
  await rows.nth(3).locator('.name').click();
  const dialog = page.locator('app-viewer-dialog');
  await expect(dialog.locator('canvas').first()).toBeVisible({ timeout: 60_000 });
  const hl = dialog.locator('.ds-highlight');
  await expect(hl).toBeVisible({ timeout: 60_000 });
  const box = await hl.boundingBox();
  expect(box!.width).toBeGreaterThan(5);
  await expect(hl).toBeInViewport({ ratio: 0.9 });                   // scrolled to the matched cell, not just present
  await expect(dialog.locator('li.match')).toContainText('250/300 Bar');   // matched spec flagged in the side panel
  await page.screenshot({ path: process.env['SHOT'] ?? 'e2e-viewer.png' });

  // non-number for a numeric property -> readable 400
  await dialog.getByRole('button', { name: 'Close' }).click();
  await page.locator('#val').fill('abc');
  await page.getByRole('button', { name: 'Go', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('is not a number');
});
