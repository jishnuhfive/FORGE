# Test ownership

Frontend unit/component tests live beside app source in `apps/web/src`.
Backend tests live in `apps/api/tests`. Cross-application browser tests live in
`tests/e2e` and run against the built placeholder in Chromium, Firefox, and WebKit.
Phase 0 tests require no real CAD data, provider credentials, or model calls.

Later features require meaningful boundary/failure-path tests. Keep fake providers
inside test code only; never advertise simulated integration behavior in the product.
