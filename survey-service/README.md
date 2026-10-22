# Hoax.ai public interpretation survey — operational release notes

**Status: STAGED ONLY. No live submission endpoint exists yet. Do not distribute the survey URL.**

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
