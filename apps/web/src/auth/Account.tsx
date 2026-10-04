import { useState } from 'react';
import { Badge, Button, Dialog, Panel } from '@forge/design-system';
import { useAuth } from './context';
import { mutateAccount } from './api';

const connectionCopy = {
  connected: 'Connected',
  disconnected: 'Reconnect required',
  revoked: 'Authorization revoked',
  error: 'Authorization error',
};

export function Account() {
  const auth = useAuth();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  if (!auth)
    return (
      <Panel title="Account">
        <p>UI lab preview. No account is signed in here.</p>
      </Panel>
    );
  const { me, reload, endSession } = auth;
  const perform = async (action: 'logout' | 'disconnect' | 'check') => {
    if (!me.csrf_token) return;
    setBusy(true);
    setMessage('');
    try {
      const path =
        action === 'logout'
          ? '/auth/logout'
          : action === 'disconnect'
            ? '/api/onshape/disconnect'
            : '/api/onshape/check';
      const status = await mutateAccount(path, me.csrf_token);
      if (status === 403)
        setMessage(
          'This request could not be verified. Reload Forge and try again.',
        );
      else if (status === 204)
        setMessage(
          action === 'disconnect'
            ? 'Forge removed its stored access. To revoke the grant in Onshape, open My account → Applications → Revoke.'
            : action === 'check'
              ? 'Onshape verified your connection.'
              : '',
        );
      else if (status !== 401)
        setMessage(
          'Your Onshape connection needs attention. Try again or reconnect.',
        );
      if (status === 204 && action === 'logout') endSession();
      else if (status === 401) endSession(true);
      else await reload();
    } catch {
      setMessage(
        'We couldn’t reach Forge. Check your connection and try again.',
      );
    } finally {
      setBusy(false);
      setConfirm(false);
    }
  };
  return (
    <Panel title="Account">
      <div className="profile-placeholder">
        <span className="avatar" aria-hidden="true">
          {me.display_name?.slice(0, 1)}
        </span>
        <div>
          <strong>{me.display_name}</strong>
          <p className="muted small">Onshape account</p>
        </div>
      </div>
      <div className="settings-row">
        <span>Onshape authorization</span>
        <Badge>{connectionCopy[me.connection ?? 'disconnected']}</Badge>
      </div>
      {me.connection === 'connected' ? (
        <p className="muted small">
          Status reflects the last successful verification. Check the connection
          to confirm access is still available.
        </p>
      ) : (
        <p className="notice">
          {me.connection === 'revoked'
            ? 'Onshape no longer accepts this authorization.'
            : me.connection === 'error'
              ? 'We couldn’t verify your authorization.'
              : 'Forge has no delegated access to your Onshape account.'}{' '}
          Reconnect to restore access.
        </p>
      )}
      <div className="action-bar">
        {me.connection !== 'connected' && (
          <a className="text-link" href="/auth/onshape/start" target="_top">
            Reconnect Onshape
          </a>
        )}
        {(me.connection === 'connected' || me.connection === 'error') && (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => {
              void perform('check');
            }}
          >
            Check connection
          </Button>
        )}
        {me.connection !== 'disconnected' && (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => setConfirm(true)}
          >
            Disconnect Onshape
          </Button>
        )}
        <Button
          variant="ghost"
          disabled={busy}
          onClick={() => {
            void perform('logout');
          }}
        >
          Sign out
        </Button>
      </div>
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      <Dialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Disconnect Onshape?"
        description="Forge will delete its stored tokens. This does not revoke the grant in Onshape or sign you out of Forge. To revoke remotely, open Onshape My account → Applications → Revoke."
      >
        <div className="action-bar">
          <Button
            disabled={busy}
            onClick={() => {
              void perform('disconnect');
            }}
          >
            Confirm disconnect
          </Button>
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => setConfirm(false)}
          >
            Keep connected
          </Button>
        </div>
      </Dialog>
    </Panel>
  );
}
