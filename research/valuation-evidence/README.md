# Valuation evidence research (Sprint 1A)

Research material only. Nothing in this directory is read by the production
valuation engine or shown in the valuation tool.

| Path | Content |
| --- | --- |
| `schema/transaction-evidence.v1.schema.json` | Structural schema for registry records |
| `registry/transactions.v1.json` | Transaction Evidence Registry v1 (49 transactions) |
| `investigations/seed-45.v1.json` | Investigation of the 45 published comparable sales |
| `holdout/status.v1.json` | Holdout status (`NOT_READY`). Holdout records are never stored in this public repository. |

The standard, findings and protocols are in `docs/valuation-evidence/`.

Validate with `python3 scripts/validate_evidence_registry.py`. After editing
the registry, run `python3 scripts/validate_evidence_registry.py --write` and
`python3 scripts/render_seed_investigation.py`.
