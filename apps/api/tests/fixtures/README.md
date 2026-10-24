# A1 synthetic parameter fixture

`modify_parameters.json` is test data, not a captured user model or live provider
conformance evidence. All identities and queries are invented.

Extrude follows the official [REST example](https://onshape-public.github.io/docs/api-adv/featureaccess/):
solid NEW BLIND, entities, and `depth` / `BTMParameterQuantity-147` / expression.
Fillet tests the narrow radius quantity, entities and tangentPropagation contract.
Radius semantics are documented in the official
[standard library](https://cad.onshape.com/FsDoc/library.html#opFillet-Context-Id-map);
the feature guide documents REST quantity/query/Boolean encodings. This fixture
does not establish current UI-created Fillet serialization. Other parameter shapes
reject pending evidence and review. See [A1 limitations](../../../../docs/HACKATHON_MODIFY_A1.md).

`modify_ui_parameters.json` is a separate Phase 16 synthetic fixture: 50 standard
Extrude inputs and 38 standard Fillet inputs, based on the official standard
library predicates and human-reported writes-OFF metadata documented in
[the Phase 16 record](../../../../docs/PHASE_16_MODIFY_LIVE_CONFORMANCE.md).
All node IDs, queries and incidental dormant quantities are invented. It is not
a private capture or proof of real write conformance. It exercises the expanded
closed contract, explicit mode guards, empty inactive queries/arrays, ordinary
overflow=true, and zero/empty quantity bookkeeping. Tests preserve the entire
definition and reject unknown fields/IDs, enabled richer modes, malformed data,
stale evidence and any unrelated post-write change. The original minimal fixture
and all of its assertions remain unchanged. The same real disposable UI fixture
must still pass the separate human writes-OFF recheck before any write trial.

The common-metadata repair adds invented empty `parameterName` / `valueString`
placeholders to representative enums, quantities, Booleans, queries and arrays.
Their string types come from the current official `/api/openapi` base parameter
schema; the feature API guide documents omitted empty-string defaults. This is
not evidence of the private fixture's text values. Nonempty text remains
unsupported. The next human checkpoint confirmed `libraryRelationType=DEFAULT`
on the ordinary Extrude domain and Fillet filletType parameters; those two exact
schema-defined constants are now included. No other library state is accepted.
This is preserved serialization metadata, never proof of configuration/import
eligibility. Tests exercise the empty placeholders on every known parameter
independently and preserve the unchanged 8 KiB replacement limit. No imported/
configured behavior or nondefault library state is added.

The latest real writes-OFF checkpoint still fails both entities envelopes.
Current OpenAPI documents optional polymorphic filter metadata, but no actual
serialized tree has been supplied. These fixtures remain filter-free synthetic
profiles, not proof of the current real UI envelope. Query-filter test trees are
invented SDK-shaped rejection cases only. No guessed filter is added or accepted.

The legacy safety repair keeps this historical JSON unchanged but now validates
its entire parameter and query envelopes. All five Extrude and all three Fillet
parameters (including tangentPropagation) are required exactly once. Historical
query items contain only btType plus featureId (Extrude region) or queryString
(Fillet individual query). Parameter nodeId strings and quantity isInteger=false
remain supported by the existing metadata-preservation tests. Current-UI fields,
filters and unknown nested fields cannot be smuggled into the minimal profile.

`modify_source_filters.json` contains invented SDK-shaped candidates derived from
public FeatureScript 3095 entities annotations. Expected signatures, preorder
leaf states and 13/5 versus 17/8 node/depth counts are explicit. These match the
human aggregate counts, not proven real REST topology/fields. Optional edge
isInternalEdge and sketch objectType are deliberately absent and diagnosed as
missing. Every candidate remains rejected in active, mismatched and inactive
roles; no target filter acceptance or normalization is introduced.
