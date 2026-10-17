import { Suspense, lazy, useState, useSyncExternalStore } from 'react';
import {
  Button,
  Skeleton,
  Tabs,
  Toast,
  TooltipProvider,
} from '@forge/design-system';
import { BookOpen, PencilRuler, SlidersHorizontal } from 'lucide-react';
import { Shell } from './components/Shell';
import { Onboarding } from './components/Onboarding';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Design } from './features/Design';
import { Modify } from './features/Modify';
import { Learn } from './features/Learn';
import { Settings } from './features/Settings';
import { History } from './features/History';
import { usePreferences } from './lib/preferences';
import { AuthGate } from './auth/AuthGate';
import { useAuth } from './auth/context';
import { LearningProvider } from './learning/LearningProvider';
import { sampleResource } from './learning/catalog';
import { OnshapeProvider } from './onshape/OnshapeProvider';
import { useOnshapeContext } from './onshape/store';
import type { Mode } from './lib/types';

// Vite removes this branch and its fixtures from a production build.
const UiLab = import.meta.env.DEV
  ? lazy(() => import('./preview/UiLab'))
  : null;
const OnshapeSimulator = import.meta.env.DEV
  ? lazy(() => import('./preview/OnshapeSimulator'))
  : null;
const subscribe = (notify: () => void) => {
  window.addEventListener('hashchange', notify);
  return () => window.removeEventListener('hashchange', notify);
};
const snapshot = () => window.location.hash;

export function App() {
  const route = useSyncExternalStore(subscribe, snapshot);
  if (
    import.meta.env.DEV &&
    route === '#/onshape-simulator' &&
    OnshapeSimulator
  )
    return (
      <Suspense fallback={<p>Loading simulator…</p>}>
        <OnshapeSimulator />
      </Suspense>
    );
  if (import.meta.env.DEV && route === '#/lab') return <Workspace />;
  return (
    <OnshapeProvider>
      <AuthGate>
        <Workspace />
      </AuthGate>
    </OnshapeProvider>
  );
}

export function Workspace() {
  const auth = useAuth();
  // Identity rotation/disconnect tears down ephemeral learning; ordinary /api/me
  // refreshes with the same session and connection preserve it.
  const owner = `${auth?.me.csrf_token ?? 'local'}:${auth?.me.connection ?? 'local'}`;
  return sampleResource.status === 'ready' ? (
    <LearningProvider owner={owner} lesson={sampleResource.lesson}>
      <WorkspaceContent />
    </LearningProvider>
  ) : (
    <WorkspaceContent />
  );
}

function WorkspaceContent() {
  const client = useOnshapeContext();
  const route = useSyncExternalStore(subscribe, snapshot);
  const { preferences, setPreferences, storageAvailable } = usePreferences();
  const [mode, setMode] = useState<Mode>('design');
  const [introRequested, setIntroRequested] = useState(false);
  const [message, setMessage] = useState('');
  const [toastOpen, setToastOpen] = useState(false);
  const notify = (text: string) => {
    setMessage(text);
    setToastOpen(true);
  };
  const closeIntro = () => {
    setIntroRequested(false);
    setPreferences({ ...preferences, onboarded: true });
  };
  const standalone = route === '#/settings' || route === '#/history';
  const labActive = route === '#/lab' && UiLab !== null;
  return (
    <TooltipProvider delayDuration={400}>
      <ErrorBoundary>
        {labActive && UiLab ? (
          <Suspense
            fallback={
              <main className="feature">
                <Skeleton label="Loading development preview" />
              </main>
            }
          >
            <UiLab
              preferences={preferences}
              onPreferencesChange={setPreferences}
              storageAvailable={storageAvailable}
            />
          </Suspense>
        ) : (
          <Shell
            context={{ kind: 'live', state: client }}
            onOnboarding={() => setIntroRequested(true)}
            onNotify={notify}
          >
            {standalone ? (
              <main>
                <div className="page-nav">
                  <Button
                    variant="ghost"
                    onClick={() => {
                      window.location.hash = '/';
                    }}
                  >
                    ← Back to workspace
                  </Button>
                </div>
                {route === '#/settings' ? (
                  <Settings
                    preferences={preferences}
                    onChange={setPreferences}
                    storageAvailable={storageAvailable}
                  />
                ) : (
                  <History />
                )}
              </main>
            ) : (
              <Tabs
                label="Engineering mode"
                value={mode}
                onValueChange={(value) => {
                  if (
                    value === 'design' ||
                    value === 'modify' ||
                    value === 'learn'
                  )
                    setMode(value);
                }}
                items={[
                  {
                    id: 'design',
                    label: 'Design',
                    icon: <PencilRuler size={16} aria-hidden="true" />,
                    content: (
                      <main>
                        <Design />
                      </main>
                    ),
                  },
                  {
                    id: 'modify',
                    label: 'Modify',
                    icon: <SlidersHorizontal size={16} aria-hidden="true" />,
                    content: (
                      <main>
                        <Modify />
                      </main>
                    ),
                  },
                  {
                    id: 'learn',
                    label: 'Learn',
                    icon: <BookOpen size={16} aria-hidden="true" />,
                    content: (
                      <main>
                        <Learn />
                      </main>
                    ),
                  },
                ]}
              />
            )}
          </Shell>
        )}
        <Onboarding
          open={introRequested || (!preferences.onboarded && !labActive)}
          onClose={closeIntro}
        />
        <Toast message={message} open={toastOpen} onOpenChange={setToastOpen} />
      </ErrorBoundary>
    </TooltipProvider>
  );
}
