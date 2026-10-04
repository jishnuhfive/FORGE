export type Connection = 'connected' | 'disconnected' | 'revoked' | 'error';
export type Me = {
  status: 'signed_out' | 'session_expired' | 'authenticated';
  configured: boolean;
  display_name: string | null;
  connection: Connection | null;
  csrf_token: string | null;
  verified_at: number | null;
};

export function parseMe(value: unknown): Me {
  if (!value || typeof value !== 'object')
    throw new Error('Invalid auth response');
  const data = value as Record<string, unknown>;
  const keys = [
    'status',
    'configured',
    'display_name',
    'connection',
    'csrf_token',
    'verified_at',
  ];
  if (
    Object.keys(data).some((key) => !keys.includes(key)) ||
    typeof data.status !== 'string' ||
    !['signed_out', 'session_expired', 'authenticated'].includes(data.status) ||
    typeof data.configured !== 'boolean' ||
    !(
      data.display_name === null ||
      (typeof data.display_name === 'string' && data.display_name.length <= 200)
    ) ||
    !(
      data.connection === null ||
      (typeof data.connection === 'string' &&
        ['connected', 'disconnected', 'revoked', 'error'].includes(
          data.connection,
        ))
    ) ||
    !(
      data.csrf_token === null ||
      (typeof data.csrf_token === 'string' &&
        /^[a-f0-9]{64}$/.test(data.csrf_token))
    ) ||
    !(
      data.verified_at === null ||
      (typeof data.verified_at === 'number' &&
        Number.isSafeInteger(data.verified_at) &&
        data.verified_at > 0)
    ) ||
    (data.status === 'authenticated' &&
      (!data.display_name || !data.connection || !data.csrf_token))
  ) {
    throw new Error('Invalid auth response');
  }
  return data as Me;
}

export async function loadMe(signal?: AbortSignal): Promise<Me> {
  const response = await fetch('/api/me', {
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
  });
  if (!response.ok) throw new Error('Account unavailable');
  return parseMe(await response.json());
}

export async function mutateAccount(
  path: '/auth/logout' | '/api/onshape/disconnect' | '/api/onshape/check',
  csrf: string,
): Promise<number> {
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'X-CSRF-Token': csrf },
  });
  return response.status;
}
