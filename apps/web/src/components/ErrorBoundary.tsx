import { Component } from 'react';
import type { ReactNode } from 'react';
import { Button, ErrorState } from '@forge/design-system';

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="feature">
        <ErrorState
          title="Something went wrong"
          description="The interface could not be loaded. No CAD operation was performed."
        >
          <Button onClick={() => window.location.reload()}>
            Reload workspace
          </Button>
        </ErrorState>
      </main>
    ) : (
      this.props.children
    );
  }
}
