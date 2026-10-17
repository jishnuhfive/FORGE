import type { Answer } from './api';

type Fact = Answer['evidence'][number];
export type ModelSummary = {
  features: string[];
  counts: { value: string; label: string }[];
  unknowns: string[];
  notes: string[];
  mass: string | null;
};
const numeric = '(0|[1-9]\\d{0,5})';
const jsonString = '("(?:[^"\\\\]|\\\\.)*")';

/** Display grammar for existing server-owned statements, never arbitrary prose extraction.
 * No measurements, joins, activity or ownership are inferred. Ambiguity keeps prose. */
export function modelSummary(result: Answer): ModelSummary | null {
  const ids = result.evidence.map((item) => item.id);
  if (new Set(ids).size !== ids.length) return null;
  const find = (id: string): Fact | undefined =>
    result.evidence.find(
      (item) => item.id === id && item.status === 'verified',
    );
  const count = (id: string, label: string) => {
    const item = find(id);
    return item?.statement.match(
      new RegExp(`^The captured Part Studio contains ${numeric} ${label}\\.$`),
    )?.[1];
  };
  const featureCount = count('features', 'features?');
  const partCount = count('parts', 'parts?');
  const bodyCount = count('bodies', '(?:body|bodies)');
  if (
    featureCount === undefined ||
    partCount === undefined ||
    bodyCount === undefined
  )
    return null;
  const features: string[] = [];
  if (
    Number(featureCount) > 3 ||
    Number(partCount) > 2 ||
    Number(bodyCount) > 1
  )
    return null;
  for (let index = 1; index <= Number(featureCount); index++) {
    const ordinal = ['first', 'second', 'third'][index - 1];
    const item = find(`feature_${index}`);
    const match = item?.statement.match(
      new RegExp(
        `^The ${ordinal} captured feature is named ${jsonString} \\((?:sketch|extrude|fillet|chamfer); active\\)\\.$`,
      ),
    );
    if (!match?.[1]) return null;
    try {
      const name: unknown = JSON.parse(match[1]);
      if (typeof name !== 'string' || !name.trim() || name.length > 500)
        return null;
      features.push(name);
    } catch {
      return null;
    }
  }
  const paragraphs = result.answer
    .split(/\n\n+/)
    .map((text) => text.trim())
    .filter(Boolean);
  const canonical = features.length
    ? `This Part Studio contains ${featureCount} active ${features.length === 1 ? 'feature' : 'features'}: ${features.map((name) => JSON.stringify(name)).join(', followed by ')}.`
    : 'This Part Studio contains 0 captured features.';
  if (paragraphs[0] !== canonical) return null;
  const counts = [
    {
      value: featureCount,
      label: featureCount === '1' ? 'feature' : 'features',
    },
    { value: partCount, label: partCount === '1' ? 'part' : 'parts' },
    { value: bodyCount, label: bodyCount === '1' ? 'body' : 'bodies' },
  ];
  const unknowns: string[] = [];
  // Only condense the exact current inventory wording. Any extra qualification
  // or mismatch keeps the complete prose visible instead of silently dropping it.
  const names: string[] = [];
  let solidPart = false;
  for (let index = 1; index <= Number(partCount); index++) {
    const part = find(`part_${index}`)?.statement.match(
      new RegExp(
        `^Part ${index}: name ${jsonString}, reported body type ("(?:SOLID|SHEET|WIRE)"|unknown)\\.$`,
      ),
    );
    if (!part?.[1]) return null;
    names.push(part[1]);
    solidPart = partCount === '1' && part[2] === '"SOLID"';
  }
  const inventory = [
    `${partCount} ${solidPart ? 'solid ' : ''}${partCount === '1' ? 'part is' : 'parts are'} reported${names.length ? ': ' + names.join(', ') : ''}.`,
  ];
  // Topology is for this returned body only; never join it to a selection.
  const body =
    bodyCount === '1'
      ? find('body_1')?.statement.match(
          /^Body 1: reported type ("(?:SOLID|SHEET|WIRE)"|unknown); returned topology counts — face: (0|[1-9]\d{0,5}|unknown), edge: (0|[1-9]\d{0,5}|unknown), vertex: (0|[1-9]\d{0,5}|unknown)\.$/,
        )
      : null;
  if (bodyCount === '1' && !body) return null;
  inventory.push(
    `${bodyCount} ${body?.[1] === '"SOLID"' ? 'solid ' : ''}${bodyCount === '1' ? 'body is' : 'bodies are'} reported.`,
  );
  if (body) {
    const known: string[] = [];
    const missing: string[] = [];
    for (const [index, kind, label] of [
      [2, 'face', 'Faces'],
      [3, 'edge', 'Edges'],
      [4, 'vertex', 'Vertices'],
    ] as const) {
      const value = body[index];
      if (value === 'unknown') {
        unknowns.push(`${label} unknown`);
        missing.push(kind);
      } else if (value !== undefined) {
        known.push(`${value} ${kind} ${value === '1' ? 'entry' : 'entries'}`);
        counts.push({
          value,
          label: `returned ${value === '1' ? kind : label.toLowerCase()}`,
        });
      }
    }
    if (known.length)
      inventory.push(
        `Forge received ${known.join(', ')} for the captured body.`,
      );
    if (missing.length) {
      const words = missing.join(' and ');
      inventory.push(
        `${words[0]!.toUpperCase() + words.slice(1)} ${missing.length === 1 ? 'count remains' : 'counts remain'} unverified.`,
      );
    }
  }
  if (paragraphs[1] !== inventory.join(' ')) return null;
  return {
    features,
    counts,
    unknowns,
    notes: paragraphs.slice(2),
    mass:
      result.evidence.find(
        (item) =>
          item.id === 'mass' &&
          item.status === 'unknown' &&
          item.statement.startsWith("Mass isn't available because"),
      )?.statement ?? null,
  };
}

export function responseTitle(result: Answer): string | null {
  for (const kind of ['face', 'edge']) {
    const sentence = `One ${kind} is selected.`;
    if (
      result.answer.startsWith(sentence) &&
      result.evidence.some(
        (item) =>
          item.id === 'selection' &&
          item.status === 'verified' &&
          item.statement === sentence,
      )
    )
      return `Selected ${kind}`;
  }
  return null;
}
