# Private valuation vault

Local storage for comparable-sale research. This is processing tooling. It does not change the published valuation engine, admit a calibration batch, or evaluate the holdout.

The Sprint 1B rules in `scripts/sales_pipeline.py` still decide eligibility. `scripts/valuation_vault.py` only imports, stores, reports, and applies a default-deny export gate. `ADMISSION_OPEN` stays `False`. A record in `calibration/` is a candidate, not an admitted observation. A record in `holdout/` is segregated storage, not a holdout evaluation, and it does not change `research/valuation-evidence/holdout/status.v1.json`.

## Location

The vault path is the environment variable `SOHADOT_PRIVATE_ROOT`. Put it in a sibling of the checkout, not inside the Git working tree:

```text
parent\
├── Sohadot\
└── valuation-vault\
    ├── sources\
    ├── licences\
    ├── raw-sales\
    ├── verified-sales\
    ├── calibration\
    ├── holdout\
    ├── evaluation\
    ├── export\
    ├── audit\
    └── config\
```

The tool refuses a path inside any Git working tree, and it refuses a junction or symbolic link on the vault or a stage directory. Do not run `git init` in the vault. The repository `.gitignore` ignores `/valuation-vault/` only as a backstop if that folder is created inside the checkout by mistake.

Public CI does not read `SOHADOT_PRIVATE_ROOT`. Tests use a temporary directory.

Real-data import is disabled. A reference string inside a JSON record is not treated as proof of a licence. Import of a non-synthetic file is refused until licence binding is implemented and separately approved.

`synthetic: true` is a self-declared dataset label. It is not cryptographic proof that the records are synthetic, and it does not authorise a real or licensed import. The prohibition is `REAL_IMPORT_PERMITTED`, which remains `False`.

## Rights and export

Five permissions are separate. A grant for one does not imply the next.

| Question | Where it is recorded | If missing |
| --- | --- | --- |
| May the record be stored privately? | `rights.storage` | Eligibility blocker `RIGHTS_NOT_ESTABLISHED` |
| May it be used for internal commercial modelling? | `rights.commercial_modelling` | Same blocker. This does not authorise publication. |
| May a derived valuation be served publicly? | `pipeline.publication_authorization.serve_derived_valuations_publicly` | Export denies derived publication |
| May aggregate statistics be disclosed? | `pipeline.publication_authorization.disclose_aggregate_statistics` | Export denies aggregates |
| May the individual transaction be redistributed? | `rights.redistribution` | The record file is not copied to `export/approved/` |

A secondary publisher grant still needs `upstream_rights_confirmed: true`. Holdout records, licence files, raw-sale files, and material that looks like a credential are never approved. `export` writes `export/manifest.json` inside the vault and does not copy files into the Git repository.

## Disk encryption and backup

Creating the folder does not encrypt it and does not create a backup. The name of a parent directory does not establish either.

Before any real transaction is imported:

1. Confirm the volume uses BitLocker or equivalent full-disk encryption. This tool does not turn encryption on.
2. Keep backups on an encrypted volume or in an encrypted archive.
3. Do not place the vault in OneDrive, Dropbox, Google Drive, iCloud, or any other automatic sync folder.
4. Do not store passwords, API keys, or encryption passphrases in the vault or in the source tree.

`config/SECURITY.md` inside the vault repeats these requirements. It is not evidence that they have been met.

## Windows setup

From the Sohadot checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_valuation_vault.ps1 -VaultPath <path-outside-the-repository>
```

The script creates that directory only after it has checked that the path is not a Git root and is not inside a Git working tree. It sets the user-level `SOHADOT_PRIVATE_ROOT` variable and limits the vault's access list to the current user, Administrators, and SYSTEM. It does not change machine policy and it does not initialise Git.

Open a new PowerShell window so the user environment variable is visible. The synthetic demonstration refuses `SOHADOT_PRIVATE_ROOT` and any directory that already contains transaction files:

```powershell
python scripts\valuation_vault.py demo --root <empty-disposable-directory>
```

## Synthetic demonstration

`build_synthetic_import()` builds records that are labelled synthetic. They are not sales.

| Id | Case | Expected result |
| --- | --- | --- |
| `SYN-TX-VALID` | Completed sale, storage and modelling granted, redistribution unestablished | Eligible candidate. Not exported. |
| `SYN-TX-PENDING` | Announced agreement | Blocked: completion not evidenced |
| `SYN-TX-UNPAID` | Unpaid auction | Rejected: not a completed sale |
| `SYN-TX-DUPLICATE` | Second report of the valid sale | Rejected: duplicate report |
| `SYN-TX-BADPRICE` | Negative price | Blocked: price invalid |
| `SYN-TX-NODATE` | No evidenced sale date | Blocked: sale date unknown |
| `SYN-TX-NORIGHTS` | Commercial-modelling right unestablished | Blocked: rights not established |
| `SYN-TX-SECONDARY` | Secondary publisher without upstream rights | Blocked: upstream rights unconfirmed |
| `SYN-TX-HOLDOUT` | Otherwise cleared record marked holdout, including publication grants | Stored only under `holdout/`. Export denied. |
| `SYN-TX-PUBLIC` | Explicit redistribution and publication grants | The only approved individual export |
| `SYN-TX-MALFORMED` and a non-object | Broken envelopes | Counted and skipped |

## Before the first 50 real transactions

1. Confirm disk encryption and an encrypted backup that is not a cloud-sync folder. This tool does not verify either.
2. Keep real-data import disabled until each rights reference is bound to a document in `licences/` and that binding is separately approved. A JSON reference is not that binding.
3. Do not scrape a marketplace and do not send vault files to a hosted service.
4. Read `evaluation/quality-report.md` and `export/manifest.json`. Do not copy `export/approved/` into the repository unless a later, explicit authorisation names those files.
5. Leave calibration admission closed and do not run an independent holdout evaluation.
