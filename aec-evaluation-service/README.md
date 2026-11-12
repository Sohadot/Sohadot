# AEC-UAT-ENG-001 — Private Evaluation Collection and Operator Dashboard

**Status: IMPLEMENTED IN CODE, NOT PROVISIONED OR LIVE.** The public page continues to work with downloads and optional email. `validation/aec-engineering/submission-config.json` is deliberately `enabled:false`; no remote submission is available until the operator performs and verifies the steps below. This is a separate service and database from the Hoax.ai survey.

## Architecture

- **Study page:** `https://sohadot.com/validation/aec-engineering/` on existing GitHub Pages.
- **Dedicated Worker custom domain (planned):** `https://aec-evaluation.sohadot.com`. Domain is *not provisioned* by this PR. Cloudflare Workers custom domain requires an active zone and appropriate operator permissions; it cannot be created by GitHub deployment.
- **Public API:** `GET /v1/status` and `POST /v1/evaluations`. CORS and request Origin only allow `https://sohadot.com`; Turnstile validation checks `sohadot.com` and action `aec_engineering_eval`. Responses are collected only after an explicit consent checkbox and actual challenge.
- **Database:** new private Cloudflare D1 binding `DB`, with only a random receipt ID, consent version, normalized evaluation payload, and UTC creation time. No IP address, user agent, raw challenge token, name, email or authentication credential is stored by this Worker.
- **Private dashboard:** `https://aec-evaluation.sohadot.com/admin` and private API under `/admin/api/`. The Worker validates a Cloudflare Access RS256 JWT signature against the **team JWKS**, exact issuer, intended application AUD and time constraints before any data read. Cloudflare Access must additionally protect `/admin*` at the edge with an explicit operator-only allow policy; **do not protect the public API routes under the admin policy**.
- **Retention:** Worker Cron runs daily and deletes rows older than 90 days. Deletion requests using the receipt ID are performed in the private Cloudflare D1 operator console; no public deletion interface is offered.
- **No access credentials in the static site.** The admin HTML is served only on the Worker after Access verification and never appears in the GitHub Pages publication manifest.
- **No telemetry on page load.** The study page makes external calls only after the reviewer explicitly consents and presses Submit. A disabled config gives a local-only outcome without calling Cloudflare challenge services.

## Required operator setup — in this order

1. **Review code and pass CI.** Run `node --test aec-evaluation-service/test/*.test.mjs` and the existing Pages/Chromium test suite. None of these tests provision live infrastructure.
2. **Create separate D1** database `sohadot-aec-engineering-private` in Cloudflare. Never reuse or migrate the existing Hoax.ai D1. Apply `aec-evaluation-service/schema.sql` to the *new* DB only; inspect schema and run a sanitized insert/select roundtrip in staging.
3. **Turnstile:** create a widget scoped to `sohadot.com`. Obtain public site key and secret. Set `TURNSTILE_SECRET` as a Worker secret; `TURNSTILE_SITE_KEY` is a non-secret environment variable. Verify server-side `action='aec_engineering_eval'` and hostname.
4. **Access policy:** create a Cloudflare Access self-hosted application for `aec-evaluation.sohadot.com/admin*` with an explicit operator identity allowlist (no public or broad organization allow policy). Obtain the team domain and audience tag. The Worker verifies JWT itself and fails closed if these are missing. Confirm Access does **not** block `/v1/status` or `/v1/evaluations`.
5. **Deploy worker:** locally copy `wrangler.toml.example` to ignored `wrangler.toml`; fill private D1 ID, team hostname, audience tag, and public Turnstile site key. Deploy by authorized Cloudflare operator only. Create/attach `aec-evaluation.sohadot.com` as a Worker Custom Domain; verify ownership and TLS. Configure WAF/rate limit for writes, edge logs without payload data and scheduled 90-day deletion.
6. **Verify private dashboard security:** without Access JWT, `/admin` and both private APIs must return 401. With a valid token for the *correct app AUD*, the list, aggregate dashboard and bounded pagination must work. Test expiration, wrong AUD, invalid signature and direct access to workers.dev. Avoid Access bypass policies.
7. **Verify public API:** before any test submission, `/v1/status` reports readiness; forged origin, missing consent, malformed records, bad Turnstile and oversized bodies all fail. Submit only a clearly labeled synthetic record, confirm a receipt and exactly one D1 row, verify duplicate-idempotency, remove the synthetic row. **Never mark a submission saved based only on browser UI.**
8. **Confirm 90-day retention:** exercise the Cron handler on synthetic dated rows. Document the operator process to delete a response by receipt ID; do not promise a deletion UI that does not exist.
9. **Separate activation PR:** after all production checks pass, update `validation/aec-engineering/submission-config.json` to `enabled:true` and `apiBase:"https://aec-evaluation.sohadot.com"`. Review the live page's CSP, consent wording and configured endpoints, then perform an independent real-browser end-to-end success test. Merge activation only with explicit owner approval.
10. **Recruit only after validated activation** and keep response access limited to authorized Sohadot operators.

### Manual deletion by receipt (private Cloudflare D1 Console)

Use a prepared parameter in Worker code or in the operator's private D1 console where supported, for example:

```sql
DELETE FROM aec_engineering_evaluations WHERE id = 'RECEIPT_UUID_HERE';
```

Confirm exactly one row was removed. Verify deletion; do not copy or log a participant's complete feedback into public tickets.

## Consent and data minimization

The study asks for no identifiers. Optional free text may inadvertently include identifying or confidential information; instruct users not to submit it. Cloudflare infrastructure may process connection metadata needed for security and service delivery. The page states a 90-day retention limit and purpose. The Worker validates controlled enumerations and caps free text. User-selected `present` flags are self-reported; no engineering claim or scientific review is inferred from submissions.

Human participants are a convenience sample. The dashboard reports counts, **not an overall grade**. It cannot prove independent accreditation, completion of the external Workbench tasks, engineering correctness, conversion lift or causal effect. Treat all comments as review candidates requiring source inspection before changes.

## Failure modes and release blockers

- Missing database, Turnstile secret or authorized origin → public API unavailable; HTML retains local exports.
- Missing or invalid Access configuration/JWT → private results inaccessible.
- Deployment cannot be confirmed → keep public submission config disabled.
- Request fails or receipt mismatches → no success statement. Reviewer can retry or download local report.
- Configured Worker without Cloudflare Access operator policy → **NOT PRODUCTION APPROVED**, even if its built-in JWT validation denies unauthorized requests.
- Access route includes `/v1/*` → public submissions blocked; correct policy rather than bypass security.
- Unexpected external POST or data leakage in browser audit → block activation immediately.

## Cloudflare and security references

- [Worker Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)
- [Cloudflare Access JWT validation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
- [Turnstile server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)
- [Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)

**No existing Hoax.ai Worker, D1 binding, GitHub Pages deployment workflow, or AIElectronicChips.com repository is to be modified for this feature.**
