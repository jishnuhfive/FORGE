import { useEffect, useState } from 'react';
import type { Preferences } from './types';

const key = 'forge.preferences.v1';
const defaults: Preferences = {
  theme: 'dark',
  units: 'metric',
  onboarded: false,
  printer: 'FDM printer',
  width: 220,
  depth: 220,
  height: 250,
  materials: 'PETG, PLA',
};
function readPreferences(): Preferences {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? 'null');
    if (!value || typeof value !== 'object') return defaults;
    const p = value as Record<string, unknown>;
    const dimension = (v: unknown, fallback: number) =>
      typeof v === 'number' && Number.isInteger(v) && v >= 1 && v <= 2000
        ? v
        : fallback;
    return {
      theme:
        p.theme === 'light' || p.theme === 'dark' || p.theme === 'system'
          ? p.theme
          : 'dark',
      reduceTransparency: p.reduceTransparency === true,
      units: p.units === 'imperial' ? 'imperial' : 'metric',
      onboarded: p.onboarded === true,
      printer:
        typeof p.printer === 'string' && p.printer.length <= 100
          ? p.printer
          : defaults.printer,
      width: dimension(p.width, defaults.width),
      depth: dimension(p.depth, defaults.depth),
      height: dimension(p.height, defaults.height),
      materials:
        typeof p.materials === 'string' && p.materials.length <= 100
          ? p.materials
          : defaults.materials,
    };
  } catch {
    return defaults;
  }
}
export function usePreferences() {
  const [preferences, setPreferences] = useState(readPreferences);
  const [storageAvailable, setStorageAvailable] = useState(true);
  const updatePreferences = (next: Preferences) => {
    try {
      localStorage.setItem(key, JSON.stringify(next));
      setStorageAvailable(true);
    } catch {
      setStorageAvailable(false);
    }
    setPreferences(next);
  };
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => {
      document.documentElement.dataset.theme =
        preferences.theme === 'system'
          ? media.matches
            ? 'dark'
            : 'light'
          : preferences.theme;
    };
    apply();
    document.documentElement.dataset.transparency =
      preferences.reduceTransparency ? 'reduced' : 'auto';
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, [preferences.theme, preferences.reduceTransparency]);
  return { preferences, setPreferences: updatePreferences, storageAvailable };
}
