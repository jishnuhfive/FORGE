import type { ErrorCode } from './types';

export const errors: Record<ErrorCode, { title: string; description: string }> =
  {
    disconnected: {
      title: 'Onshape is disconnected',
      description:
        'Open account settings to reconnect Onshape. CAD context will be available in a later phase.',
    },
    'no-document': {
      title: 'No document context',
      description:
        'Open a supported Onshape document when the integration is available.',
    },
    permission: {
      title: 'Permission required',
      description:
        'You do not have permission to edit this workspace. Ask the document owner for access.',
    },
    network: {
      title: 'Network unavailable',
      description:
        'Your connection could not be reached. Reconnect before continuing.',
    },
    timeout: {
      title: 'Request timed out',
      description:
        'The result is unknown. CAD must be inspected before any future write is retried.',
    },
    'ai-unavailable': {
      title: 'AI temporarily unavailable',
      description:
        'The engineering assistant could not be reached. Your draft is still available in this session.',
    },
    'cad-failed': {
      title: 'CAD operation failed',
      description:
        'The operation could not be verified. Review the affected feature before continuing.',
    },
    'rate-limited': {
      title: 'Onshape rate limit reached',
      description:
        'Pause requests and try again after the service allows them.',
    },
    cancelled: {
      title: 'Operation cancelled',
      description:
        'No further steps will run. Any future partially completed CAD work must be inspected.',
    },
    unexpected: {
      title: 'Something went wrong',
      description:
        'This view could not be loaded. Return to the workspace and try again.',
    },
  };
