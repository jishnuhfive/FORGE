# Test ownership

Frontend unit/component tests live beside app source in `apps/web/src`.
Backend tests live in `apps/api/tests`. Cross-application browser tests live in
`tests/e2e` and run against the built production UI (4173) and development lab
(4174) in Chromium, Firefox and WebKit. Build before running. No real CAD data,
provider credentials or model calls are required.

Later features require meaningful boundary/failure-path tests. Keep fake providers
inside test code only. Phase 1 synthetic UI fixtures belong in the DEV-only lab,
with clear provenance and no fake service behavior in the normal workspace.
