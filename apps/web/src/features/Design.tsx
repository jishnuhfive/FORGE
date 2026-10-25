import { Badge, Button, Card, ForgeMark } from '@forge/design-system';
import { ArrowRight } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../auth/context';
import { Analysis } from '../ai/Analysis';
import { Create } from '../create/Create';
import { PromptComposer } from '../components/PromptComposer';
import { useOnshapeContext } from '../onshape/store';
import { revisionId } from '../onshape/model';

export function Design({
  preview = false,
  onSubmit,
}: {
  preview?: boolean;
  onSubmit?: (text: string) => void;
}) {
  const [draft, setDraft] = useState('');
  const [creating, setCreating] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const client = useOnshapeContext();
  const auth = useAuth();
  const contextLabel = client.context
    ? client.context.revision.kind === 'workspace'
      ? 'Onshape workspace context'
      : 'Onshape version context · messaging unverified'
    : client.status === 'STANDALONE'
      ? 'Not inside Onshape'
      : client.status === 'UNTRUSTED_ORIGIN'
        ? 'Onshape origin could not be verified'
        : client.status === 'EMBEDDED_CONTEXT_ERROR'
          ? 'Document context unavailable'
          : 'Waiting for document context';
  if (auth && !preview && client.status !== 'STANDALONE') {
    const context = client.context;
    const available =
      ['EMBEDDED_CONNECTED', 'EMBEDDED_INITIALIZING'].includes(client.status) &&
      context?.revision.kind === 'workspace' &&
      context.server === 'https://cad.onshape.com' &&
      (!context.elementType || context.elementType === 'partStudio') &&
      auth.me.connection === 'connected' &&
      auth.me.csrf_token &&
      !['stale', 'unavailable'].includes(client.selection.status);
    const selection =
      client.selection.status !== 'available'
        ? 'unknown'
        : client.selection.entities.length === 0
          ? 'none'
          : client.selection.entities[0]?.type === 'face'
            ? 'FACE'
            : client.selection.entities[0]?.type === 'edge'
              ? 'EDGE'
              : 'unknown';
    const key = context
      ? [
          context.documentId,
          context.revision.kind,
          revisionId(context),
          context.elementId,
          context.server,
          context.microversionId ?? '',
          auth.me.csrf_token,
        ].join(':')
      : '';
    return (
      <div className="feature design-feature">
        <h1 className="sr-only">Design workspace</h1>
        {available && context && auth.me.csrf_token ? (
          <>
            <div className="design-mode" role="group" aria-label="Design mode">
              <Button
                variant={creating ? 'secondary' : 'primary'}
                aria-pressed={!creating}
                disabled={createBusy}
                onClick={() => setCreating(false)}
              >
                Ask
              </Button>
              <Button
                variant={creating ? 'primary' : 'secondary'}
                aria-pressed={creating}
                onClick={() => setCreating(true)}
              >
                Create
              </Button>
            </div>
            {/* Ask stays mounted; Create unmounts, so Ask is locked while it is busy. */}
            <div hidden={creating}>
              <Analysis
                key={key}
                context={context}
                csrf={auth.me.csrf_token}
                selection={selection}
              />
            </div>
            {creating && (
              <Create
                key={key}
                context={context}
                csrf={auth.me.csrf_token}
                onBusyChange={setCreateBusy}
              />
            )}
          </>
        ) : (
          <p role="status" className="notice">
            Open a current workspace Part Studio inside Onshape with a connected
            account to ask Forge.
          </p>
        )}
      </div>
    );
  }
  return (
    <div className="feature design-feature">
      <div className="design-intro">
        <ForgeMark />
        <h1>Ask about this Part Studio</h1>
        <p>Understand the model. Explore an approach.</p>
        <Badge>{preview ? 'Mock preview' : 'Local design draft'}</Badge>
      </div>
      <PromptComposer
        context={preview ? 'Mock context · 1 face' : contextLabel}
        label="Design prompt"
        placeholder="Ask an engineering question…"
        onSubmit={(text) => {
          setDraft(text);
          onSubmit?.(text);
        }}
        showSuggestions
      />
      <p className="local-notice">
        {preview
          ? 'Development sample only. No AI runs and no CAD changes.'
          : 'Local draft only. Open Forge inside Onshape to use read-only AI.'}
      </p>
      {draft && (
        <Card className="draft-card">
          <span className="eyebrow">Your local draft</span>
          <p className="draft-text">{draft}</p>
          <p className="muted small">
            This text has not been sent to a service or converted into
            requirements.
          </p>
          <Button onClick={() => setDraft('')}>Dismiss draft</Button>
        </Card>
      )}
      {import.meta.env.DEV && !preview && (
        <a className="text-link preview-entry" href="#/lab">
          Explore the development preview
          <ArrowRight size={14} aria-hidden="true" />
        </a>
      )}
    </div>
  );
}
