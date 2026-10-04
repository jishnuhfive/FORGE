import { Badge, Panel } from '@forge/design-system';
import { Box, Unplug } from 'lucide-react';
import type { CadContext as Context } from '../lib/types';

export function CadContext({ context }: { context: Context }) {
  return (
    <Panel title="CAD context" action={<Box size={15} aria-hidden="true" />}>
      {context.kind === 'preview' ? (
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
          <Badge>Integration planned</Badge>
        </div>
      )}
    </Panel>
  );
}
