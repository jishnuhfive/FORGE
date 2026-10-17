import { useId } from 'react';
import type { Dispatch, ReactNode } from 'react';
import { Button } from '@forge/design-system';
import { ChevronRight } from 'lucide-react';
import type { LessonStep, VocabularyTerm } from './lesson';
import type { LearningAction, StepInteraction } from './session';

export function LessonDisclosure({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="learning-disclosure">
      <Button
        tabIndex={0}
        variant="ghost"
        className="glass-action"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={onToggle}
      >
        {title}
        <ChevronRight
          size={14}
          className={`disclosure-icon ${open ? 'is-open' : ''}`}
          aria-hidden="true"
        />
      </Button>
      {open && (
        <div id={id} className="learning-reveal learning-disclosure-content">
          {children}
        </div>
      )}
    </div>
  );
}
export function Vocabulary({
  terms,
  interaction,
  dispatch,
}: {
  terms: VocabularyTerm[];
  interaction: StepInteraction;
  dispatch: Dispatch<LearningAction>;
}) {
  return (
    <section className="learning-vocabulary" aria-label="Vocabulary">
      <h2>
        Vocabulary <span className="muted small">· Open a term</span>
      </h2>
      {terms.map((term) => (
        <LessonDisclosure
          key={term.id}
          title={term.term}
          open={interaction.vocabularyVisible.includes(term.id)}
          onToggle={() =>
            dispatch({
              type: 'vocabulary',
              stepId: interaction.stepId,
              termId: term.id,
            })
          }
        >
          <p>{term.definition}</p>
        </LessonDisclosure>
      ))}
    </section>
  );
}
export function HintLadder({
  step,
  interaction,
  dispatch,
}: {
  step: LessonStep;
  interaction: StepInteraction;
  dispatch: Dispatch<LearningAction>;
}) {
  const id = useId();
  const level = interaction.hintLevel;
  const titles = ['Conceptual hint', 'Tool-specific hint', 'Full explanation'];
  const hints = [
    step.hints.conceptual,
    step.hints.tool,
    step.hints.explanation,
  ];
  return (
    <section className="learning-help" aria-label="Lesson help">
      <h2>Need help?</h2>
      {level === 0 && (
        <p className="muted">Start with a way to think about the problem.</p>
      )}
      {!interaction.completed && (
        <Button
          tabIndex={0}
          className="glass-action"
          aria-expanded={level > 0}
          aria-disabled={level === 3}
          aria-controls={level > 0 ? id : undefined}
          onClick={() =>
            level < 3 &&
            dispatch({
              type: 'hint',
              stepId: step.id,
              level: level === 0 ? 1 : level === 1 ? 2 : 3,
            })
          }
        >
          {level === 0
            ? 'Request a conceptual hint'
            : level === 1
              ? 'More help: tool-specific hint'
              : level === 2
                ? 'Request full explanation'
                : 'Full explanation shown'}
        </Button>
      )}
      <div id={id} aria-live="polite" aria-atomic="true">
        {level > 0 && (
          <div key={level} className="learning-hint learning-reveal">
            <h3>{titles[level - 1]}</h3>
            <p>{hints[level - 1]}</p>
          </div>
        )}
      </div>
    </section>
  );
}
