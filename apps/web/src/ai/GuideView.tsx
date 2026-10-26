import { useId, useRef, useState } from 'react';
import { Badge, Button } from '@forge/design-system';
import { ArrowDown, Check, ChevronRight } from 'lucide-react';
import type { Guide } from './api';

function Chips({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="guide-chips" aria-label={title}>
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

/** A collapsed-by-default section. Content stays in the document for every reader. */
function Fold({
  title,
  count,
  children,
}: {
  title: string;
  count?: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <section className="guide-fold" data-open={open}>
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((value) => !value)}
        >
          <span>{title}</span>
          {count !== undefined && <span className="guide-count">{count}</span>}
          <ChevronRight size={14} aria-hidden="true" />
        </button>
      </h3>
      <div id={id} className="guide-body" inert={!open}>
        <div>{children}</div>
      </div>
    </section>
  );
}

function ItemList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <Fold title={title} count={items.length}>
      <ul className="guide-list" aria-label={title}>
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </Fold>
  );
}

/**
 * Presentation of model-written general Onshape guidance. It states nothing about
 * the open Part Studio and is always labelled so; evidence is rendered elsewhere.
 * Every step stays in the document: the layout only chooses what to show first.
 * Step progress is the reader's own and is never a CAD check.
 */
export function GuideView({
  guide,
  note,
  onAsk,
  askDisabled = false,
}: {
  guide: Guide;
  note?: string;
  onAsk?: (question: string) => void;
  askDisabled?: boolean;
}) {
  const [open, setOpen] = useState<Set<number>>(() => new Set([0]));
  const [done, setDone] = useState<Set<number>>(() => new Set());
  const headers = useRef<(HTMLButtonElement | null)[]>([]);
  const prefix = useId();
  const total = guide.steps.length;
  const allOpen = total > 0 && open.size === total;
  const toggle = (index: number) =>
    setOpen((previous) => {
      const next = new Set(previous);
      if (!next.delete(index)) next.add(index);
      return next;
    });
  const advance = (index: number) => {
    setDone((previous) => new Set(previous).add(index));
    setOpen((previous) => {
      const next = new Set(previous);
      next.delete(index);
      if (index + 1 < total) next.add(index + 1);
      return next;
    });
    const next = headers.current[index + 1];
    if (next) {
      const reduce =
        window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ===
        true;
      next.focus({ preventScroll: true });
      next.scrollIntoView?.({
        block: 'nearest',
        behavior: reduce ? 'auto' : 'smooth',
      });
    }
  };
  return (
    <div className="guide">
      <h2 className="response-heading">{guide.title}</h2>
      <Badge>General guidance · not from your model</Badge>
      <p className="draft-text guide-summary">{guide.summary}</p>
      {guide.key_dimensions.length > 0 && (
        <Chips title="Key dimensions" items={guide.key_dimensions} />
      )}
      {guide.assumptions.length > 0 && (
        <Fold title="Assumptions to confirm" count={guide.assumptions.length}>
          <ul className="guide-list">
            {guide.assumptions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </Fold>
      )}
      {guide.questions.length > 0 && (
        <section className="guide-block" aria-label="Questions for you">
          <h3>Questions before you start</h3>
          <ol>
            {guide.questions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ol>
        </section>
      )}
      {guide.explanation && (
        <p className="draft-text guide-explanation">{guide.explanation}</p>
      )}
      {total > 0 && (
        <>
          <div className="guide-progress">
            <div
              className="guide-meter"
              role="progressbar"
              aria-label="Your progress through the steps"
              aria-valuemin={0}
              aria-valuemax={total}
              aria-valuenow={done.size}
              aria-valuetext={`${done.size} of ${total} steps marked done by you`}
            >
              <span style={{ width: `${(done.size / total) * 100}%` }} />
            </div>
            <span>
              {done.size} of {total} done
            </span>
            <button
              type="button"
              className="guide-toggle"
              onClick={() =>
                setOpen(allOpen ? new Set() : new Set(guide.steps.keys()))
              }
            >
              {allOpen ? 'Collapse all' : 'Show all steps'}
            </button>
          </div>
          <ol className="guide-steps" aria-label="Modeling steps">
            {guide.steps.map((step, index) => {
              const expanded = open.has(index);
              const finished = done.has(index);
              const region = `${prefix}-${index}`;
              return (
                <li
                  key={index}
                  className="guide-step"
                  data-open={expanded}
                  data-done={finished}
                >
                  <h3>
                    <button
                      type="button"
                      ref={(node) => {
                        headers.current[index] = node;
                      }}
                      aria-expanded={expanded}
                      aria-controls={region}
                      onClick={() => toggle(index)}
                    >
                      <span className="guide-number" aria-hidden="true">
                        {finished ? <Check size={13} /> : index + 1}
                      </span>
                      <span className="guide-step-title">{step.title}</span>
                      {finished && (
                        <span className="sr-only">Marked done by you.</span>
                      )}
                      <ChevronRight size={14} aria-hidden="true" />
                    </button>
                  </h3>
                  <div id={region} className="guide-body" inert={!expanded}>
                    <div className="guide-step-content">
                      <p className="guide-action">{step.action}</p>
                      {step.controls.length > 0 && (
                        <ul
                          className="guide-controls"
                          aria-label="Onshape controls"
                        >
                          {step.controls.map((item, at) => (
                            <li key={at}>{item}</li>
                          ))}
                        </ul>
                      )}
                      {step.parameters.length > 0 && (
                        <ul
                          className="guide-parameters"
                          aria-label="Values to enter"
                        >
                          {step.parameters.map((item, at) => (
                            <li key={at}>{item}</li>
                          ))}
                        </ul>
                      )}
                      <p className="guide-check">
                        <Check size={13} aria-hidden="true" />
                        <span>
                          <strong>Check:</strong> {step.check}
                        </span>
                      </p>
                      <details>
                        <summary>Why this matters</summary>
                        <p>{step.why}</p>
                      </details>
                      <div className="guide-next">
                        <Button
                          variant={index + 1 < total ? 'primary' : 'secondary'}
                          onClick={() => advance(index)}
                        >
                          {index + 1 < total ? (
                            <>
                              Done, next step
                              <ArrowDown size={14} aria-hidden="true" />
                            </>
                          ) : (
                            'Done'
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </>
      )}
      <ItemList title="Common mistakes" items={guide.mistakes} />
      <ItemList title="Final checklist" items={guide.checklist} />
      {guide.follow_ups.length > 0 && (
        <section className="guide-block" aria-label="Ask next">
          <h3>Ask next</h3>
          <ul className="guide-followups">
            {guide.follow_ups.map((item, index) => (
              <li key={index}>
                {onAsk ? (
                  <button
                    type="button"
                    disabled={askDisabled}
                    onClick={() => onAsk(item)}
                  >
                    {item}
                  </button>
                ) : (
                  item
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
      {note && <p className="small muted guide-note">{note}</p>}
    </div>
  );
}
