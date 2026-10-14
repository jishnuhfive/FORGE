import { useState } from 'react';
import { InspectorView } from '../cad/InspectorView';
import { inspectorFixture } from '../cad/__fixtures__/inspector';
import { syntheticProof } from '../cad/__fixtures__/proof';
const states = [
  'Simple Part Studio',
  'Empty Part Studio',
  'Many features',
  'Suppressed feature',
  'Unknown feature',
  'Partial provider failure',
  'Unavailable mass',
  'Selected FACE',
  'Selected EDGE',
] as const;
export default function InspectorPreview() {
  const [state, setState] =
    useState<(typeof states)[number]>('Simple Part Studio');
  const source = structuredClone(syntheticProof);
  if (state === 'Empty Part Studio')
    for (const name of ['features', 'parts', 'bodies', 'mass'] as const)
      source[name].count = 0;
  if (state === 'Many features') source.features.count = 100;
  if (state === 'Partial provider failure')
    source.bodies = {
      status: 'provider_failure',
      code: 'provider_timeout',
      count: null,
      retry_after_seconds: null,
    };
  if (state === 'Unavailable mass') source.has_mass = false;
  const result = inspectorFixture(source);
  const feature = result.features.items[0];
  if (feature && state === 'Suppressed feature')
    feature.suppression = 'suppressed';
  if (feature && state === 'Unknown feature') {
    feature.feature_type = 'unknown';
    feature.name = 'Synthetic custom feature';
    feature.completeness = 'partial';
    result.features.completeness = 'partial';
  }
  return (
    <div className="feature">
      <h1>CAD inspector preview</h1>
      <p className="local-notice">
        Synthetic evidence only. No Onshape request or CAD change.
      </p>
      <label htmlFor="inspector-preview" className="field-label">
        Inspector state
      </label>
      <select
        id="inspector-preview"
        className="input"
        value={state}
        onChange={(e) => {
          const next = states.find((s) => s === e.target.value);
          if (next) setState(next);
        }}
      >
        {states.map((s) => (
          <option key={s}>{s}</option>
        ))}
      </select>
      <p role="status">
        Selection:{' '}
        {state === 'Selected FACE'
          ? '1 face selected'
          : state === 'Selected EDGE'
            ? '1 edge selected'
            : 'No selection'}
        . Ownership and geometry unverified.
      </p>
      <InspectorView key={state} result={result} />
    </div>
  );
}
