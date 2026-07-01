# Operator Escrow Launcher — Specification (Not Implemented)

**This sprint does not implement the operator console. This sprint only documents the public
protocol and future private launcher requirements.**

Nothing in this document is wired to code, and no route, form, function, or credential exists in this
repository as a result of it. It exists so that if a private operator tool is built later, it is built
against a spec that already assumes the constraints below — not bolted onto the public site after the
fact.

## Private-only operator console concept

The Operator Escrow Launcher is a concept for a **private, internal-only** tool used by Sohadot's own
operator (not by buyers, not by the public) to record a seller-approved closing and hand it to an
independent escrow provider. It is the private counterpart to the public
`docs/ESCROW_CLOSING_PROTOCOL.md` — the public page explains the protocol to buyers and sellers; this
tool would let the operator *execute* step 4 of that protocol ("Escrow transaction is initiated or
approved by the seller") once the seller has actually approved it off-platform.

It is not part of `sohadot.com` as a public surface. It would not be reachable from
`escrow-closing.html`, `strategic-brief.html`, or any other public page, and it would not be built on
GitHub Pages, which serves this repository's static files directly to the public and cannot hold
secrets.

## Fields required after agreement

Once a buyer and seller have reached written agreement (protocol step 2) and the seller has confirmed
eligibility (step 3), the operator console would need to record:

- `asset` / `domain` — the specific domain being transacted.
- `buyer_name`
- `buyer_email`
- `agreed_price`
- `currency`
- `escrow_fee_payer` — buyer, seller, or split.
- `inspection_period` — the agreed escrow inspection/holding window.
- `registrar_transfer_method` — how the domain will actually move (registrar push, auth-code, etc.).
- `written_agreement_reference` — a pointer to the off-platform written agreement (e.g. an email
  thread ID or document reference), not the agreement's contents.
- `notes` — free-text operator notes.

None of these fields, or any real values for them, exist anywhere in this public repository. They are
listed here only as the schema a future private tool would need.

## One-click operator action

- **Create Escrow Transaction** — a single operator-triggered action that takes the fields above and
  opens a transaction with the independent escrow provider via that provider's own API. This action is
  only available to the operator, after the seller-approval gate (protocol step 4) has already been
  satisfied off-platform; the tool does not decide eligibility or approval itself, it only records a
  decision that has already been made.

## Security requirements

Any future implementation of this concept must satisfy all of the following before it is built:

- **No API keys in GitHub Pages.** This repository is served as static files directly to the public;
  nothing that touches an escrow provider's credentials may live here.
- **No escrow credentials in JavaScript.** Client-side code delivered to a browser is public by
  definition, regardless of how it is obfuscated.
- **No private buyer data in public repo.** Buyer names, emails, prices, and agreement references
  belong in a private data store the operator tool controls — never committed to
  `Sohadot/Sohadot` or any other public repository.
- **Backend only.** The tool must run as a private, authenticated, server-side function — for example
  a Cloudflare Worker, a serverless function behind an operator login, or another private backend —
  never as static site code.
- **Secrets in environment variables only.** Escrow-provider API keys and any other credentials must
  be stored as environment variables on the private backend, never in source, config files, or the
  public repository.
- **Seller approval required before creation.** The "Create Escrow Transaction" action must be
  unreachable, or a no-op, until the seller has approved closing for that specific asset — the tool
  must not be able to originate a transaction on its own initiative.

## Explicitly out of scope for this sprint

This sprint does not implement the operator console. This sprint only documents the public protocol
and future private launcher requirements.
