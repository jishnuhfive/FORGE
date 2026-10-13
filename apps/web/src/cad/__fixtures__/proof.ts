import type { ReadProof } from '../api';
// Invented compact Forge response, never a live Onshape capture.
export const syntheticProof: ReadProof = {
  schema_version: 'forge-cad-read-v1',
  request_id: '1'.repeat(32),
  captured_at: '2026-10-10T12:00:00+00:00',
  consistency: 'unverified',
  has_mass: true,
  features: {
    status: 'success',
    code: 'ok',
    count: 2,
    retry_after_seconds: null,
  },
  parts: { status: 'success', code: 'ok', count: 1, retry_after_seconds: null },
  bodies: {
    status: 'success',
    code: 'ok',
    count: 1,
    retry_after_seconds: null,
  },
  mass: { status: 'success', code: 'ok', count: 1, retry_after_seconds: null },
};
