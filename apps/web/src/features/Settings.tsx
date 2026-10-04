import { Badge, Button, Input, Panel } from '@forge/design-system';
import { useId, useState } from 'react';
import type { Preferences } from '../lib/types';

export function Settings({
  preferences,
  onChange,
  storageAvailable,
}: {
  preferences: Preferences;
  onChange: (preferences: Preferences) => void;
  storageAvailable: boolean;
}) {
  const [saved, setSaved] = useState(false);
  const id = useId();
  return (
    <div className="feature settings-feature">
      <div className="section-kicker">
        <span>WORKSPACE PREFERENCES</span>
        <Badge>Local settings</Badge>
      </div>
      <div className="feature-heading">
        <h1>Settings</h1>
        <p>A workspace that fits how you engineer.</p>
      </div>
      <Panel title="Account">
        <div className="profile-placeholder">
          <span className="avatar" aria-hidden="true">
            F
          </span>
          <div>
            <strong>No account connected</strong>
            <p className="muted small">
              Profile and Onshape sign-in are planned.
            </p>
          </div>
        </div>
        <div className="settings-row">
          <span>Onshape connection</span>
          <Badge>Not implemented</Badge>
        </div>
        <Button disabled>Sign out · not available</Button>
      </Panel>
      <Panel title="Preferences">
        <fieldset>
          <legend>Units</legend>
          <div className="segmented-options">
            {(['metric', 'imperial'] as const).map((units) => (
              <label key={units}>
                <input
                  type="radio"
                  name={`${id}-units`}
                  checked={preferences.units === units}
                  onChange={() => onChange({ ...preferences, units })}
                />
                {units === 'metric' ? 'Metric' : 'Imperial'}
              </label>
            ))}
          </div>
        </fieldset>
        <p className="muted small">
          Local display preference for future live data. Development fixtures
          retain their explicit units.
        </p>
        <fieldset>
          <legend>Theme</legend>
          <div className="segmented-options">
            {(['system', 'light', 'dark'] as const).map((theme) => (
              <label key={theme}>
                <input
                  type="radio"
                  name={`${id}-theme`}
                  checked={preferences.theme === theme}
                  onChange={() => onChange({ ...preferences, theme })}
                />
                {theme[0]?.toUpperCase()}
                {theme.slice(1)}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="settings-row">
          <span>AI preferences</span>
          <Badge>Not implemented</Badge>
        </div>
      </Panel>
      <Panel title="Manufacturing profile">
        <p className="muted small">
          Stored on this browser only. No manufacturing validation is performed.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const dimensions = ['width', 'depth', 'height'].map((name) =>
              Number(data.get(name)),
            );
            if (
              dimensions.some((v) => !Number.isInteger(v) || v < 1 || v > 2000)
            )
              return;
            onChange({
              ...preferences,
              printer: String(data.get('printer')).trim(),
              width: dimensions[0] ?? preferences.width,
              depth: dimensions[1] ?? preferences.depth,
              height: dimensions[2] ?? preferences.height,
              materials: String(data.get('materials')).trim(),
            });
            setSaved(true);
          }}
          onChange={() => setSaved(false)}
        >
          <label className="field-label" htmlFor={`${id}-printer`}>
            Printer type
          </label>
          <Input
            id={`${id}-printer`}
            name="printer"
            required
            maxLength={100}
            defaultValue={preferences.printer}
          />
          <div className="dimensions-grid">
            {(['width', 'depth', 'height'] as const).map((dimension) => (
              <div key={dimension}>
                <label className="field-label" htmlFor={`${id}-${dimension}`}>
                  {dimension === 'height' ? 'Build height' : `Bed ${dimension}`}{' '}
                  (mm)
                </label>
                <Input
                  id={`${id}-${dimension}`}
                  name={dimension}
                  type="number"
                  min={1}
                  max={2000}
                  step={1}
                  required
                  defaultValue={preferences[dimension]}
                />
              </div>
            ))}
          </div>
          <label className="field-label" htmlFor={`${id}-materials`}>
            Available materials
          </label>
          <Input
            id={`${id}-materials`}
            name="materials"
            required
            maxLength={100}
            defaultValue={preferences.materials}
          />
          <div className="action-bar">
            <Button type="submit">Save local profile</Button>
          </div>
          {saved && (
            <p role="status" className="muted small">
              Profile saved{' '}
              {storageAvailable ? 'in this browser' : 'for this session'}.
            </p>
          )}
        </form>
      </Panel>
      <Panel title="Privacy">
        <p>
          Only interface preferences and onboarding completion are stored
          locally. Prompts and sample edits stay in memory. No data is sent to
          OpenAI or Onshape.
        </p>
        <p className="muted small">
          Account data retention and deletion controls will be defined with the
          future backend integration.
        </p>
        <Button disabled>Delete Forge data · not available</Button>
      </Panel>
      {!storageAvailable && (
        <p className="notice" role="status">
          Browser storage is unavailable. Preferences last for this session
          only.
        </p>
      )}
    </div>
  );
}
