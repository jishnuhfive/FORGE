import type { Answer } from './api';
import { modelSummary } from './presentation';

// Exact server-owned grammar. A changed contract keeps the original answer;
// neither model prose nor a prompt supplies a verified CAD statement here.
export const technicalLimits = {
  freshness:
    'Forge inspected the default configuration at the end of the feature list. Data comes from separate reads; currentness and snapshot consistency remain unverified.',
  units:
    "Physical units haven't been independently verified. Exact mass and volume aren't supplied.",
  validation:
    "Forge hasn't run deterministic engineering validation on this design. Validation remains unverified.",
  order:
    "Forge's feature ordering evidence describes returned feature-list order only. That ordering does not establish dependency, ownership, or parent-child relationships. Selection references do not establish ownership. Missing relationships prove nothing about CAD. A terminal feature is known only when complete feature-list and end-of-list rollback evidence establish one.",
  parameters:
    'Parameter values are captured settings, not verified dimensions. Expressions are not evaluated, options may be inactive, and selection queries do not establish geometry ownership.',
} as const;

type Kind =
  'inventory' | 'terminal' | 'order' | 'dependency' | 'state' | 'ownership';
export type FriendlyAnswer = {
  kind: Kind | 'write';
  paragraphs: string[];
  sequence?: string[];
  counts?: { value: string; label: string }[];
  title?: string;
};
type Fact = Answer['evidence'][number];
type Feature = { index: number; name: string; state: 'active' | 'suppressed' };
type Order = { before: number; after: number; first: string; second: string };
const jsonString = '("(?:[^"\\\\]|\\\\.)*")';
const position = '(first|second|third|number (?:[4-9]|1\\d|20))';
const indexOf = (value: string) =>
  ['first', 'second', 'third'].includes(value)
    ? ['first', 'second', 'third'].indexOf(value) + 1
    : Number(value.slice(7));
const nameOf = (value: string): string | null => {
  try {
    const name: unknown = JSON.parse(value);
    return typeof name === 'string' && name.trim() && name.length <= 500
      ? name
      : null;
  } catch {
    return null;
  }
};
const question = (prompt: string) => prompt.trim().replace(/[?.!]+$/, '');

function kindOf(prompt: string): Kind | null {
  const value = question(prompt);
  if (
    /^(?:what(?: is|'s) in|summari[sz]e|describe|give me an overview of) (?:this|the|my) (?:part studio|model|design)$/i.test(
      value,
    ) ||
    /^what features (?:are in|does) (?:this|the|my|your) (?:part studio|model|design)(?: have)?(?: and in what order)?$/i.test(
      value,
    )
  )
    return 'inventory';
  if (/^what(?: is|'s) the (?:final|last|terminal) feature$/i.test(value))
    return 'terminal';
  if (/^what (?:comes|is) (?:immediately )?before .+$/i.test(value))
    return 'order';
  if (/^does .+ depend on .+$/i.test(value)) return 'dependency';
  if (
    /^is .+ (?:active(?: or suppressed)?|suppressed(?: or active)?)$/i.test(
      value,
    )
  )
    return 'state';
  if (
    /^what feature owns (?:this|the selected|my selected) (?:face|edge)$/i.test(
      value,
    )
  )
    return 'ownership';
  return null;
}

function feature(item: Fact): Feature | null {
  const match = item.statement.match(
    new RegExp(
      `^The ${position} captured feature is named ${jsonString} \\((?:sketch|extrude|fillet|chamfer); (active|suppressed)\\)\\.$`,
    ),
  );
  if (!match || item.status !== 'verified') return null;
  const index = indexOf(match[1]!);
  const name = nameOf(match[2]!);
  return item.id === `feature_${index}` && name
    ? { index, name, state: match[3] as Feature['state'] }
    : null;
}

function order(item: Fact): Order | null {
  const match = item.statement.match(
    new RegExp(
      `^The ${position} captured modeled feature, ${jsonString}, appears before the ${position} captured modeled feature, ${jsonString}, in the returned feature order\\.$`,
    ),
  );
  if (!match || item.status !== 'verified') return null;
  const before = indexOf(match[1]!);
  const after = indexOf(match[3]!);
  const first = nameOf(match[2]!);
  const second = nameOf(match[4]!);
  return item.id === `order_${before}_${after}` &&
    after === before + 1 &&
    first &&
    second
    ? { before, after, first, second }
    : null;
}

function terminal(item: Fact): { index: number; name: string } | null {
  const match = item.statement.match(
    new RegExp(
      `^The terminal feature in the complete captured feature list is the ${position} feature, ${jsonString}\\.$`,
    ),
  );
  const name = match && nameOf(match[2]!);
  return item.id === 'terminal_feature' &&
    item.status === 'verified' &&
    match &&
    name
    ? { index: indexOf(match[1]!), name }
    : null;
}

function factsOf(result: Answer): Map<string, Fact> | null {
  const facts = new Map(result.evidence.map((item) => [item.id, item]));
  if (facts.size !== result.evidence.length) return null;
  // Keep identity in canonical positions. Never join duplicate display names.
  const names = new Map<number, string>();
  const add = (index: number, name: string) => {
    if (names.has(index) && names.get(index) !== name) return false;
    if ([...names].some(([other, label]) => other !== index && label === name))
      return false;
    names.set(index, name);
    return true;
  };
  for (const item of facts.values()) {
    if (/^feature_\d+$/.test(item.id)) {
      const value = feature(item);
      if (!value || !add(value.index, value.name)) return null;
    } else if (item.id.startsWith('order_') && item.id !== 'order_semantics') {
      const value = order(item);
      if (
        !value ||
        !add(value.before, value.first) ||
        !add(value.after, value.second)
      )
        return null;
    } else if (item.id === 'terminal_feature') {
      const value = terminal(item);
      if (!value || !add(value.index, value.name)) return null;
    } else if (
      item.id === 'order_semantics' &&
      (item.status !== 'verified' || item.statement !== technicalLimits.order)
    )
      return null;
  }
  const total = count(facts, 'features');
  if (total !== null && [...names.keys()].some((index) => index > total))
    return null;
  const last = facts.get('terminal_feature');
  if (total !== null && last && terminal(last)?.index !== total) return null;
  return facts;
}

function count(facts: Map<string, Fact>, id: 'features' | 'parts' | 'bodies') {
  const item = facts.get(id);
  const noun = {
    features: 'features?',
    parts: 'parts?',
    bodies: '(?:body|bodies)',
  }[id];
  const match = item?.statement.match(
    new RegExp(
      `^The captured Part Studio contains (0|[1-9]\\d{0,5}) ${noun}\\.$`,
    ),
  );
  if (item?.status !== 'verified' || !match) return null;
  const value = Number(match[1]);
  const label =
    value === 1
      ? { features: 'feature', parts: 'part', bodies: 'body' }[id]
      : id;
  return item.statement ===
    `The captured Part Studio contains ${value} ${label}.`
    ? value
    : null;
}

const writeCapability =
  "Forge is currently read-only and can't modify CAD yet. I can inspect the current model and explain or propose how a change could be made.";
const widthUnknown =
  'The captured evidence does not identify a verified width-driving dimension, so I cannot safely identify which parameter to edit.';
const targetUnknown =
  'The captured evidence does not identify a verified controlling dimension or edit target, so I cannot safely identify which parameter to edit.';

/** Formatting only: exact canonical facts remain the authority and are never edited. */
export function friendlyAnswer(
  result: Answer,
  prompt: string,
): FriendlyAnswer | null {
  const facts = factsOf(result);
  if (!facts || !facts.size || result.capability_state !== 'read_only')
    return null;
  const exact = (id: string, status: Fact['status'], statement: string) => {
    const item = facts.get(id);
    return item?.status === status && item.statement === statement;
  };
  const joined =
    result.answer ===
    result.evidence.map((item) => item.statement).join('\n\n');
  if (
    joined &&
    exact('write_capability', 'verified', writeCapability) &&
    exact(
      'no_cad_writes',
      'verified',
      'Forge performed no CAD writes for this request.',
    ) &&
    (exact('write_target_unknown', 'unknown', widthUnknown) ||
      exact('write_target_unknown', 'unknown', targetUnknown))
  )
    return {
      kind: 'write',
      paragraphs: [
        "Forge is read-only here, so I can't change the model.",
        facts.get('write_target_unknown')!.statement === widthUnknown
          ? "I also can't verify which parameter controls the width from the current evidence."
          : "I also can't verify which parameter to edit from the current evidence.",
      ],
    };
  const kind = kindOf(prompt);
  if (kind === 'ownership') {
    for (const noun of ['face', 'edge']) {
      if (!question(prompt).toLowerCase().endsWith(noun)) continue;
      if (
        !exact('selection', 'verified', `One ${noun} is selected.`) ||
        !exact(
          'selection_feature',
          'unknown',
          `The selected ${noun}'s owning feature is unknown.`,
        )
      )
        continue;
      const unknowns = {
        selection_ownership:
          'Selection ownership by a part, body or feature is unknown.',
        selection_part: `The selected ${noun}'s owning part is unknown.`,
        selection_body: `The selected ${noun}'s owning body is unknown.`,
        selection_dimensions: `The selected ${noun}'s dimensions are unknown.`,
        selection_type:
          noun === 'face'
            ? "The selected face's surface type is unknown."
            : "The selected edge's curve type is unknown.",
        selection_geometry:
          noun === 'face'
            ? 'Selected-face geometry, including area and normal direction, is unknown.'
            : 'Adjacent faces and edge-specific geometry are unknown.',
      };
      const capability =
        "Forge can confirm the selection type, but selection-specific ownership and measurements aren't available yet.";
      if (
        Object.entries(unknowns).some(
          ([id, text]) => !exact(id, 'unknown', text),
        ) ||
        !exact('selection_capability', 'verified', capability)
      )
        return null;
      const canonical = `One ${noun} is selected.\n\nOwning part, body, feature, dimensions, ${noun === 'face' ? 'surface type and face-specific geometry (including area and normal direction)' : 'curve type, adjacent faces and edge-specific geometry'} are currently unknown.\n\nForge can confirm the selection type, but selection-specific ownership and measurements aren't available yet.`;
      if (result.answer !== canonical) return null;
      return {
        kind,
        title: `Selected ${noun}`,
        paragraphs: [
          `I can see that one ${noun} is selected, but its owning feature isn't known yet.`,
        ],
      };
    }
  }
  if (!kind || (!joined && !(kind === 'inventory' && modelSummary(result))))
    return null;
  if (kind === 'inventory') {
    const total = count(facts, 'features');
    if (total === null || total > 20) return null;
    const features = [...facts.values()]
      .filter((item) => /^feature_\d+$/.test(item.id))
      .map(feature);
    if (features.length !== total || features.some((item) => !item))
      return null;
    const ordered = (features as Feature[]).sort((a, b) => a.index - b.index);
    if (ordered.some((item, index) => item.index !== index + 1)) return null;
    const counts = (['features', 'parts', 'bodies'] as const).flatMap((id) => {
      const value = count(facts, id);
      return value === null
        ? []
        : [
            {
              value: String(value),
              label:
                value === 1
                  ? { features: 'feature', parts: 'part', bodies: 'body' }[id]
                  : id,
            },
          ];
    });
    return {
      kind,
      title: 'Current model',
      paragraphs: [
        total === 0
          ? 'This Part Studio has no modeled features.'
          : `Your model has ${total} ${total === 1 ? 'feature' : 'features'}:`,
      ],
      sequence: ordered.map(
        (item) =>
          item.name + (item.state === 'suppressed' ? ' (suppressed)' : ''),
      ),
      counts,
    };
  }
  if (kind === 'terminal') {
    const item = facts.get('terminal_feature');
    const value = item && terminal(item);
    return value
      ? { kind, paragraphs: [`${value.name} is the final feature.`] }
      : null;
  }
  if (kind === 'state') {
    const values = [...facts.values()]
      .map(feature)
      .filter((value) => value !== null);
    if (values.length !== 1) return null;
    const value = values[0]!;
    const asked = question(prompt).match(
      /^is (.+?) (?:active(?: or suppressed)?|suppressed(?: or active)?)$/i,
    )?.[1];
    return asked === value.name
      ? { kind, paragraphs: [`${value.name} is ${value.state}.`] }
      : null;
  }
  if (kind === 'order' || kind === 'dependency') {
    const values = [...facts.values()]
      .map(order)
      .filter((value) => value !== null);
    if (values.length !== 1 || !hasOrderLimit(result)) return null;
    const value = values[0]!;
    if (kind === 'order')
      return {
        kind,
        paragraphs: [`${value.first} comes before ${value.second}.`],
      };
    const asked = question(prompt).match(/^does (.+) depend on (.+)$/i);
    if (asked?.[1] !== value.second || asked[2] !== value.first) return null;
    return {
      kind,
      paragraphs: [
        `I can't confirm that ${value.second} depends on ${value.first}.`,
        `I can verify that ${value.first} comes before ${value.second} in the feature order.`,
      ],
    };
  }
  return null;
}

function hasOrderLimit(result: Answer) {
  return (
    result.uncertainties.includes(technicalLimits.order) ||
    result.evidence.some(
      (item) =>
        item.id === 'order_semantics' &&
        item.status === 'verified' &&
        item.statement === technicalLimits.order,
    )
  );
}

export function contextualLimits(result: Answer, prompt: string): string[] {
  const kind = kindOf(prompt);
  const limits: string[] = [];
  if (hasOrderLimit(result)) {
    if (kind === 'dependency')
      limits.push('Dependency has not been established.');
    else if (
      kind === 'order' ||
      (kind === 'inventory' && /order/i.test(prompt))
    )
      limits.push('Feature order does not prove dependency.');
  }
  if (
    kind === 'ownership' &&
    result.evidence.some(
      (item) =>
        item.id === 'selection_feature' &&
        item.status === 'unknown' &&
        /^The selected (?:face|edge)'s owning feature is unknown\.$/.test(
          item.statement,
        ),
    )
  )
    limits.push('Owning feature is not available from the current evidence.');
  if (
    /\b(dimensions?|parameters?|units?|width|height|length|diameter|mass|volume)\b/i.test(
      prompt,
    )
  )
    limits.push(
      ...result.uncertainties.filter(
        (item) =>
          item === technicalLimits.units || item === technicalLimits.parameters,
      ),
    );
  if (
    /\b(safe|safety|valid|validation|engineering|strength|stress|loads?)\b/i.test(
      prompt,
    ) &&
    result.uncertainties.includes(technicalLimits.validation)
  )
    limits.push('Engineering validation has not been run.');
  // Unknown future limits stay visible rather than guessing that they are generic.
  const generic: readonly string[] = Object.values(technicalLimits);
  limits.push(
    ...result.uncertainties.filter(
      (item) => item.trim() && !generic.includes(item),
    ),
  );
  return [...new Set(limits)];
}
