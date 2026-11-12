# AEC-UAT-ENG-001 — Independent Engineering Evaluation Pilot

**Owner:** Sohadot  
**Subject:** AIElectronicChips.com / Research Workbench, Workflow C documentary preflight  
**Evaluation page:** `/validation/aec-engineering/`  
**Release state:** Draft pilot; no respondents have been recruited and no results are claimed.

## Why this exists

The evaluation examines whether technically knowledgeable participants can use the existing AIElectronicChips.com documentary preflight to identify documentary gaps and understand evidence boundaries. It is not a validation of any real data-center deployment, a product certification, or independent scientific peer review.

The evaluator interacts with the actual tool in a separate tab. This questionnaire cannot observe whether the tool was opened or used; task completion is self-reported. Only answers voluntarily exported or emailed can be examined by Sohadot.

## Protocol and sampling

- Recruit 3–5 willing participants who have relevant exposure to data-center electrical engineering, commissioning, network or systems operations, or technical due diligence. This is a formative usability pilot, not a statistically representative survey.
- Invite participants independently of development; do not describe the expected answers before they attempt the tasks.
- Do not reward favorable responses. Do not represent one participant as an independent certified reviewer of the entire methodology.
- Record specialization in broad categories, prior exposure, voluntary experience range and inability to attempt a task. No names, contact details, real facility information or confidential documents are requested.
- Do not assume completion because a participant clicks Next. Record the explicit self-reported task outcome.
- The protocol is an evaluation of a Sohadot-developed product hosted by Sohadot. "Independent" refers to the invited evaluator's perspective, not an accredited independent auditing organization.

## Three scenarios and organizer-side reference expectations

These expected behaviors are for the owner evaluating the results, NOT a script to give the participant in advance.

1. **Power redundancy / rc-03:** A commissioning record is reported held; method and results present; acceptance criteria missing and date unknown. An appropriate document-preparation aid should surface those gaps, identify why criteria and date matter, and distinguish collection from commissioning success. It must not treat the record as authenticated.
2. **Formal acceptance / rc-12:** Integrated technical testing is documented but the agreed criteria are missing and a signed formal acceptance is unknown. A useful tool should distinguish technical-test evidence from formal decision and identify separate requested records. It must not infer contractual acceptance from technical testing.
3. **Regulatory access / rc-15:** A general regulation is available. Even if all reported record attributes are present, it does not establish transaction-specific legality or site-level deployment. This is a wording and inference-boundary test, not a request for a legal opinion.

The participant is free to disagree with the tool or find other issues. Do not mark a participant wrong for raising a legitimate alternative that the current methodology misses.

## Instrument

The voluntary evaluation is six screens: reviewer context, task rc-03, task rc-12, task rc-15, professional ratings and issue reporting, and review/export.

- Task completion: independently completed / partially completed / not completed / could not attempt.
- Technical observation: clearly / partly / not clearly / unable to assess.
- Six optional 1–5 ratings; do not equate them to engineering correctness or create an overall numerical score.
- Technical issue: yes / no / unsure, with a required explanation only when yes.
- Suggestions and first-task observations: optional bounded text, with an explicit request not to enter sensitive information.
- A complete JSON or CSV report is generated entirely in the browser; a short summary can be copied. Email is voluntary and opens only an unsent draft, prompting the participant to attach JSON if they want to share full details.

### Privacy and handling of replies

The study page has no analytics, submission endpoint, cookies, browser storage, uploads or remote form calls; no response is stored by the page. Ordinary hosting and visiting an external website may still involve network metadata.

**Collected results depend on participants deliberately sending a file/email** to `agent@sohadot.com`. No central database, automatic aggregation, participant tracking, or result-receipt acknowledgment is implemented. Do not describe an email draft as a successful submission.

If emailed results are received, restrict access, do not publish raw participant comments or metadata, and set a retention and deletion policy before recruitment. Exclude any accidental confidential material from analysis and handle it under applicable privacy requirements. A future collection backend must be designed, consented and reviewed separately; do not reuse the Hoax.ai survey service or Cloudflare D1 without explicit authorization.

The public page uses `noindex,nofollow,noarchive,noimageindex`, is absent from the sitemap and normal navigation; it is **not access-controlled**. A public GitHub repo and unindexed public URL must never be treated as private.

## Evaluation rubric

Record each test as observed, self-reported, untested or blocked. Do not convert missing answers into failures or into passes.

Suggested formative quality gate:

- Browser flows and export functionality: no unresolved critical defect.
- Technical boundaries: zero verified misleading claims in the three scenarios.
- Participant task completion: describe raw counts, e.g., `4/5 independently completed`, per task, without pretending the sample is statistically representative.
- Technical relevance, usability, exports and clarity: report each rating distribution and exact cited concerns. Do not generate a pooled score.
- Engineering disagreements: collect the literal statement at issue, independently inspect the governed source, and classify as verified error, unresolved, or product-copy improvement.

The site must not claim independent expert validation until the reviewer has actually reviewed and explicitly consented to the scope and attribution, and even then only the reviewed portion should be described.

## Publication and rollback

This pilot adds only three explicitly enumerated files to `deploy/pages-manifest.json`. It is not linked from the main navigation or sitemap. It has a strict local-content CSP and does not load the main site's analytics or advertising.

1. Review PR and passing CI before any merge.
2. Owner authorizes the deployment separately via the normal guarded merge to `main`.
3. After deployment, test mobile/desktop keyboard interactions and exports from the live URL using synthetic answers.
4. Recruit human participants only after the privacy and operational instructions are approved.
5. If an integrity or disclosure issue is found, remove the explicit files from the manifest to unpublish the route and handle any responses already received appropriately.

**There is no automated human-review conclusion or certification.**
