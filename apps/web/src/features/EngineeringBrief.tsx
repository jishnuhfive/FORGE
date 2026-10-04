import { Badge, Button, Input } from '@forge/design-system';
import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import type { BriefSection } from '../lib/types';

export function EngineeringBrief({
  sections,
  onContinue,
}: {
  sections: BriefSection[];
  onContinue: () => void;
}) {
  const [values, setValues] = useState(sections);
  const [editing, setEditing] = useState(false);
  return (
    <div className="feature">
      <div className="section-kicker">
        <span>01 / REQUIREMENTS</span>
        <Badge tone="accent">Mock engineering brief</Badge>
      </div>
      <div className="feature-heading">
        <h1>Engineering brief</h1>
        <p>A shared definition of what this mechanism needs to do.</p>
      </div>
      <div className="row-between brief-toolbar">
        <span className="muted small">Synthetic camera slider example</span>
        <Button onClick={() => setEditing(!editing)}>
          {editing ? 'Done editing' : 'Edit locally'}
        </Button>
      </div>
      <div className="brief-sections">
        {values.map((section, sectionIndex) => (
          <section key={section.title} className="brief-section">
            <h2 className="eyebrow">{section.title}</h2>
            <dl>
              {section.values.map((value, valueIndex) => (
                <div className="brief-value" key={value.label}>
                  <dt>{value.label}</dt>
                  <dd>
                    {editing ? (
                      <Input
                        aria-label={`Edit ${value.label}`}
                        maxLength={180}
                        value={value.value}
                        onChange={(event) =>
                          setValues((current) =>
                            current.map((s, si) =>
                              si === sectionIndex
                                ? {
                                    ...s,
                                    values: s.values.map((v, vi) =>
                                      vi === valueIndex
                                        ? { ...v, value: event.target.value }
                                        : v,
                                    ),
                                  }
                                : s,
                            ),
                          )
                        }
                      />
                    ) : (
                      <strong>{value.value}</strong>
                    )}
                    <span className={`source-label source--${value.source}`}>
                      {value.source === 'confirmed'
                        ? 'Confirmed in sample'
                        : value.source === 'assumed'
                          ? 'Assumption · review needed'
                          : 'Missing · input needed'}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
      <p className="local-notice">
        Edits affect this preview only and are discarded when the view closes.
        The plan uses a separate fixed sample.
      </p>
      <div className="action-bar">
        <Button variant="primary" onClick={onContinue}>
          Review sample plan
          <ArrowRight size={14} aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
