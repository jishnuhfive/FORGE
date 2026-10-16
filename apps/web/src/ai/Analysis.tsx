import { Badge, Button, Card } from '@forge/design-system';
import { useEffect, useRef, useState } from 'react';
import { PromptComposer } from '../components/PromptComposer';
import type { OnshapeClientContext } from '../onshape/model';
import { AiError, askForge, messages, stages } from './api';
import type {
  Answer,
  ErrorCode,
  HistoryMessage,
  Selection,
  Stage,
} from './api';

type Exchange = { prompt: string; result: Answer };

function Evidence({ items }: { items: Answer['evidence'] }) {
  const [open, setOpen] = useState(false);
  const valid = items.filter((item) => item.statement.trim());
  if (valid.length === 0) return null;
  return (
    <div className="ai-evidence-panel">
      <Button aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        {open ? 'Hide evidence' : 'Evidence'}
      </Button>
      {open && (
        <ul className="ai-evidence" aria-label="Evidence">
          {valid.map((item) => (
            <li key={item.id}>
              <Badge>{item.status}</Badge>
              <span>{item.statement}</span>
            </li>
          ))}
        </ul>
      )}
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
        setCooling(true);
        cooldown.current = setTimeout(() => setCooling(false), delay * 1000);
      }
    }
  };
  return (
    <section className="ai-analysis" aria-label="Forge read-only analysis">
      <p className="small muted">
        Forge AI sends your prompt, recent conversation and bounded CAD evidence
        to the configured AI service only when you send. Read-only · kept in
        this panel’s memory.
      </p>
      <div className="ai-conversation" aria-label="Current conversation">
        {exchanges.map((exchange, index) => (
          <Card key={index} className="ai-exchange">
            <span className="eyebrow">You</span>
            <p className="draft-text">{exchange.prompt}</p>
            <h2>Forge analysis</h2>
            <Badge>Read-only</Badge>
            {exchange.result.answer && (
              <p className="draft-text">{exchange.result.answer}</p>
            )}
            <Evidence items={exchange.result.evidence} />
            {exchange.result.uncertainties.length > 0 && (
              <div>
                <h3>Uncertainties</h3>
                <ul>
                  {exchange.result.uncertainties.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {exchange.result.discussion.trim() &&
              exchange.result.discussion.trim() !==
                exchange.result.answer.trim() && (
                <div>
                  <h3>Suggestions · unverified</h3>
                  <p className="draft-text">{exchange.result.discussion}</p>
                </div>
              )}
            {exchange.result.assumptions.length > 0 && (
              <div>
                <h3>Assumptions</h3>
                <ul>
                  {exchange.result.assumptions.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {exchange.result.follow_up_questions.length > 0 && (
              <div>
                <h3>To explore next</h3>
                <ul>
                  {exchange.result.follow_up_questions.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {exchange.result.captured_at && (
              <p className="small muted">
                Evidence captured{' '}
                <time dateTime={exchange.result.captured_at}>
                  {new Date(exchange.result.captured_at).toLocaleTimeString()}
                </time>
                . Selection reflects send time.
              </p>
            )}
          </Card>
        ))}
      </div>
      {(stage || cooling) && (
        <div role="status" aria-live="polite" aria-busy={stage !== null}>
          {stage && <p>{stages[stage]}</p>}
          {cooling && (
            <p className="small muted">Please wait before the next request.</p>
          )}
        </div>
      )}
      {error && (
        <div role="alert" className="notice">
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
        hint="Ask about this model. CAD changes are unavailable."
      />
      <p className="small muted">
        No deterministic engineering validation has run. CAD is unchanged.
      </p>
      {exchanges.length > 0 && (
        <Button disabled={stage !== null} onClick={() => setExchanges([])}>
          Clear conversation
        </Button>
      )}
    </section>
  );
}
