import { afterEach, expect, it, vi } from 'vitest';
import {
  developerToolsSnapshot,
  openDeveloperTools,
  setDeveloperToolsOpen,
  subscribeDeveloperTools,
} from './developerAccess';

afterEach(() => setDeveloperToolsOpen(false));
it('retains an open request made before the lazy view subscribes', () => {
  openDeveloperTools();
  const listener = vi.fn();
  const unsubscribe = subscribeDeveloperTools(listener);
  expect(developerToolsSnapshot()).toBe(true);
  setDeveloperToolsOpen(false);
  expect(listener).toHaveBeenCalledOnce();
  expect(developerToolsSnapshot()).toBe(false);
  unsubscribe();
});
it('removes the development view listener on cleanup', () => {
  const listener = vi.fn();
  const unsubscribe = subscribeDeveloperTools(listener);
  unsubscribe();
  openDeveloperTools();
  expect(listener).not.toHaveBeenCalled();
});
