# Seller-Approved Escrow Closing Protocol

**Public page:** `escrow-closing.html`
**Status:** Documentation of an existing closing pathway. No payment processing, escrow API
integration, or transaction automation is added by this document or by the public page it describes.

## Purpose

Sohadot's acquisition path (Home → Portfolio / Category Artifacts / Category Clusters → Strategic
Brief) qualifies serious buyer interest but deliberately stops short of a transaction. This protocol
documents what happens *after* that interest becomes a real, written deal: how a qualified Sohadot
asset transaction may close through an **independent escrow provider**, and under what conditions.

Sohadot does not process direct payments on-site. Qualified asset transactions may close through
independent escrow only after written agreement and seller approval.

## Public boundaries

`escrow-closing.html` is a trust and process page, not a transaction system. It intentionally contains:

- No price list or pricing table.
- No payment form, card field, or checkout flow.
- No escrow account numbers, API keys, or integration code.
- No public "start transaction" control of any kind.
- No buyer's private data — the page is generic and static, addressed to no one in particular.

Positioning held constant throughout the page and this document:

- Sohadot is not a marketplace.
- Sohadot does not offer public checkout.
- Sohadot does not operate as a third-party domain broker.
- No asset can be purchased automatically from the website.
- Escrow closing applies only to Sohadot-owned or Sohadot-controlled asset transactions — not to
  domains Sohadot does not own or control.
- Escrow closing is available only after written agreement between buyer and seller.
- The seller initiates or approves the closing path.
- The buyer funds escrow through an independent escrow provider.
- The domain is transferred only after escrow funding is secured.
- Funds are released only after the agreed transfer process is completed.

## Closing sequence

The protocol is a fixed seven-step sequence. No step is automated past the seller-approval gate, and
no step is skipped:

1. **Strategic brief requested.** A buyer (or seller, on behalf of a counterparty) opens a Strategic
   Brief naming the asset, cluster, or relationship in question.
2. **Buyer and seller discuss asset, scope, price, and terms in writing.** This happens off-platform,
   directly between the parties — Sohadot's public pages play no further role once the conversation
   starts.
3. **Seller confirms that the asset is eligible for closing.** Not every inquiry reaches this point,
   and reaching it is not a guarantee of sale.
4. **Escrow transaction is initiated or approved by the seller.** This is the seller-approval gate —
   see below.
5. **Buyer funds escrow.** This is the buyer-funding gate — see below.
6. **Seller transfers the domain through the agreed registrar method.** This is the domain-transfer
   gate — see below.
7. **Escrow releases funds after the transfer conditions are satisfied.** This is the release gate —
   see below.

## Seller approval gate

No escrow transaction exists, and no funding request goes out, until the seller has explicitly
initiated or approved it. Sohadot does not open an escrow transaction on a buyer's behalf, and a
completed Strategic Brief does not itself trigger escrow — it starts the written conversation in step
2, nothing more.

## Buyer funding gate

Escrow is funded directly by the buyer, through the independent escrow provider's own funding channel
— not through Sohadot.com. Sohadot never touches, holds, or forwards buyer funds; it has no payment
processing capability on this or any public page.

## Domain transfer gate

The domain transfers only after escrow funding is confirmed secured by the independent escrow
provider. The seller carries out the transfer through the agreed registrar method (e.g. registrar
push, auth-code transfer) — Sohadot does not execute or automate the transfer itself.

## Release gate

Escrow funds release to the seller only after the agreed transfer conditions are satisfied and
confirmed by the escrow provider — not on a timer, not automatically on funding, and not by Sohadot.

## What is not automated

- Opening an escrow transaction (requires seller approval).
- Funding escrow (requires the buyer's own deliberate action with the escrow provider).
- Transferring the domain (requires the seller's own registrar-side action).
- Releasing funds (requires the escrow provider's confirmation that transfer conditions were met).
- Deciding that an inquiry qualifies for closing (requires the seller's own confirmation — step 3).

## What is intentionally not public

- Any specific escrow provider's account credentials, API keys, or integration code.
- Any buyer's name, email, or deal terms — those exist only in the private, written conversation
  between buyer and seller, never on a public Sohadot page.
- Any mechanism to create, fund, or release an escrow transaction from the website. A private,
  seller-gated operator tool for Sohadot's own internal use is specified — but not implemented — in
  `docs/OPERATOR_ESCROW_LAUNCHER_SPEC.md`, and it must never live in this public repository with
  secrets attached.

## Strategic conclusion

Sohadot separates acquisition interest from transaction closing. Public pages qualify serious buyers;
escrow closing begins only after written agreement and seller approval, preserving the strategic-asset
posture while enabling professional transaction execution.
