import { expect, test } from '@playwright/test';
import { signedIn } from './auth-fixtures';
const brief = {
  kind: 'rect_plate_with_through_holes',
  width: { value: 60, unit: 'mm' },
  length: { value: 40, unit: 'mm' },
  thickness: { value: 10, unit: 'mm' },
  holes: [],
};
for (const mode of ['success', 'cancel', 'uncertain']) {
  test(`creation ${mode}: explicit approval and no automatic retry`, async ({
    page,
  }) => {
    let approvals = 0;
    await page.setViewportSize({ width: 360, height: 900 });
    await page.addInitScript(() =>
      localStorage.setItem(
        'forge.preferences.v1',
        JSON.stringify({ onboarded: true }),
      ),
    );
    await page.route('https://forge-create.test/**', async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/me') return route.fulfill({ json: signedIn });
      if (url.pathname === '/api/create/interpret')
        return route.fulfill({ json: { status: 'ready', brief } });
      if (url.pathname === '/api/create/plan')
        return route.fulfill({
          json: {
            brief,
            proposal_id: 'a'.repeat(43),
            digest: 'b'.repeat(64),
            plan: {
              steps: [
                { op: { operation: 'CREATE_SKETCH_RECT' } },
                { op: { operation: 'EXTRUDE_NEW' } },
              ],
            },
          },
        });
      if (url.pathname.endsWith('/approve')) {
        approvals++;
        expect(route.request().postDataJSON()).toEqual({
          digest: 'b'.repeat(64),
          brief_confirmed: true,
        });
        return route.fulfill({
          json: {
            state:
              mode === 'uncertain' ? 'execution_uncertain' : 'verified_success',
          },
        });
      }
      if (url.pathname.endsWith('/cancel'))
        return route.fulfill({ json: { state: 'cancelled' } });
      if (url.pathname.startsWith('/api/'))
        return route.fulfill({ status: 503, json: { detail: 'unavailable' } });
      return route.fulfill({
        response: await page.request.get(
          'http://127.0.0.1:4173' + url.pathname + url.search,
        ),
      });
    });
    await page.route('https://cad.onshape.com/forge-create-test', (route) =>
      route.fulfill({
        contentType: 'text/html',
        body: `<!doctype html><html lang="en"><title>Mock CAD host</title><iframe title="Forge" style="width:100%;height:850px;border:0" src="https://forge-create.test/extension?documentId=${'a'.repeat(24)}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${'c'.repeat(24)}&server=https://cad.onshape.com"></iframe></html>`,
      }),
    );
    await page.goto('https://cad.onshape.com/forge-create-test');
    const frame = page.frameLocator('iframe');
    await frame.getByText('Create editable CAD', { exact: true }).click();
    await frame
      .getByLabel('Creation request', { exact: true })
      .fill('Create a 60 by 40 by 10 mm plate with no holes.');
    await frame
      .getByRole('button', { name: 'Interpret creation request' })
      .click();
    await expect(frame.getByText(/Width 60 mm/)).toBeVisible();
    await frame
      .getByRole('button', { name: 'Prepare creation preview' })
      .click();
    const approve = frame.getByRole('button', {
      name: 'Approve creation once',
    });
    await expect(approve).toBeDisabled();
    expect(approvals).toBe(0);
    if (mode === 'cancel') {
      await frame.getByRole('button', { name: 'Cancel creation' }).click();
      await expect(frame.getByText(/Creation cancelled/)).toBeVisible();
      expect(approvals).toBe(0);
    } else {
      await frame.getByRole('checkbox').check();
      await approve.click();
      await expect(
        frame.getByText(
          mode === 'success'
            ? /Creation verified by fresh provider evidence/
            : /Creation did not complete/,
        ),
      ).toBeVisible();
      await expect(approve).toBeDisabled();
      expect(approvals).toBe(1);
    }
  });
}
