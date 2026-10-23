import { useState } from 'react';
import type { ReactNode, RefObject } from 'react';
import { Dialog, Dropdown, ForgeMark } from '@forge/design-system';
import { Box, Eye, MoreHorizontal, Search } from 'lucide-react';
import { openDeveloperTools } from '../onshape/developerAccess';
import { useAuth } from '../auth/context';
import { CadContext } from './CadContext';
import type { CadContext as Context } from '../lib/types';

export function Shell({
  children,
  context = { kind: 'disconnected' },
  onOnboarding,
  onNotify,
  brandMark,
  capability = 'Read-only',
  workspaceRef,
}: {
  children: ReactNode;
  context?: Context;
  onOnboarding: () => void;
  onNotify: (message: string) => void;
  brandMark?: ReactNode;
  capability?: 'Read-only' | 'Approval required';
  workspaceRef?: RefObject<HTMLDivElement | null>;
}) {
  const auth = useAuth();
  const [contextOpen, setContextOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="wordmark" href="#/" aria-label="Forge workspace">
          {brandMark ?? <ForgeMark />}
          <span>FORGE</span>
        </a>
        <div className="header-actions">
          <span className="capability glass-action">
            <Eye size={12} aria-hidden="true" />
            {capability}
          </span>
          <Dropdown
            label="Workspace menu"
            items={[
              {
                label: 'Appearance & settings',
                onSelect: () => {
                  window.location.hash = '/settings';
                },
              },
              { label: 'Privacy', onSelect: () => setPrivacyOpen(true) },
              ...(import.meta.env.DEV
                ? [{ label: 'Developer', onSelect: openDeveloperTools }]
                : []),
              { label: 'Introduction', onSelect: onOnboarding },
              {
                label: 'About Forge',
                onSelect: () =>
                  onNotify(
                    'Forge inspects and explains your CAD. Changes are planned; no engineering validation has run.',
                  ),
              },
            ]}
          >
            <MoreHorizontal size={16} aria-hidden="true" />
          </Dropdown>
        </div>
        <button
          type="button"
          className="document-area glass-action"
          onClick={(event) => {
            event.currentTarget.focus();
            setContextOpen(true);
          }}
          aria-label="View CAD context"
        >
          <Box size={16} aria-hidden="true" />
          <span>
            {context.kind === 'preview'
              ? context.document
              : context.kind === 'live' && context.state.context
                ? context.state.context.revision.kind === 'version'
                  ? 'Saved version'
                  : context.state.context.elementType === 'partStudio'
                    ? 'Current Part Studio'
                    : 'Current workspace'
                : 'Document context'}
          </span>
          <span className="context-action">
            <Search size={12} aria-hidden="true" />
            <span>CAD inspector</span>
          </span>
        </button>
      </header>
      <div className="shell-layout">
        <div
          className="workspace-pane"
          ref={workspaceRef}
          tabIndex={0}
          role="region"
          aria-label="Workspace content"
        >
          {auth && auth.me.connection !== 'connected' && (
            <p role="status" className="notice">
              Onshape needs to reconnect.{' '}
              <a href="#/settings">Open account settings</a>.
            </p>
          )}
          {children}
        </div>
      </div>
      <Dialog
        open={privacyOpen}
        onOpenChange={setPrivacyOpen}
        title="Your data"
        description="Explicit sends, read-only access"
      >
        <p>
          When you send, Forge shares your prompt, recent conversation and
          bounded CAD evidence with the configured hosted AI service. This
          conversation stays in the panel’s memory; provider retention policies
          apply.
        </p>
        <p className="muted small">
          Selection changes and CAD inspection do not start AI analysis. No
          engineering validation has run. Forge cannot change CAD.
        </p>
        <a
          className="text-link"
          href="#/settings"
          onClick={() => setPrivacyOpen(false)}
        >
          Privacy and appearance settings
        </a>
      </Dialog>
      <Dialog
        open={contextOpen}
        onOpenChange={setContextOpen}
        title="Document & selection"
        description="Current document, selection and CAD inspection."
      >
        <CadContext context={context} />
      </Dialog>
    </div>
  );
}
