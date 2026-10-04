# Database boundary

SQLAlchemy models and explicit Alembic migrations own Phase 2 users, authorizations,
opaque sessions, OAuth states, preference foundations and minimized audit events.
Startup verifies the migration revision; it never creates or destroys tables.
PostgreSQL row locks serialize rotating refresh tokens. SQLite is a unit-test-only
backend, with separate real PostgreSQL concurrency tests. See docs/AUTHENTICATION.md.
