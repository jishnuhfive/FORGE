import { Button, Dialog, GlassSurface, Textarea } from '@forge/design-system';
import { ArrowUp, CornerDownLeft, Info, Scan, Square } from 'lucide-react';
import { useId, useLayoutEffect, useRef, useState } from 'react';

const defaults = [
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
  hint = 'Describe the function. Include constraints.',
  cancelLabel = 'Stop preview',
  suggestions = defaults,
  progress,
  privacy,
}: {
  label: string;
  placeholder: string;
  onSubmit: (text: string) => void;
  context?: string;
  busy?: boolean;
  onCancel?: () => void;
  disabled?: boolean;
  showSuggestions?: boolean;
  hint?: string;
  cancelLabel?: string;
  suggestions?: string[];
  progress?: string;
  privacy?: string;
}) {
  const [text, setText] = useState('');
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const fit = () => {
      const style = getComputedStyle(node);
      const min =
        parseFloat(style.getPropertyValue('--composer-input-min')) || 44;
      const max =
        parseFloat(style.getPropertyValue('--composer-input-max')) || 144;
      node.style.height = 'auto';
      const height = node.scrollHeight;
      node.style.height = `${Math.min(max, Math.max(min, height))}px`;
      node.style.overflowY = height > max ? 'auto' : 'hidden';
    };
    fit();
    if (typeof ResizeObserver === 'undefined') return;
    const container = node.parentElement;
    if (!container) return;
    let width = container.clientWidth;
    let frame: number | null = null;
    const observer = new ResizeObserver(([entry]) => {
      if (entry && entry.contentRect.width !== width) {
        width = entry.contentRect.width;
        if (frame !== null) cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          frame = null;
          fit();
        });
      }
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [text]);
  const submit = () => {
    if (text.trim() && !busy && !disabled) onSubmit(text.trim());
  };
  const selected =
    context === '1 face selected' || context === '1 edge selected';
  return (
    <div
      className="composer-area"
      data-busy={busy}
      data-state={
        busy
          ? 'sending'
          : disabled
            ? 'disabled'
            : text.trim()
              ? 'typing'
              : 'idle'
      }
    >
      {showSuggestions && (
        <div className="suggestions" aria-label="Example questions">
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
              <span className="suggestion-index" aria-hidden="true">
                ›
              </span>
              <span>{suggestion}</span>
              <CornerDownLeft size={12} aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
      <div className="composer-progress">
        {progress && (
          <span role="status" aria-live="polite" key={progress}>
            <span className="progress-dot" aria-hidden="true" />
            {progress}
          </span>
        )}
      </div>
      <div className="material-bed composer-bed">
        <GlassSurface className="composer">
          <form
            aria-busy={busy}
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
              rows={1}
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
              aria-describedby={`${id}-hint${privacy ? ` ${id}-privacy` : ''}`}
            />
            <div className="composer-toolbar">
              <span className="composer-context" data-selected={selected}>
                <Scan size={12} aria-hidden="true" />
                {context ?? 'No CAD context'}
              </span>
              <div className="composer-controls">
                <kbd
                  className="composer-shortcut"
                  aria-hidden="true"
                  title="Command or Control + Enter"
                >
                  ⌘ ↵
                </kbd>
                {privacy && (
                  <Button
                    className="composer-info"
                    variant="ghost"
                    aria-label="Data use"
                    title="Data use"
                    onClick={(event) => {
                      event.currentTarget.focus();
                      setPrivacyOpen(true);
                    }}
                  >
                    <Info size={12} aria-hidden="true" />
                  </Button>
                )}
                <Button
                  className="composer-send glass-action"
                  variant="ghost"
                  type={busy ? 'button' : 'submit'}
                  disabled={busy ? !onCancel : !text.trim() || disabled}
                  onClick={busy ? onCancel : undefined}
                  aria-label={busy ? cancelLabel : 'Send prompt'}
                  data-sending={busy}
                >
                  <span
                    className="send-glyph send-glyph--arrow"
                    aria-hidden="true"
                  >
                    <ArrowUp size={16} />
                  </span>
                  <span
                    className="send-glyph send-glyph--stop"
                    aria-hidden="true"
                  >
                    <Square size={12} />
                  </span>
                </Button>
              </div>
            </div>
          </form>
        </GlassSurface>
      </div>
      <p id={`${id}-hint`} className="sr-only">
        {hint} Enter adds a line. Command or Control + Enter sends.
      </p>
      {privacy && (
        <>
          <p id={`${id}-privacy`} className="sr-only">
            {privacy}
          </p>
          <Dialog
            open={privacyOpen}
            onOpenChange={setPrivacyOpen}
            title="Your data"
            description="What happens when you send a question"
          >
            <p>{privacy}</p>
          </Dialog>
        </>
      )}
    </div>
  );
}
