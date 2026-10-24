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
