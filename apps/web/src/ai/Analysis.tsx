import { Badge, Button, ForgeMark } from '@forge/design-system';
import type { ReactNode } from 'react';
import { ArrowRight, ChevronRight } from 'lucide-react';
import { useId } from 'react';
import { useEffect, useRef, useState } from 'react';
import { PromptComposer } from '../components/PromptComposer';
import type { OnshapeClientContext } from '../onshape/model';
import { modelSummary, responseTitle } from './presentation';
import { AiError, askForge, messages, stages } from './api';
import type {
  Answer,
  ErrorCode,
  HistoryMessage,
  Selection,
  Stage,
} from './api';

type Exchange = { prompt: string; result: Answer };

const symbols = {
  verified: '✓',
  unknown: '?',
  unverified: '◇',
  assumption: '◇',
};

function Evidence({
  items,
  capturedAt,
  fullAnswer,
}: {
  items: Answer['evidence'];
  capturedAt: string | null;
  fullAnswer?: string;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const valid = items.filter((item) => item.statement.trim());
  if (valid.length === 0) return null;
  const groups = (
    ['verified', 'unknown', 'unverified', 'assumption'] as const
  ).map((status) => ({
    status,
    items: valid.filter((item) => item.status === status),
  }));
  return (
    <div className="ai-evidence-panel">
      <Button
        variant="ghost"
        className="evidence-trigger glass-action"
        aria-label={open ? 'Hide evidence' : 'Evidence'}
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen((value) => !value)}
      >
        <span>{open ? 'Hide evidence' : 'Evidence'}</span>
        <span className="evidence-count" aria-hidden="true">
          {valid.length}
        </span>
        <ChevronRight
          className={open ? 'disclosure-icon is-open' : 'disclosure-icon'}
          size={12}
          aria-hidden="true"
        />
      </Button>
      {open && (
        <div id={id} className="evidence-content">
          <ul className="ai-evidence" aria-label="Evidence">
            {groups.flatMap((group) =>
              group.items.map((item, index) => (
                <li key={item.id}>
                  {index === 0 && (
                    <span
                      className={`evidence-status evidence-status--${group.status}`}
                    >
                      <span aria-hidden="true">{symbols[group.status]}</span>
                      <Badge>{group.status}</Badge>
                    </span>
                  )}
                  <span>{item.statement}</span>
                </li>
              )),
            )}
          </ul>
          {fullAnswer && (
            <div className="evidence-original">
              <h3>Full answer</h3>
              <p className="draft-text">{fullAnswer}</p>
            </div>
          )}
          {capturedAt && (
            <p className="small muted">
              Evidence captured{' '}
              <time dateTime={capturedAt}>
                {new Date(capturedAt).toLocaleTimeString()}
              </time>
              . Selection reflects send time.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Uncertainties({
  items,
  previous,
}: {
  items: string[];
  previous: readonly string[];
}) {
  const [open, setOpen] = useState(false);
  if (!items.length) return null;
  const fresh = items.filter((item) => !previous.includes(item));
  const repeated = items.filter((item) => previous.includes(item));
  return (
    <section className="answer-uncertainty">
      <h3>Uncertainties</h3>
      {fresh.length > 0 && (
        <ul>
          {fresh.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      {repeated.length > 0 && (
        <>
          <Button
            variant="ghost"
            className="uncertainty-repeat"
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            {repeated.length} unchanged{' '}
            {repeated.length === 1 ? 'limit' : 'limits'}
            <ChevronRight
              className={open ? 'disclosure-icon is-open' : 'disclosure-icon'}
              size={12}
              aria-hidden="true"
            />
          </Button>
          {open && (
            <ul>
              {repeated.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

/** Formatting only. Request, policy and grounding stay in their existing boundaries. */
export function AnswerContent({
  result,
  previousUncertainties = [],
}: {
  result: Answer;
  previousUncertainties?: readonly string[];
}) {
  const summary = modelSummary(result);
  const title = summary ? 'Current model' : responseTitle(result);
  return (
    <>
      <h2 className={title ? 'response-heading' : 'sr-only'}>
        {title ?? 'Response'}
      </h2>
      {summary ? (
        <div className="model-overview">
          {summary.features.length > 0 && (
            <div
              className="feature-sequence"
              aria-label="Captured feature order"
            >
              {summary.features.map((name, index) => (
                <span key={index}>
                  {index > 0 && (
                    <ArrowRight size={12} aria-label="followed by" />
                  )}
                  <span>{name}</span>
                </span>
              ))}
            </div>
          )}
          <p className="model-facts">
            {summary.counts.map((item, index) => (
              <span key={item.label}>
                {index > 0 && (
                  <span className="fact-separator" aria-hidden="true">
                    ·
                  </span>
                )}
                <strong>{item.value}</strong> {item.label}
              </span>
            ))}
          </p>
          {summary.unknowns.length > 0 && (
            <p className="topology-note">{summary.unknowns.join(' · ')}</p>
          )}
          {summary.notes.map((note) => (
            <p className="small muted" key={note}>
              {note}
            </p>
          ))}
          {summary.mass && (
            <div className="model-availability">
              <span className="availability-marker" aria-hidden="true">
                ◇
              </span>
              <p>{summary.mass}</p>
            </div>
          )}
        </div>
      ) : (
        result.answer && (
          <div className="answer-text">
            {result.answer
              .split(/\n\n+/)
              .filter((text) => text.trim())
              .map((text, index) => (
                <p key={index} className="draft-text">
                  {text}
                </p>
              ))}
          </div>
        )
      )}
      <Uncertainties
        items={result.uncertainties}
        previous={previousUncertainties}
      />
      <Evidence
        items={result.evidence}
        capturedAt={result.captured_at}
        fullAnswer={summary ? result.answer : undefined}
      />
      {result.discussion.trim() &&
        result.discussion.trim() !== result.answer.trim() && (
          <section className="answer-guidance">
            <h3>Suggestions · unverified</h3>
            <p className="draft-text">{result.discussion}</p>
          </section>
        )}
      {result.assumptions.length > 0 && (
        <section className="answer-guidance">
          <h3>Assumptions</h3>
          <ul>
            {result.assumptions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>
      )}
      {result.follow_up_questions.length > 0 && (
        <section className="answer-guidance">
          <h3>To explore next</h3>
          <ul>
            {result.follow_up_questions.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

export function AnalysisEmpty({ mark }: { mark?: ReactNode }) {
  return (
    <div className="analysis-empty">
      {mark ?? <ForgeMark />}
      <div>
        <h2>Ask about this Part Studio</h2>
        <p>Read the model. Understand the next step.</p>
      </div>
    </div>
  );
}

export function Analysis({
  context,
  csrf,
  selection,
}: {
  context: OnshapeClientContext;
  csrf: string;
  selection: Selection;
}) {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [stage, setStage] = useState<Stage | null>(null);
  const [activePrompt, setActivePrompt] = useState('');
  const [error, setError] = useState<ErrorCode | null>(null);
  const [cooling, setCooling] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const cooldown = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestSelection = useRef(selection);
  const retryPrompt = useRef('');
  useEffect(() => {
    latestSelection.current = selection;
  }, [selection]);
  useEffect(() => {
    const invalidate = () => {
      pending.current?.abort();
      pending.current = null;
      setExchanges([]);
      setActivePrompt('');
      setStage(null);
      setError(null);
    };
    window.addEventListener('pagehide', invalidate);
    return () => {
      pending.current?.abort();
      if (cooldown.current) clearTimeout(cooldown.current);
      window.removeEventListener('pagehide', invalidate);
    };
  }, []);
  const send = async (prompt: string) => {
    if (pending.current || cooling) return;
    const controller = new AbortController();
    pending.current = controller;
    const selectedAtSend = selection;
    retryPrompt.current = prompt;
    setActivePrompt(prompt);
    setError(null);
    setStage('understanding');
    const history: HistoryMessage[] = exchanges
      .flatMap((exchange) => [
        { role: 'user' as const, content: exchange.prompt },
        {
          role: 'assistant' as const,
          content:
            exchange.result.answer.slice(0, 4000) ||
            'General unverified guidance was provided.',
        },
      ])
      .slice(-6);
    let delay = 5;
    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 155000);
    try {
      const result = await askForge(
        context,
        csrf,
        prompt,
        selectedAtSend,
        history,
        controller.signal,
        (next) => {
          if (pending.current === controller && !controller.signal.aborted)
            setStage(next);
        },
      );
      if (controller.signal.aborted || pending.current !== controller) return;
      // Discard late answers about a selection that has since changed. No auto resend.
      if (latestSelection.current !== selectedAtSend) {
        setError('context_unavailable');
        return;
      }
      setExchanges((previous) => [...previous, { prompt, result }].slice(-3));
    } catch (cause) {
      if (pending.current === controller) {
        const code = controller.signal.aborted
          ? timedOut
            ? 'timeout'
            : 'cancelled'
          : cause instanceof AiError
            ? cause.code
            : 'connection_unavailable';
        setError(code);
        if (cause instanceof AiError) delay = cause.retryAfter;
      }
    } finally {
      clearTimeout(timeout);
      if (pending.current === controller) {
        pending.current = null;
        setStage(null);
        setActivePrompt('');
        setCooling(true);
        cooldown.current = setTimeout(() => setCooling(false), delay * 1000);
      }
    }
  };
  return (
    <section
      className="ai-analysis"
      data-empty={exchanges.length === 0}
      aria-label="Forge read-only analysis"
    >
      {exchanges.length === 0 && (
        <div className="analysis-intro-slot">
          {stage ? (
            <div className="user-prompt" data-pending="true">
              <span className="sr-only">You</span>
              <p className="draft-text">{activePrompt}</p>
            </div>
          ) : !error ? (
            <AnalysisEmpty />
          ) : null}
        </div>
      )}
      <div className="ai-conversation" aria-label="Current conversation">
        {exchanges.map((exchange, index) => (
          <article key={index} className="ai-exchange">
            <div className="user-prompt">
              <span className="sr-only">You</span>
              <p className="draft-text">{exchange.prompt}</p>
            </div>
            <AnswerContent
              result={exchange.result}
              previousUncertainties={exchanges
                .slice(0, index)
                .flatMap((item) => item.result.uncertainties)}
            />
          </article>
        ))}
        {stage && exchanges.length > 0 && (
          <div className="user-prompt" data-pending="true">
            <span className="sr-only">You</span>
            <p className="draft-text">{activePrompt}</p>
          </div>
        )}
      </div>
      {error && (
        <div role="alert" className="analysis-error">
          <p>{messages[error]}</p>
          <Button
            disabled={cooling || stage !== null}
            onClick={() => {
              void send(retryPrompt.current);
            }}
          >
            Try again
          </Button>
        </div>
      )}
      {exchanges.length > 0 && (
        <Button
          className="clear-conversation"
          variant="ghost"
          disabled={stage !== null}
          onClick={() => setExchanges([])}
        >
          Clear conversation
        </Button>
      )}
      <PromptComposer
        label="Design prompt"
        cancelLabel="Stop request"
        placeholder="What is in this Part Studio?"
        context={
          selection === 'FACE'
            ? '1 face selected'
            : selection === 'EDGE'
              ? '1 edge selected'
              : selection === 'none'
                ? 'No selection'
                : 'Selection unknown'
        }
        onSubmit={(prompt) => {
          void send(prompt);
        }}
        busy={stage !== null}
        disabled={cooling}
        onCancel={() => pending.current?.abort()}
        hint="Ask about the current model"
        progress={
          stage
            ? stages[stage]
            : cooling
              ? 'Please wait before the next request.'
              : undefined
        }
        showSuggestions={exchanges.length === 0}
        suggestions={[
          "What's in this model?",
          'Explain the selected face',
          'How would you approach modifying this?',
        ]}
        privacy="Your prompt, recent conversation and bounded CAD evidence go to the configured AI service only on send. This conversation stays in this panel’s memory; provider retention policies apply."
      />
      <p className="sr-only">
        Forge sends your prompt, recent conversation and CAD evidence only when
        you send. No engineering validation has run.
      </p>
    </section>
  );
}
