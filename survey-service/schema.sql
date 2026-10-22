-- Sohadot-controlled private Cloudflare D1. No private results in GitHub.
CREATE TABLE IF NOT EXISTS survey_responses (
 id TEXT PRIMARY KEY NOT NULL,
 secret_hash TEXT NOT NULL,
 version INTEGER NOT NULL CHECK(version=1),
 q1 TEXT NOT NULL CHECK(q1 IN ('detector','guidance','news','other','unsure')),
 referral TEXT NOT NULL CHECK(referral IN ('rick','discord','direct','other')),
 q2 TEXT CHECK(q2 IN ('evidence','detector','reporting','unsure')),
 q3 TEXT CHECK(q3 IN ('checklist','sources','synthetic','gaps')),
 q4 TEXT CHECK(q4 IN ('regular','occasional','conditional','unlikely')),
 q5 TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 completed_at TEXT
) STRICT;
CREATE INDEX IF NOT EXISTS survey_by_date ON survey_responses(created_at);
