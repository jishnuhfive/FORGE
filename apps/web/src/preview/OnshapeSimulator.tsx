import { useState } from 'react';
import { Button, TooltipProvider } from '@forge/design-system';
import { CadContext } from '../components/CadContext';
import { createBridge } from '../onshape/bridge';
import { parseLaunch } from '../onshape/context';
import { selectionLabel, standaloneState } from '../onshape/model';
import type { ClientState, SelectionEntity } from '../onshape/model';
import { usePreferences } from '../lib/preferences';

// Presentation fixtures only, including multi-selection beyond the live adapter.
// This does not install a trusted local origin in the production bridge.
const documentId = 'a'.repeat(24);
const elementId = 'c'.repeat(24);
const search = `?server=https://cad.onshape.com&documentId=${documentId}&workspaceOrVersion=w&workspaceOrVersionId=${'b'.repeat(24)}&elementId=${elementId}`;
const launch = () => parseLaunch(search, true, true);
export default function OnshapeSimulator() {
  const [state, setState] = useState<ClientState>(standaloneState);
  const probe = (data: unknown, origin: string) => {
    let receive: ((event: MessageEvent<unknown>) => void) | undefined;
    const parent = {
      postMessage: () => {
        /* no window or network access */
      },
    };
    const bridge = createBridge({
      parent,
      embedded: true,
      extension: true,
      search,
      referrer: '',
      focus: () => {},
      listen: (listener) => {
        receive = listener;
        return () => {
          receive = undefined;
        };
      },
    });
    bridge.start();
    const before = bridge.snapshot();
    receive?.({
      data,
      origin,
      source: parent,
    } as unknown as MessageEvent<unknown>);
    setResult(
      bridge.snapshot() === before
        ? 'Boundary probe rejected; displayed context unchanged'
        : 'Boundary probe accepted',
    );
    bridge.stop();
  };
  const [authUnavailable, setAuthUnavailable] = useState(false);
  const [result, setResult] = useState('No scenario applied');
  const { preferences, setPreferences } = usePreferences();
  const select = (entities: SelectionEntity[]) => {
    const base = state.context ? state : launch();
    const selection = {
      status: 'available' as const,
      entities,
      sourceElementId: base.context?.elementId,
    };
    setState({ ...base, status: 'EMBEDDED_CONNECTED', selection });
    setResult(`Internal UI fixture: ${selectionLabel(selection)}`);
  };
  const switchContext = (key: 'documentId' | 'elementId') => {
    const next = new URLSearchParams(search);
    next.set(key, 'd'.repeat(24));
    setState(parseLaunch(`?${next}`, true, true));
    setResult('New launch resets selection');
  };
  return (
    <TooltipProvider>
      <main className="feature extension-simulator">
        <span className="eyebrow">DEVELOPMENT ONLY · SYNTHETIC</span>
        <h1>Onshape context simulator</h1>
        <p>
          Selection counts below are internal presentation fixtures. Multiple
          selection remains a preview; the live adapter supports single faces,
          single edges and clearing. This page cannot authenticate or
          communicate with Onshape.
        </p>
        <label htmlFor="simulator-theme">Theme</label>
        <select
          id="simulator-theme"
          value={preferences.theme}
          onChange={(event) =>
            setPreferences({
              ...preferences,
              theme: event.target.value === 'dark' ? 'dark' : 'light',
            })
          }
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="system">System</option>
        </select>
        <div className="simulator-actions">
          <Button onClick={() => setState(standaloneState)}>Standalone</Button>
          <Button onClick={() => setState(parseLaunch('', true, true))}>
            Initializing
          </Button>
          <Button onClick={() => setState(launch())}>
            Valid launch context
          </Button>
          <Button
            onClick={() =>
              setState(parseLaunch(`${search}&documentId=bad`, true, true))
            }
          >
            Invalid context
          </Button>
          <Button
            onClick={() =>
              setState(
                parseLaunch(
                  search.replace(
                    'https://cad.onshape.com',
                    'https://untrusted.example',
                  ),
                  true,
                  true,
                ),
              )
            }
          >
            Untrusted server
          </Button>
          <Button onClick={() => select([])}>No selection</Button>
          <Button onClick={() => select([{ type: 'face' }])}>
            Single face
          </Button>
          <Button onClick={() => select([{ type: 'edge' }, { type: 'edge' }])}>
            Multiple edges
          </Button>
          <Button onClick={() => select([])}>Clear selection</Button>
          <Button onClick={() => switchContext('elementId')}>
            Change element
          </Button>
          <Button onClick={() => switchContext('documentId')}>
            Change document
          </Button>
          <Button
            onClick={() =>
              setState({
                ...state,
                selection: { status: 'stale', entities: [] },
              })
            }
          >
            Stale context
          </Button>
          <Button
            onClick={() =>
              probe({ messageName: 'show' }, 'https://untrusted.example')
            }
          >
            Invalid message origin
          </Button>
          <Button
            onClick={() =>
              probe({ messageName: ['show'] }, 'https://cad.onshape.com')
            }
          >
            Malformed message
          </Button>
          <Button
            onClick={() =>
              probe(
                { messageName: 'contextChanged' },
                'https://cad.onshape.com',
              )
            }
          >
            Unsupported message
          </Button>
          <Button onClick={() => setAuthUnavailable(!authUnavailable)}>
            Auth unavailable
          </Button>
        </div>
        {authUnavailable && (
          <p role="status" className="notice">
            Preview: your Forge session is unavailable in this panel. Open Forge
            in a new tab, then check the panel session.
          </p>
        )}
        <h2>Panel preview</h2>
        <CadContext context={{ kind: 'live', state }} />
        <p role="status" className="small muted">
          {result}
        </p>
        <p className="small muted">
          Invalid origin, malformed message, unsupported message, and
          cross-origin iframe behavior are exercised by the bridge tests and
          browser fixtures. No development postMessage bypass exists.
        </p>
        <a href="/">Back to Forge</a>
      </main>
    </TooltipProvider>
  );
}
