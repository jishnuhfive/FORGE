# Local infrastructure

The root `docker-compose.yml` runs PostgreSQL only. Web and API run natively for
fast reloads. The root Dockerfile and Railway config now provide a separate
[production foundation](../docs/DEPLOYMENT.md), not yet hosted.
The PostgreSQL 18 volume mounts `/var/lib/postgresql`, its supported parent data
directory. Ports bind only to loopback. Local credentials are public development
placeholders and must never be used in production.

`make db-up` waits for health. `make db-down` retains the named data volume. Change
credentials on existing databases through an explicit migration; changing Compose
environment variables alone does not change credentials inside existing volumes.
Never use `down --volumes` on valuable data without explicit approval and backups.

Source: [official PostgreSQL image](https://hub.docker.com/_/postgres).
