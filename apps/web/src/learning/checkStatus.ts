import type { Status } from './check';

// Shared wording and tone for deterministic statuses, so a check result and an
// Ask Forge answer always describe the same status the same way.
export const statusTone = {
  PASS: 'pass',
  FAIL: 'fail',
  WARNING: 'warning',
  UNVERIFIED: 'unverified',
} as const;
export const statusLabel: Record<Status, string> = {
  PASS: 'Verified',
  FAIL: 'Not yet',
  WARNING: 'Worth a look',
  UNVERIFIED: 'Can’t verify',
};
