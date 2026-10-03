# Future database boundary

SQLAlchemy and psycopg are installed. No engine, session, tables, migrations, seed
data, or automatic schema creation exists. `DATABASE_URL` is optional and redacted.
Add scoped sessions and reviewed migrations only when persistence is authorized.
Design future user ownership, encrypted token storage, audit retention, and deletion
from the requirements in `docs/SECURITY.md` before creating real multi-user records.
