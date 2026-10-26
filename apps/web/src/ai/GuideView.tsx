import { Badge } from '@forge/design-system';
import type { Guide } from './api';

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <section className="guide-block" aria-label={title}>
      <h3>{title}</h3>
      <ul>
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Presentation of model-written general Onshape guidance. It states nothing about
 * the open Part Studio and is always labelled so; evidence is rendered elsewhere.
 */
export function GuideView({ guide, note }: { guide: Guide; note?: string }) {
  return (
    <div className="guide">
      <h2 className="response-heading">{guide.title}</h2>
      <Badge>General guidance · not from your model</Badge>
      <p className="draft-text guide-summary">{guide.summary}</p>
      <List title="Key dimensions" items={guide.key_dimensions} />
      <List title="Assumptions to confirm" items={guide.assumptions} />
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
      {guide.steps.length > 0 && (
        <ol className="guide-steps" aria-label="Modeling steps">
          {guide.steps.map((step, index) => (
            <li key={index} className="guide-step">
              <h3>{step.title}</h3>
              <p>{step.action}</p>
              {step.controls.length > 0 && (
                <ul className="guide-controls" aria-label="Onshape controls">
                  {step.controls.map((item, at) => (
                    <li key={at}>{item}</li>
                  ))}
                </ul>
              )}
              {step.parameters.length > 0 && (
                <ul className="guide-parameters" aria-label="Values to enter">
                  {step.parameters.map((item, at) => (
                    <li key={at}>{item}</li>
                  ))}
                </ul>
              )}
              <p className="guide-check">
                <strong>Check:</strong> {step.check}
              </p>
              <details>
                <summary>Why this step matters</summary>
                <p>{step.why}</p>
              </details>
            </li>
          ))}
        </ol>
      )}
      <List title="Common mistakes" items={guide.mistakes} />
      <List title="Final checklist" items={guide.checklist} />
      <List title="Ask next" items={guide.follow_ups} />
      {note && <p className="small muted guide-note">{note}</p>}
    </div>
  );
}
