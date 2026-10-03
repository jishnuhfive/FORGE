import type { ReactNode } from 'react';

export function StatusBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600">
      {children}
    </span>
  );
}
