import { Badge, EmptyState, Tabs } from '@forge/design-system';
import { Clock3 } from 'lucide-react';
import { useState } from 'react';
import type { HistoryEntry } from '../lib/types';

const categories: { id: HistoryEntry['kind']; label: string }[] = [
  { id: 'project', label: 'Projects' },
  { id: 'conversation', label: 'Conversations' },
  { id: 'run', label: 'Agent runs' },
  { id: 'operation', label: 'CAD operations' },
  { id: 'validation', label: 'Reports' },
  { id: 'activity', label: 'Activity' },
];
export function History({ entries = [] }: { entries?: HistoryEntry[] }) {
  const [tab, setTab] = useState('project');
  return (
    <div className="feature history-feature">
      <div className="section-kicker">
        <span>PROJECT RECORD</span>
        <Badge>{entries.length ? 'Mock history' : 'Integration planned'}</Badge>
      </div>
      <div className="feature-heading">
        <h1>Projects & activity</h1>
        <p>
          A record of requirements, plans, operations and the evidence behind
          them.
        </p>
      </div>
      <Tabs
        label="History category"
        value={tab}
        onValueChange={setTab}
        items={categories.map((category) => ({
          ...category,
          content: (
            <div className="history-list">
              {entries.filter((entry) => entry.kind === category.id).length ===
              0 ? (
                <EmptyState
                  title="No history yet"
                  description="Your projects and verified activity will appear here when backend persistence is available."
                  icon={<Clock3 />}
                />
              ) : (
                entries
                  .filter((entry) => entry.kind === category.id)
                  .map((entry) => (
                    <article key={entry.id}>
                      <span className="timeline-dot" aria-hidden="true" />
                      <div>
                        <h2>{entry.title}</h2>
                        <p>{entry.detail}</p>
                        <span className="mono small muted">{entry.time}</span>
                      </div>
                    </article>
                  ))
              )}
            </div>
          ),
        }))}
      />
    </div>
  );
}
