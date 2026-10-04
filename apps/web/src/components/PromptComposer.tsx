import { Button, Textarea } from '@forge/design-system';
import { ArrowUp, Paperclip, Square } from 'lucide-react';
import { useId, useRef, useState } from 'react';

const suggestions = [
  'Design a NEMA 17 motor mount.',
  'Create a carriage for two 8 mm rails.',
  'Help me design a belt-driven camera slider.',
];
export function PromptComposer({
  label,
  placeholder,
  onSubmit,
  context,
  busy = false,
  onCancel,
  disabled = false,
  showSuggestions = false,
}: {
  label: string;
  placeholder: string;
  onSubmit: (text: string) => void;
  context?: string;
  busy?: boolean;
  onCancel?: () => void;
  disabled?: boolean;
  showSuggestions?: boolean;
}) {
  const [text, setText] = useState('');
  const id = useId();
  const ref = useRef<HTMLTextAreaElement>(null);
  const submit = () => {
    if (text.trim() && !busy && !disabled) onSubmit(text.trim());
  };
  return (
    <div className="composer-area">
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label className="sr-only" htmlFor={id}>
          {label}
        </label>
        <Textarea
          ref={ref}
          id={id}
          value={text}
          disabled={disabled || busy}
          maxLength={4000}
          placeholder={placeholder}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === 'Enter' &&
              (event.metaKey || event.ctrlKey) &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              submit();
            }
          }}
          aria-describedby={`${id}-hint`}
        />
        <div className="composer-toolbar">
          <span className="composer-context">
            <Paperclip size={14} aria-hidden="true" />
            {context ?? 'No CAD context'}
          </span>
          {busy ? (
            <Button
              onClick={onCancel}
              aria-label="Stop preview"
              disabled={!onCancel}
            >
              <Square size={13} aria-hidden="true" />
              Stop
            </Button>
          ) : (
            <Button
              variant="primary"
              type="submit"
              disabled={!text.trim() || disabled}
              aria-label="Send prompt"
            >
              <ArrowUp size={16} aria-hidden="true" />
            </Button>
          )}
        </div>
      </form>
      <div id={`${id}-hint`} className="composer-hint">
        <span>Describe the function. Include constraints.</span>
        <kbd>⌘ / Ctrl + Enter</kbd>
      </div>
      {showSuggestions && (
        <div className="suggestions">
          <span className="eyebrow">A place to start</span>
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              disabled={disabled || busy}
              onClick={() => {
                setText(suggestion);
                ref.current?.focus();
              }}
            >
              <span>{suggestion}</span>
              <ArrowUp size={13} aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
