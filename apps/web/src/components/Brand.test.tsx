import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen } from '@testing-library/react';
import { ForgeMark } from '@forge/design-system';
import { describe, expect, it } from 'vitest';
import { Shell } from './Shell';

const asset = (name: string) =>
  readFileSync(resolve(process.cwd(), 'public/brand', name), 'utf8');

describe('FORGE brand mark', () => {
  it('draws the F as stem, two sheared arms and the sketch-origin dot, hidden from assistive tech', () => {
    const { container } = render(<ForgeMark />);
    const svg = container.querySelector('svg')!;
    expect(svg).toHaveAttribute('aria-hidden', 'true');
    expect(svg).toHaveAttribute('viewBox', '0 0 32 32');
    expect(svg.querySelectorAll('path')).toHaveLength(3);
    expect(svg.querySelectorAll('circle')).toHaveLength(1);
  });
  it('keeps the shipped SVG sources geometrically identical to the component', () => {
    const { container } = render(<ForgeMark />);
    const paths = [...container.querySelectorAll('path')].map((p) =>
      p.getAttribute('d'),
    );
    for (const file of [
      'forge-mark.svg',
      'forge-mark-mono.svg',
      'forge-wordmark.svg',
    ]) {
      const source = asset(file);
      for (const d of paths) expect(source).toContain(`d="${d}"`);
      expect(source).toContain('<circle cx="22" cy="25" r="3"');
      expect(source).toContain('aria-label="FORGE"');
    }
    // The app icon scales the same geometry onto a rounded tile; no raster data.
    const icon = asset('forge-icon.svg');
    for (const d of paths) expect(icon).toContain(`d="${d}"`);
    for (const file of ['forge-mark.svg', 'forge-icon.svg'])
      expect(asset(file)).not.toMatch(/<image|data:image/);
  });
  it('labels the header brand link for screen readers', () => {
    render(
      <Shell onOnboarding={() => {}} onNotify={() => {}}>
        <p>body</p>
      </Shell>,
    );
    const link = screen.getByRole('link', { name: 'Forge workspace' });
    expect(link.querySelector('.forge-mark')).not.toBeNull();
    expect(link).toHaveTextContent('FORGE');
  });
});
