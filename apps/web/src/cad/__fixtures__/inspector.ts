/** Invented UI/test evidence only; imported by the DEV lab, never live fallback. */
import type { Inspector } from '../inspector';
import type { ReadProof } from '../api';
import { syntheticProof } from './proof';
export function inspectorFixture(
  source: ReadProof = syntheticProof,
): Inspector {
  const list = <T>(items: T[], success: boolean) => ({
    items,
    completeness: success ? ('complete' as const) : ('unavailable' as const),
    returned_count: items.length,
    omitted_count: 0,
  });
  return {
    schema_version: 'forge-cad-inspector-v1',
    context: {
      kind: 'workspace_part_studio',
      configuration: 'default',
      evaluation: 'end_of_list',
    },
    source,
    freshness:
      source.consistency === 'mismatch' ? 'stale' : 'captured_unverified',
    features: list(
      Array.from({ length: source.features.count ?? 0 }, (_, i) => ({
        index: i + 1,
        name:
          i === 0
            ? 'Sketch 1'
            : i === 1
              ? 'Extrude 1'
              : `Synthetic feature ${i + 1}`,
        feature_type: i === 0 ? ('sketch' as const) : ('extrude' as const),
        suppression: 'active' as const,
        completeness: 'complete' as const,
        omitted_parameters: 0,
        parameters:
          i === 1
            ? [
                {
                  label: 'end depth',
                  kind: 'expression' as const,
                  state: 'available' as const,
                  text: '12 mm',
                  boolean: null,
                  count: null,
                },
                {
                  label: 'opposite direction',
                  kind: 'boolean' as const,
                  state: 'available' as const,
                  text: null,
                  boolean: false,
                  count: null,
                },
              ]
            : [],
      })),
      source.features.status === 'success',
    ),
    parts: list(
      Array.from({ length: source.parts.count ?? 0 }, (_, i) => ({
        index: i + 1,
        name: `Part ${i + 1}`,
        description: 'Synthetic preview part',
        part_number: 'DEMO-001',
        body_type: 'SOLID',
        state: 'IN_PROGRESS',
        is_mesh: false,
        mass: 'unverified' as const,
        completeness: 'complete' as const,
      })),
      source.parts.status === 'success',
    ),
    bodies: list(
      Array.from({ length: source.bodies.count ?? 0 }, (_, i) => ({
        index: i + 1,
        body_type: 'SOLID',
        face_count: 6,
        edge_count: 12,
        vertex_count: 8,
      })),
      source.bodies.status === 'success',
    ),
    physical: {
      mass:
        source.mass.status !== 'success'
          ? 'unverified'
          : source.mass.count === 0 || source.has_mass === false
            ? 'unavailable'
            : source.has_mass === true
              ? 'available'
              : 'unverified',
      volume:
        source.mass.status !== 'success'
          ? 'unverified'
          : source.mass.count === 0
            ? 'unavailable'
            : 'reported',
      missing_mass:
        source.mass.status !== 'success' || source.mass.count === 0
          ? null
          : source.has_mass === false,
      units: 'provider_native_unverified',
      scope: 'aggregate',
    },
  };
}
