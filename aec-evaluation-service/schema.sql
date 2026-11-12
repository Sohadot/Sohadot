-- Dedicated private D1 database; never use the Hoax.ai survey database.
-- No names, emails, IP addresses, user agents, raw Turnstile tokens or credentials stored.
CREATE TABLE IF NOT EXISTS aec_engineering_evaluations (
  id TEXT PRIMARY KEY NOT NULL,
  consent_version TEXT NOT NULL CHECK(consent_version = '2026-11-12'),
  payload TEXT NOT NULL CHECK(json_valid(payload)),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
CREATE INDEX IF NOT EXISTS aec_evaluations_created_at ON aec_engineering_evaluations(created_at);
