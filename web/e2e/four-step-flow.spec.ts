import { expect, Page, test } from '@playwright/test';

/** Text of the pdf.js text-layer spans that lie under the highlight overlay: proves it sits on the right words. */
async function textUnderHighlight(page: Page): Promise<string> {
  return page.evaluate(() => {
    const hl = document.querySelector('.ds-highlight')!.getBoundingClientRect();
    return [...document.querySelectorAll('.textLayer span')]
      .filter((s) => {
        const r = s.getBoundingClientRect();
        return r.right > hl.left && r.left < hl.right && r.bottom > hl.top && r.top < hl.bottom;
      })
      .map((s) => s.textContent)
      .join(' ');
  });
}

// AT-1 (ordering) and AT-4 (viewer opens on the right page with the matched cell highlighted) in the browser.
test('category -> property -> value -> nearest match -> viewer highlight', async ({ page }) => {
  await page.goto('/');

  // 1 Category (the first one, Hydraulic circuit, is pre-selected) and 2 Property
  await expect(page.locator('#cat')).toHaveValue('hyd_circuit');
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
  await expect.poll(() => textUnderHighlight(page)).toContain('250/300');   // ...and it is on the value itself
  await expect(dialog.locator('li.match')).toContainText('250/300 Bar');   // matched spec flagged in the side panel
  await page.screenshot({ path: process.env['SHOT'] ?? 'e2e-viewer.png' });

  // non-number for a numeric property -> readable 400
  await dialog.getByRole('button', { name: 'Close' }).click();
  await page.locator('#val').fill('abc');
  await page.getByRole('button', { name: 'Go', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('is not a number');
});

// AT-3 in the browser: nearest cylinders by bore, with the reuse list, and the BOM table in the viewer.
test('cylinder BOM: bore 80 -> the 80x56 cylinders with reused_on; BOM row highlight', async ({ page }) => {
  await page.goto('/');
  await page.locator('#cat').selectOption('bom_cylinder');
  await expect(page.locator('#prop')).toContainText('Bore (mm)');
  await page.locator('#prop').selectOption({ label: 'Bore (mm)' });
  await expect(page.getByRole('button', { name: /^80 mm/ })).toContainText('· 4');

  await page.getByRole('button', { name: /^80 mm/ }).click();
  await expect(page.locator('#val')).toHaveValue('80');
  await page.getByRole('button', { name: 'Go', exact: true }).click();

  const rows = page.locator('.row-result');
  for (const i of [0, 1, 2, 3]) await expect(rows.nth(i)).toContainText('Δ 0');
  await expect(rows.nth(4)).not.toContainText('Δ 0');
  const hit = rows.filter({ hasText: 'HAS90264' });
  await expect(hit).toContainText('Reused on');
  for (const code of ['PP60050', 'PP60053', 'PP60056']) await expect(hit.locator('.code', { hasText: code })).toBeVisible();
  await expect(rows.filter({ hasText: 'HA90471' })).not.toContainText('Reused on');   // its title has no list

  // viewer: highlight on the matched bore in the title block, then jump to a BOM row
  await hit.locator('.name').click();
  const dialog = page.locator('app-viewer-dialog');
  const hl = dialog.locator('.ds-highlight');
  await expect(hl).toBeInViewport({ ratio: 0.9, timeout: 60_000 });
  const rowsInPanel = dialog.locator('.bom tbody tr');
  await expect(rowsInPanel).toHaveCount(8);
  await expect.poll(() => textUnderHighlight(page)).toContain('Platen Wheel Gripper');   // on the title block, at "Ø80 x 56"
  await rowsInPanel.nth(5).click();                                                // 145.01~145.03, Minimess Test Coupling
  await expect(dialog.locator('.bom tbody tr.match')).toHaveCount(1);
  await expect.poll(() => textUnderHighlight(page)).toContain('2103-01-18.00');    // on that row in the PDF
  if (process.env['SHOT_BOM']) await page.screenshot({ path: process.env['SHOT_BOM'] });
});

// M6: motor datasheet and JB cover (coarse filters), highlight on the right words.
test('motor datasheet and JB cover: nearest value, highlight on the printed cell', async ({ page }) => {
  await page.goto('/');

  await page.locator('#cat').selectOption('motor_datasheet');
  await page.locator('#prop').selectOption({ label: 'Rated output (kW)' });
  await expect(page.getByRole('button', { name: /^110 kW/ })).toContainText('· 2');
  await page.locator('#val').fill('100');
  await page.getByRole('button', { name: 'Go', exact: true }).click();
  const rows = page.locator('.row-result');
  await expect(rows.first()).toContainText('110 kW');
  await expect(rows.first()).toContainText('Δ 10');
  await rows.first().locator('.name').click();
  const dialog = page.locator('app-viewer-dialog');
  await expect(dialog.locator('.ds-highlight')).toBeInViewport({ ratio: 0.9, timeout: 60_000 });
  await expect.poll(() => textUnderHighlight(page)).toContain('Rated Output');
  await expect.poll(() => textUnderHighlight(page)).toContain('110');
  await dialog.getByRole('button', { name: 'Close' }).click();

  await page.locator('#cat').selectOption('jb_doc');
  await page.locator('#prop').selectOption({ label: 'Enclosure W x H x D (mm)' });
  await page.locator('#val').fill('350');
  await page.getByRole('button', { name: 'Go', exact: true }).click();
  await expect(rows.first()).toContainText('(D)');
  await expect(rows.first()).toContainText('Δ 0');
  await rows.first().locator('.name').click();
  await expect(dialog.locator('.ds-highlight')).toBeInViewport({ ratio: 0.9, timeout: 60_000 });
  await expect.poll(() => textUnderHighlight(page)).toContain('Enclosures');
  if (process.env['SHOT_JB']) await page.screenshot({ path: process.env['SHOT_JB'] });
});
