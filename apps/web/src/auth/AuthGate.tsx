import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Button, Skeleton } from '@forge/design-system';
import { ArrowUpRight, ShieldCheck } from 'lucide-react';
import { loadMe } from './api';
import type { Me } from './api';
import { useOnshapeContext } from '../onshape/store';
import { CadContext } from '../components/CadContext';
import { AuthContext } from './context';
import { usePreferences } from '../lib/preferences';

const notices: Record<string, string> = {
  authorization_denied:
    'Authorization was denied. Continue with Onshape when you’re ready to grant profile access.',
  authorization_error:
    'Onshape authorization could not be completed. Try again, or check your connection.',
  invalid_state:
    'This sign-in attempt expired or could not be verified. Start again in this browser.',
};

export function AuthGate({ children }: { children: ReactNode }) {
  usePreferences();
  const client = useOnshapeContext();
  const embedded = client.status !== 'STANDALONE';
  const [me, setMe] = useState<Me | null>(null);
  const [networkError, setNetworkError] = useState(false);
  const [authorizing, setAuthorizing] = useState(false);
  const [notice] = useState(
    () => notices[window.location.hash.replace('#/auth/', '')],
  );
  const revision = useRef(0);
  const pending = useRef<AbortController | null>(null);
  const cancelPending = useCallback(() => {
    ++revision.current;
    pending.current?.abort();
  }, []);
  const reload = useCallback(() => {
    const current = ++revision.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    return loadMe(controller.signal)
      .then((result) => {
        if (current === revision.current) {
          setMe(result);
          setNetworkError(false);
        }
      })
      .catch(() => {
        if (current === revision.current) setNetworkError(true);
      })
      .finally(() => window.clearTimeout(timeout));
  }, []);
  const endSession = (expired = false) => {
    cancelPending();
    setNetworkError(false);
    setMe({
      status: expired ? 'session_expired' : 'signed_out',
      configured: true,
      display_name: null,
      connection: null,
      csrf_token: null,
      verified_at: null,
    });
  };
  useEffect(() => {
    void reload();
    const refresh = () => {
      void reload();
    };
    window.addEventListener('focus', refresh);
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      cancelPending();
      window.removeEventListener('focus', refresh);
      window.clearInterval(timer);
    };
  }, [reload, cancelPending]);

  if (me?.status === 'authenticated') {
    return (
      <AuthContext.Provider value={{ me, reload, endSession }}>
        {networkError && (
          <div role="alert" className="notice">
            Forge is temporarily unreachable. Your local draft is still here.{' '}
            <Button
              onClick={() => {
                void reload();
              }}
            >
              Try again
            </Button>
          </div>
        )}
        {children}
      </AuthContext.Provider>
    );
  }
  return (
    <main className="auth-page">
      <div className="auth-card">
        <a className="wordmark" href="/" aria-label="Forge home">
          <span>FORGE</span>
        </a>
        <span className="eyebrow">YOUR ENGINEERING WORKSPACE</span>
        <h1>
          Engineering intelligence
          <br />
          inside Onshape.
        </h1>
        <p className="muted">
          Connect securely with your Onshape account to make this workspace
          yours.
        </p>
        {!me && !networkError ? (
          <Skeleton label="Checking your Forge session" />
        ) : (
          <>
            {networkError ? (
              <div role="alert" className="notice">
                <strong>We couldn’t reach Forge.</strong>
                <p>Check your connection and try again.</p>
                <Button
                  onClick={() => {
                    void reload();
                  }}
                >
                  Try again
                </Button>
              </div>
            ) : (
              <>
                {(notice || me?.status === 'session_expired') && (
                  <p role="status" className="notice">
                    {notice ??
                      'Your Forge session has expired. Sign in again to continue.'}
                  </p>
                )}
                {me?.configured ? (
                  <a
                    className="auth-continue"
                    href="/auth/onshape/start"
                    target="_top"
                    onClick={(event) => {
                      if (authorizing) event.preventDefault();
                      else setAuthorizing(true);
                    }}
                    aria-disabled={authorizing}
                  >
                    {authorizing ? 'Opening Onshape…' : 'Continue with Onshape'}
                    <ArrowUpRight size={17} aria-hidden="true" />
                  </a>
                ) : (
                  <p role="status" className="notice">
                    Onshape sign-in is awaiting server configuration. Contact
                    your Forge administrator to enable sign-in.
                  </p>
                )}
                {authorizing && (
                  <p role="status">
                    Authorizing with Onshape. Complete sign-in in the browser.
                  </p>
                )}
              </>
            )}
          </>
        )}
        {embedded && (me || networkError) && (
          <section aria-label="Embedded session" className="embedded-session">
            <h2>Panel session</h2>
            <p role="status">
              Your Forge session is unavailable in this panel. Sign in in a
              separate tab, then check again. Browser cookie restrictions may
              prevent this panel from sharing that session.
            </p>
            <Button
              onClick={() => {
                void reload();
              }}
            >
              Check panel session
            </Button>
            <CadContext context={{ kind: 'live', state: client }} />
          </section>
        )}
        <p className="small muted auth-security">
          <ShieldCheck size={17} aria-hidden="true" />
          Your Onshape password stays with Onshape.
        </p>
        <a
          className="text-link"
          href="/"
          target="_blank"
          rel="noopener noreferrer"
        >
          Open Forge in a new tab
        </a>
        <p className="small muted">
          If sign-in is blocked inside Onshape, use a separate tab. Embedded
          sessions may require third-party cookies.
        </p>
        {import.meta.env.DEV && (
          <a className="text-link" href="#/lab">
            Open development UI lab
          </a>
        )}
      </div>
      <span className="muted small">FORGE / PHASE 3 · Onshape extension</span>
    </main>
  );
}
