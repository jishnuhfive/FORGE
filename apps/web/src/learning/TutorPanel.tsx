import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Button, StatusBadge } from '@forge/design-system';
import { ChevronRight } from 'lucide-react';
import { useAuth } from '../auth/context';
import { useOnshapeContext } from '../onshape/store';
import { statusLabel, statusTone } from './checkStatus';
import { useLearning } from './context';
import type { LessonStep } from './lesson';
import { activeInvestigation } from './session';
import type { StepInteraction } from './session';
import { TutorError, askTutor, stageText, tutorMessages } from './tutorApi';
import type {
  CheckWord,
  TutorAnswerView,
  TutorHints,
  TutorMessage,
  TutorStage,
} from './tutorApi';

const MAX_EXCHANGES = 3;
const outcomeWord: Record<CheckWord, string> = {
  verified: 'Verified',
  not_met: 'Not yet',
  unverified: 'Can’t fully verify',
};
const cadTone = {
  verified: ['pass', 'Observed'],
  unknown: ['unverified', 'Unknown'],
  unverified: ['unverified', 'Unverified'],
  assumption: ['unverified', 'Assumption'],
} as const;

type Exchange = { question: string; answer: TutorAnswerView };

function ObservedItem({ item }: { item: TutorAnswerView['observed'][number] }) {
  if (item.source === 'check') {
    const status = item.status as keyof typeof statusTone;
    if (!(status in statusTone)) return <li>{item.statement}</li>;
    return (
      <li>
        <StatusBadge status={statusTone[status]} label={statusLabel[status]} />
        <span>{item.statement}</span>
      </li>
    );
  }
  const known = cadTone[item.status as keyof typeof cadTone] ?? cadTone.unknown;
  return (
    <li>
      <StatusBadge status={known[0]} label={known[1]} />
      <span>{item.statement}</span>
    </li>
  );
}

// Server-composed answer. The model's prose comes first; everything Forge states as
// observed or unknown is the server's own wording, listed separately below it.
export function TutorAnswerBlock({ answer }: { answer: TutorAnswerView }) {
  return (
    <div className="tutor-answer">
      {answer.explanation
        .split(/\n\n+/)
        .filter((p) => p.trim())
        .map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      {answer.reasoning_question && (
        <p className="tutor-question">
          <span className="muted">Something to think about</span>
          {answer.reasoning_question}
        </p>
      )}
      {answer.latest_check && (
        <p className="muted small">
          Latest check: {outcomeWord[answer.latest_check.outcome]}. Only Check
          my step can change that.
        </p>
      )}
      {answer.observed.length > 0 && (
        <section className="check-findings" aria-label="What Forge observed">
          <h3>What Forge observed</h3>
          <ul>
            {answer.observed.map((item, index) => (
              <ObservedItem key={index} item={item} />
            ))}
          </ul>
        </section>
      )}
      {answer.unknowns.length > 0 && (
        <section className="check-findings" aria-label="Still unknown">
          <h3>Still unknown</h3>
          <ul>
            {answer.unknowns.map((item, index) => (
              <li key={index}>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {answer.next_action && (
        <p className="tutor-next">
          <span className="muted">Next thing to try</span>
          {answer.next_action}
        </p>
      )}
      {answer.notes.map((note) => (
        <p key={note} className="muted small">
          {note}
        </p>
      ))}
    </div>
  );
}

function hintsFor(
  step: LessonStep,
  interaction: StepInteraction,
  transfer: boolean,
  experience: TutorHints['experience'],
  goal: TutorHints['goal'],
): TutorHints {
  const active = activeInvestigation(step, interaction);
  const state = active?.state;
  return {
    experience,
    goal,
    hints_revealed: interaction.hintLevel,
    guidance: state?.guidance ?? (transfer ? 'independent' : 'full'),
    investigation: state
      ? {
          stage: state.recommendation
            ? 'recommended'
            : state.hypothesis
              ? 'explained'
              : state.prediction !== undefined
                ? 'predicted'
                : 'observed',
          prediction_answered: state.prediction !== undefined,
          rechecked: state.rechecked === true,
          resolved: state.status === 'resolved',
        }
      : null,
  };
}

export function TutorPanel({
  step,
  interaction,
}: {
  step: LessonStep;
  interaction: StepInteraction;
}) {
  const auth = useAuth();
  const client = useOnshapeContext();
  const learning = useLearning();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [sending, setSending] = useState(false);
  const [stage, setStage] = useState<TutorStage>('understanding');
  const [error, setError] = useState<TutorError | null>(null);
  const [lastQuestion, setLastQuestion] = useState('');
  const controller = useRef<AbortController | null>(null);
  const panel = useId();
  const field = useId();
  useEffect(() => () => controller.current?.abort(), []);
  const lesson = learning?.lesson;
  const session = learning?.session;
  if (
    !lesson ||
    lesson.id !== 'mounting-bracket' ||
    !session ||
    !('profile' in session)
  )
    return null;
  const transfer =
    lesson.transfer?.steps.some((s) => s.id === step.id) ?? false;
  const token = interaction.evidenceToken ?? null;
  const csrf = auth?.me.csrf_token ?? null;
  const hasContext =
    client.context !== null &&
    client.context.revision.kind === 'workspace' &&
    (!client.context.elementType ||
      client.context.elementType === 'partStudio');

  async function send(question: string) {
    const text = question.trim();
    if (!text || sending) return;
    if (!csrf) {
      setError(new TutorError('session_expired'));
      return;
    }
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setSending(true);
    setError(null);
    setStage('understanding');
    setLastQuestion(text);
    const history: TutorMessage[] = exchanges.flatMap((e) => [
      { role: 'user' as const, content: e.question },
      {
        role: 'assistant' as const,
        content: e.answer.explanation.slice(0, 1500),
      },
    ]);
    try {
      const answer = await askTutor(
        {
          lessonId: 'mounting-bracket',
          stepId: step.id,
          question: text,
          history,
          learner: hintsFor(
            step,
            interaction,
            transfer,
            session && 'profile' in session
              ? session.profile.experience
              : 'beginner',
            session && 'profile' in session
              ? session.profile.goal
              : 'fundamentals',
          ),
          evidenceToken: token,
          context: client.context,
        },
        csrf,
        current.signal,
        setStage,
      );
      if (current.signal.aborted) return;
      setExchanges((items) =>
        [...items, { question: text, answer }].slice(-MAX_EXCHANGES),
      );
      setDraft('');
    } catch (cause) {
      if (current.signal.aborted) return;
      setError(
        cause instanceof TutorError
          ? cause
          : new TutorError('connection_unavailable'),
      );
    } finally {
      if (controller.current === current) setSending(false);
    }
  }
  function stop() {
    controller.current?.abort();
    setSending(false);
    setError(new TutorError('cancelled'));
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }
  function key(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Ctrl/Cmd+Enter sends, matching the Design composer. Enter adds a new line.
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void send(draft);
    }
  }
  const empty = draft.trim().length === 0;
  return (
    <section className="learning-tutor" aria-label="Ask Forge">
      <Button
        tabIndex={0}
        variant="ghost"
        className="glass-action"
        aria-expanded={open}
        aria-controls={open ? panel : undefined}
        onClick={() => setOpen((value) => !value)}
      >
        Ask Forge
        <ChevronRight
          size={14}
          className={`disclosure-icon ${open ? 'is-open' : ''}`}
          aria-hidden="true"
        />
      </Button>
      {open && (
        <div id={panel} className="learning-reveal">
          <p className="muted small">
            Using: this step{token ? ' and your latest check result' : ''}.{' '}
            {hasContext
              ? 'Forge reads your model only if your question needs it.'
              : tutorMessages.context_unavailable}
          </p>
          {exchanges.map((exchange, index) => (
            <div key={index} className="tutor-exchange">
              <p className="tutor-asked">
                <span className="muted">You asked</span>
                {exchange.question}
              </p>
              <TutorAnswerBlock answer={exchange.answer} />
            </div>
          ))}
          <form className="tutor-form" onSubmit={submit}>
            <label htmlFor={field}>Ask about this step</label>
            <textarea
              id={field}
              rows={3}
              maxLength={600}
              value={draft}
              disabled={sending}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={key}
              placeholder="For example: Why isn’t my second part showing up?"
            />
            <div className="action-bar">
              <Button
                tabIndex={0}
                type="submit"
                variant="primary"
                className="check-action"
                aria-disabled={empty || sending}
              >
                Send
              </Button>
              {sending && (
                <Button tabIndex={0} type="button" onClick={stop}>
                  Stop request
                </Button>
              )}
            </div>
            <p className="muted small">
              Ctrl+Enter to send. Forge asks the AI only when you send.
            </p>
          </form>
          <div role="status" aria-live="polite">
            {sending && <p>{stageText[stage]}</p>}
          </div>
          {error && (
            <div role="alert" className="tutor-error">
              <p>{tutorMessages[error.code]}</p>
              <p className="muted small">
                Your lesson, hints and Check my step still work.
              </p>
              {error.code !== 'cancelled' && lastQuestion && (
                <Button
                  tabIndex={0}
                  type="button"
                  variant="ghost"
                  className="glass-action"
                  onClick={() => void send(lastQuestion)}
                >
                  Try again
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
