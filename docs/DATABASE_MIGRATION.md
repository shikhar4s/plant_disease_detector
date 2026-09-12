# Database and preview migration runbook

The current Render database `plantdoc-preview-db` expires on **11 October 2026 at 13:37:40 UTC**. The service is not durable until `DATABASE_URL` points to a lasting PostgreSQL instance.

No paid database is provisioned automatically. Before the deadline:

1. Create or select a lasting PostgreSQL provider in a region suitable for the Singapore Render service. Confirm its free-plan retention, sleeping, storage and egress terms; plans can change.
2. Put the destination URL in a secure local environment variable. Do not paste either URL into logs, issues or commits.
3. Quiesce writes for a short maintenance window, export the Render database with `pg_dump --format=custom`, and restore with `pg_restore --clean --if-exists --no-owner`.
4. Run `python manage.py migrate --noinput` against the destination and compare counts for users, analysis results, snapshots and watchlist rows.
5. Change the Render service's private `DATABASE_URL`, deploy, and test login, account isolation, history images, notes and watchlists.
6. Keep the old database untouched until the new service has been verified and a second export exists.
7. Remove the `fromDatabase` binding from `render.yaml` before any future Blueprint sync, otherwise the expiring database can be reattached.

Migration `0003_platform_intelligence` converts existing diagnosis preview data URIs to compact JPEG bytes in PostgreSQL and clears the redundant base64 text when decoding succeeds. New diagnosis originals are never written to Render's ephemeral filesystem. A future private object-store migration should copy previews first, verify checksums and ownership-scoped reads, then clear database bytes only after rollback has been tested.
