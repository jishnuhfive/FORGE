import { Separator, StatusBadge } from '@forge/design-system';
import { Wrench } from 'lucide-react';

export function App() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-slate-50 px-6 py-12 text-slate-950">
      <section aria-labelledby="forge-title" className="w-full max-w-sm">
        <Wrench
          aria-hidden="true"
          className="mb-6 size-7 text-slate-700"
          strokeWidth={1.5}
        />
        <h1 id="forge-title" className="text-3xl font-semibold tracking-tight">
          Forge
        </h1>
        <p className="mt-3 text-base leading-relaxed text-slate-600">
          AI engineering inside Onshape
        </p>
        <Separator className="my-6 h-px w-full bg-slate-200" />
        <StatusBadge>Phase 0 — Foundation</StatusBadge>
      </section>
    </main>
  );
}
