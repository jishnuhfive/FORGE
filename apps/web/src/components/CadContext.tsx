import { Badge, Panel } from '@forge/design-system';
import { Box, Unplug } from 'lucide-react';
import { ReadCad } from '../cad/ReadCad';
import { selectionLabel, revisionId } from '../onshape/model';
import type { ClientState } from '../onshape/model';
import type { CadContext as Context } from '../lib/types';

export function CadContext({ context }: { context: Context }) {
  return (
    <Panel title="CAD context" action={<Box size={15} aria-hidden="true" />}>
      {context.kind === 'live' ? (
        <LiveContext state={context.state} />
      ) : context.kind === 'preview' ? (
        <>
          <Badge tone="accent">Mock context</Badge>
          <dl className="context-list">
            <div>
              <dt>Document</dt>
              <dd>{context.document}</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd>{context.workspace}</dd>
            </div>
            <div>
              <dt>Element</dt>
              <dd>{context.element}</dd>
            </div>
            <div>
              <dt>Selection</dt>
              <dd>{context.selection}</dd>
            </div>
          </dl>
        </>
      ) : (
        <div className="context-disconnected">
          <Unplug size={18} aria-hidden="true" />
          <strong>
            {context.kind === 'disconnected'
              ? 'Not connected to Onshape'
              : 'No document context'}
          </strong>
          <p>
            {context.kind === 'disconnected'
              ? 'Document and selection context will appear here when the integration is available.'
              : 'No Onshape document is available in this view.'}
          </p>
          <Badge>CAD integration planned</Badge>
        </div>
      )}
    </Panel>
  );
}

function LiveContext({ state }: { state: ClientState }) {
  const context = state.context;
  if (!context) {
    const status =
      state.status === 'STANDALONE'
        ? 'Not inside Onshape'
        : state.status === 'UNTRUSTED_ORIGIN'
          ? 'Onshape origin could not be verified'
          : state.status === 'EMBEDDED_CONTEXT_ERROR'
            ? 'Document context could not be validated'
            : 'Waiting for document context';
    return (
      <div className="context-disconnected" role="status">
        <Unplug size={18} aria-hidden="true" />
        <strong>{status}</strong>
        <p>
          {state.status === 'STANDALONE'
            ? 'Open Forge from an Onshape Part Studio to receive document context.'
            : 'Reopen the Forge panel from Onshape. If this continues, check the extension configuration.'}
        </p>
      </div>
    );
  }
  const short = (id: string) => `${id.slice(0, 6)}…${id.slice(-4)}`;
  return (
    <>
      <Badge tone="accent">Onshape launch context</Badge>
      <dl className="context-list">
        <div>
          <dt>Document</dt>
          <dd>{short(context.documentId)}</dd>
        </div>
        <div>
          <dt>Element</dt>
          <dd>{short(context.elementId)}</dd>
        </div>
        <div>
          <dt>
            {context.revision.kind === 'workspace' ? 'Workspace' : 'Version'}
          </dt>
          <dd>{short(revisionId(context))}</dd>
        </div>
        <div>
          <dt>Selection</dt>
          <dd>
            <span role="status">{selectionLabel(state.selection)}</span>
          </dd>
        </div>
      </dl>
      <p className="muted small">
        Document names are not supplied. Selection supports a single Part Studio
        face or edge.
      </p>
      <ReadCad state={state} />
      {state.status === 'EMBEDDED_INITIALIZING' && (
        <p className="small muted">
          {context.revision.kind === 'version'
            ? 'Version context is available. Client messaging for versions is not verified.'
            : 'Waiting for Onshape client messages.'}
        </p>
      )}
    </>
  );
}
