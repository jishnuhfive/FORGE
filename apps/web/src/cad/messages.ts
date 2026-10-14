import type { ReadCode } from './api';

export const messages: Record<
  ReadCode | 'session_check_required' | 'unsupported_context',
  string
> = {
  ok: 'Available',
  connection_required:
    'Onshape connection required. Reconnect in account settings.',
  read_permission_required:
    'Additional Onshape read permission required. Update the app permissions, then reconnect.',
  permission_or_access_required:
    'Onshape denied this read. Check the app’s document-read permission and your access to this document.',
  document_forbidden: 'Access to this document is forbidden.',
  not_found: 'Document or element not found.',
  rate_limited: 'Onshape API rate limit reached. Wait before reading again.',
  quota_exceeded:
    'Onshape API allowance reached. Check usage in Onshape Developer settings.',
  provider_unavailable: 'Onshape temporarily unavailable. Try again later.',
  provider_timeout: 'Onshape took too long to respond. Try again later.',
  invalid_response: 'Onshape returned data Forge could not verify.',
  response_too_large: 'This Part Studio exceeds the current read size limit.',
  redirect_rejected:
    'Onshape requested a redirect that Forge does not support.',
  unsupported_provider:
    'This Onshape server is not supported for CAD reads yet.',
  request_in_progress:
    'A CAD read is already in progress. Wait before reading again.',
  session_check_required:
    'Your Forge session needs to be checked. Reload the panel.',
  unsupported_context:
    'CAD reads currently support workspace Part Studios only.',
};
