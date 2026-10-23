# Hoax.ai public interpretation survey — operational release notes

**Status as of 2026-10-23:** The initial survey is live and a first end-to-end response was verified in private D1. Cohort metadata extension below is **proposed and not yet deployed**. Existing 2026-10-22 test responses must be retained but excluded from analysis.

## Rollout for source and prior-exposure metadata (Revision 2)

The public questionnaire remains one survey with the original five questions. The optional source referral label alone does **not** prove whether someone saw the site before completing Q1. Revision 2 adds an explicit self-report item at the end, after the original substantive questions. Name-only results from previously exposed visitors are retrospective and must **not** be compared as blind first impressions.

**Required order, to preserve existing participants:**

1. In Cloudflare D1 `hoax-interpretation-private`, run `survey-service/migrations/2026-10-23-source-exposure.sql` **once only** via Console. It uses additive columns and preserves existing records. Running it twice produces a duplicate-column error; never delete or recreate the table.
2. Update the existing `sohadot-hoax-interpretation` Worker in its dashboard from this repository's `survey-service/worker.mjs`. Keep `DB`, `FRONTEND_ORIGIN`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET` unchanged. This revision accepts legacy clients and returns `instrumentRevision: 2` on `GET /status`.
3. Confirm old survey `https://sohadot.com/hoax-ai-survey/` still works after the Worker update (legacy request payloads are supported), and inspect a private D1 record.
4. Only then merge and publish the Sohadot front-end revision that sends `instrument_revision:2`, `source_detail`, and the self-reported `prior_exposure`. Test end-to-end using `?ref=hoax`, `?ref=rick`, `?ref=discord`, as well as direct entrance.
5. Only after the new survey is confirmed should the separate HoaxAI homepage banner PR be merged, linking to `https://sohadot.com/hoax-ai-survey/?ref=hoax`. No changes to Hoax.ai's DNS, form, or data store.

**Storage and interpretation:** `referral` retains its legacy CHECK constraint. For `hoax`, `x`, and `linkedin`, the Worker stores `referral='other'` and the more precise `source_detail`. Old responses remain `instrument_revision=1`; later ones are 2. `prior_exposure` is a voluntarily self-reported yes/no/unsure field for completed responses. `source_detail` is a URL hint and can be modified by visitors; neither proves actual exposure or verified visitor identity.

**Private aggregate query example** (exclude known operational test IDs explicitly when reporting):

```sql
SELECT source_detail, prior_exposure, COUNT(*) AS completed
FROM survey_responses
WHERE completed_at IS NOT NULL
GROUP BY source_detail, prior_exposure
ORDER BY completed DESC;
```



The standalone page is planned at `https://sohadot.com/hoax-ai-survey/`. It does not alter `hoax.ai`, its DNS, or its GitHub repository. The page has `noindex` and is not linked from Sohadot navigation or sitemap.

## Respondent journey

1. Q1 asks a *name-only* question; do not show the site's description until the answer is saved.
2. `POST /start` stores Q1 immediately in a **private** Cloudflare D1 database, returning a random session capability kept only in the tab's session storage.
3. The respondent explores the real site using an external-tab link, and then voluntarily confirms they explored it. This is **self-reported**; it is not independently verified.
4. `POST /complete` accepts Q2–Q5 for that same session. Q1 is immutable. Incomplete sessions remain in D1 and may be analyzed as noncompletion.

## Setup (authorized Cloudflare operator only)

This design uses a Worker under the operator's `workers.dev` account subdomain: **no new DNS record and no change to GitHub Pages hosting are required**.

1. Confirm the questionnaire wording and run `npm test --prefix survey-service` locally.
2. In Cloudflare create D1 `hoax-interpretation-private`; run the SQL from `survey-service/schema.sql`. Create a Turnstile widget restricted to `sohadot.com`.
3. Copy `survey-service/wrangler.toml.example` to a **local ignored** `survey-service/wrangler.toml`; supply the D1 UUID and the **public** site key. Do not commit real credentials.
4. Deploy the Worker using Wrangler under the authorized account, and set the private secret with `npx wrangler secret put TURNSTILE_SECRET` (the initial deploy/secret ordering varies by Wrangler setup). Configure rate limiting/WAF or an equivalent abuse-control policy.
5. Confirm HTTPS `GET /status` returns `ready:true`, rejected attempts cannot write, and a legitimate first-and-final response is saved privately.
6. Insert the **public** `https://<worker>.<account>.workers.dev` API base URL into `hoax-ai-survey/config.json` (currently `null` deliberately). The browser will not accept submissions with a missing or unreachable endpoint.
7. Test on desktop, narrow mobile and keyboard; verify the first answer is saved *before* exposing the actual site. Confirm that scheduled deletion removes responses older than 90 days and that operators have a way to honor data-removal requests before launch.
8. Merge and distribute only after those production checks pass. Use `?ref=rick` and `?ref=discord` to obtain broad **unverified** recruitment-source categories.

## Boundaries

- No respondent email, name, account, or upload field. Application records question choices, a short optional comment, approximate source label, random response ID/token hash and timestamps. Cloudflare may process request metadata in its infrastructure.
- Do not publish raw D1 responses, individual comments, personal information accidentally volunteered, evaluation results, strategic valuations, purchase prices, or Sohadot's internal financial analysis in this public repository.
- The recruitment sources are convenience samples; first impressions may already be informed by prior familiarity. The survey **does not prove** causal commercial uplift, business demand, economic value, or that a participant actually read the site.

## Release checklist

- [ ] GitHub survey checks passing
- [ ] D1 private database provisioned
- [ ] Turnstile site key and secret configured
- [ ] Workers.dev API live; same-origin restriction verified
- [ ] Rate limiting and 90-day purge tested
- [ ] End-to-end browser submission checked
- [ ] Public survey config updated to real API address
- [ ] Merged only after all blockers resolved; link verified
