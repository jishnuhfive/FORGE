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

An earlier real writes-OFF checkpoint failed both entities envelopes before exact
filter evidence was supplied. The parameter fixtures remain filter-free synthetic
profiles, not proof of the current real UI envelope. Early query-filter test trees
remain invented SDK-shaped rejection cases; the later complete evidence has a
separate fixture below. No guessed filter is accepted from source intent alone.

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

`modify_observed_filters.json` is the subsequent strict-contract fixture. It
reconstructs synthetic provider-shaped objects from the complete human-reported
sanitized topology and leaf evidence, using official OpenAPI discriminators and
field names. It contains no private provider capture, identifiers or queries.
Only its exact matching current-UI `entities` roles are accepted: Extrude 13 nodes /
depth 5, Fillet 17 / 8. Every leaf value and operand slot is explicit; missing
optional schema fields do not acquire defaults. Diagnostic strings in this fixture
are expected output only and are never production acceptance authority. Tests
combine these trees with the unchanged 50/38-input UI parameter fixture, preserve
all accepted fields, and reject every role/schema/state deviation. The original
source candidates deliberately remain incomplete and rejected. Neither the
reconstruction nor mock replacement tests prove real live write conformance; the
next human writes-OFF exact-match Inspector checkpoint remains mandatory.

`modify_current_query_filters.json` reconstructs all 13 Extrude and 8 Fillet query
roles from the complete human sanitized evidence supplied for both Inspector
variants. It contains only official SDK-shaped filter metadata, role names and
expected counts/depths/query cardinality; no private capture/identities/queries.
The complete profile combines it with the existing synthetic 50/38-parameter
fixture. Immutable production trees are separate from this test fixture and never
compare diagnostic strings. Dormant roles are empty; only the exact direction
role has depth 9. Full replacement tests preserve every filter/empty list and
metadata field within the separately authorized 32 KiB wire cap. Historical and
earlier incomplete/source-derived fixtures remain separate and retain rejection
for their unsupported fields/states. Real writes remain unproven.
