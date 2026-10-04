import { useState } from 'react';
import type { ReactNode } from 'react';
import {
  Badge,
  Button,
  Dialog,
  Dropdown,
  IconButton,
  Panel,
} from '@forge/design-system';
import {
  ArrowUpRight,
  BookOpen,
  Box,
  CircleHelp,
  FolderClock,
  MoreHorizontal,
  Settings2,
  Unplug,
} from 'lucide-react';
import { CadContext } from './CadContext';
import type { CadContext as Context } from '../lib/types';

export function Shell({
  children,
  context = { kind: 'disconnected' },
  onOnboarding,
  onNotify,
}: {
  children: ReactNode;
  context?: Context;
  onOnboarding: () => void;
  onNotify: (message: string) => void;
}) {
  const [contextOpen, setContextOpen] = useState(false);
  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="wordmark" href="#/" aria-label="Forge workspace">
          <svg viewBox="0 0 24 28" fill="none" aria-hidden="true">
            <path d="M3 3h19L16 9H9v5h10l-6 6H9v5H3z" fill="currentColor" />
          </svg>
          <span>FORGE</span>
        </a>
        <button
          type="button"
          className="document-area"
          onClick={(event) => {
            event.currentTarget.focus();
            setContextOpen(true);
          }}
          aria-label="View CAD context"
        >
          <Box size={15} aria-hidden="true" />
          <span>
            {context.kind === 'preview'
              ? context.document
              : 'Untitled workspace'}
          </span>
        </button>
        <div className="header-actions">
          <span className="connection-label">
            <Unplug size={13} aria-hidden="true" />
            Disconnected
          </span>
          <IconButton
            label="Settings"
            onClick={() => {
              window.location.hash = '/settings';
            }}
          >
            <Settings2 size={17} aria-hidden="true" />
          </IconButton>
          <Dropdown
            label="Workspace menu"
            items={[
              { label: 'Introduction', onSelect: onOnboarding },
              {
                label: 'Projects & activity',
                onSelect: () => {
                  window.location.hash = '/history';
                },
              },
              {
                label: 'About this foundation',
                onSelect: () =>
                  onNotify(
                    'Phase 1 UI foundation. No live AI, Onshape or CAD operations.',
                  ),
              },
            ]}
          >
            <MoreHorizontal size={17} aria-hidden="true" />
          </Dropdown>
        </div>
      </header>
      <div className="shell-layout">
        <aside className="app-sidebar" aria-label="Workspace navigation">
          <span className="eyebrow sidebar-label">WORKSPACE</span>
          <a
            className="sidebar-link"
            href="#/"
            aria-current={
              window.location.hash === '#/' || !window.location.hash
                ? 'page'
                : undefined
            }
          >
            <Box size={17} aria-hidden="true" />
            Engineering workspace
          </a>
          <a
            className="sidebar-link"
            href="#/history"
            aria-current={
              window.location.hash === '#/history' ? 'page' : undefined
            }
          >
            <FolderClock size={17} aria-hidden="true" />
            Projects & activity
          </a>
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <span className="eyebrow">BUILT FOR ONSHAPE</span>
              <p>
                Engineering intent.
                <br />
                Editable geometry.
                <br />
                Verifiable results.
              </p>
              <Badge>UI foundation</Badge>
            </div>
            <Button
              variant="ghost"
              onClick={(event) => {
                event.currentTarget.focus();
                onOnboarding();
              }}
            >
              <CircleHelp size={16} aria-hidden="true" />
              Getting started
            </Button>
            <a className="sidebar-link" href="#/settings">
              <Settings2 size={17} aria-hidden="true" />
              Settings
            </a>
          </div>
        </aside>
        <div className="workspace-pane">
          {children}
          <footer className="workspace-footer">
            <span>FORGE / PHASE 1</span>
            <span>No live integrations</span>
          </footer>
        </div>
        <aside className="context-rail" aria-label="Workspace context">
          <CadContext context={context} />
          <Panel title="Intent → evidence">
            <p className="muted small">
              A precise workflow for turning functional requirements into a
              reviewable design.
            </p>
            <div className="context-workflow">
              <span>
                01 <strong>Engineering brief</strong>
              </span>
              <span>
                02 <strong>Proposed plan</strong>
              </span>
              <span>
                03 <strong>Approved build</strong>
              </span>
              <span>
                04 <strong>Validation report</strong>
              </span>
            </div>
            <Badge>Future live workflow</Badge>
          </Panel>
          <Panel title="Keep design deliberate">
            <BookOpen size={19} aria-hidden="true" />
            <p className="muted small">
              Start with what the mechanism needs to do. Dimensions, inventory
              and manufacturing limits make intent concrete.
            </p>
            <button
              type="button"
              className="text-link"
              onClick={(event) => {
                event.currentTarget.focus();
                onOnboarding();
              }}
            >
              Explore the workflow
              <ArrowUpRight size={14} aria-hidden="true" />
            </button>
          </Panel>
          {import.meta.env.DEV && (
            <a className="text-link lab-link" href="#/lab">
              UI development lab
              <ArrowUpRight size={14} aria-hidden="true" />
            </a>
          )}
        </aside>
      </div>
      <Dialog
        open={contextOpen}
        onOpenChange={setContextOpen}
        title="Document & selection"
        description="Live Onshape context is not available in Phase 1."
      >
        <CadContext context={context} />
      </Dialog>
    </div>
  );
}
