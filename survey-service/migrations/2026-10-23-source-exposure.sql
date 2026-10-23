-- Run ONCE in the existing private D1 database before deploying worker revision 2.
-- Preserves every existing response and leaves the two 2026-10-22 test rows intact.
-- Existing rows remain instrument_revision=1 with prior_exposure=NULL.
ALTER TABLE survey_responses ADD COLUMN source_detail TEXT
  CHECK(source_detail IN ('rick','discord','direct','other','hoax','x','linkedin'));
ALTER TABLE survey_responses ADD COLUMN instrument_revision INTEGER NOT NULL DEFAULT 1
  CHECK(instrument_revision IN (1,2));
ALTER TABLE survey_responses ADD COLUMN prior_exposure TEXT
  CHECK(prior_exposure IN ('yes','no','unsure'));
-- Optional, legacy rows: identify already-known source from the old referral code.
UPDATE survey_responses SET source_detail = referral WHERE source_detail IS NULL;
