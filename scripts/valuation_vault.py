#!/usr/bin/env python3
"""Local private valuation vault.

Stores comparable-sale research outside the public Git working tree and
reuses the Sprint 1B pipeline in scripts/sales_pipeline.py. This module does
not admit calibration batches, does not evaluate the holdout, and does not
publish anything.

The vault root is the environment variable SOHADOT_PRIVATE_ROOT. It must be
a directory outside every Git working tree. Nothing in this module reads or
writes js/valuation-engine.js, data/valuation_comps.json, or the public
holdout status file.

Usage:
    python scripts/valuation_vault.py layout
    python scripts/valuation_vault.py import --file PATH
    python scripts/valuation_vault.py report
    python scripts/valuation_vault.py export
    python scripts/valuation_vault.py demo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sales_pipeline as sp  # noqa: E402

ENV_ROOT = "SOHADOT_PRIVATE_ROOT"
STAGES = (
    "sources", "licences", "raw-sales", "verified-sales", "calibration",
    "holdout", "evaluation", "export", "audit", "config",
)
PARTITIONS = {"calibration", "holdout"}
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")
REASON_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
SECRET_MARKERS = ("api_key", "api-key", "password", "private_key", "begin private key", "aws_secret_access_key")
RESERVED_WINDOWS_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{n}" for n in range(1, 10)),
    *(f"LPT{n}" for n in range(1, 10)),
}
# A JSON reference is not evidence that a licence file authorises the record.
# Real imports stay disabled until that binding exists and is separately approved.
REAL_IMPORT_PERMITTED = False
TRANSACTION_STAGES = ("raw-sales", "verified-sales", "calibration", "holdout", "evaluation/rejected")
PIPELINE_KEYS = (
    "price_type", "sale_date_basis", "original_amount", "original_currency",
    "amount_usd", "fx_basis", "rights_provenance", "duplicate_of",
)
RECORD_KEYS = (
    "transaction_id", "domain", "sale_price", "currency", "price_scope",
    "transaction_type", "consideration_type", "price_disclosure_status",
    "evidence_status", "sale_date", "sale_date_precision", "rights", "pipeline",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _inside_git(path: Path) -> Path | None:
    for parent in (path, *path.resolve().parents):
        if (parent / ".git").exists():
            return parent
    return None


def _reparse_point(path: Path) -> bool:
    """True for a symbolic link, junction, or other Windows reparse point."""
    if not path.exists() and not path.is_symlink():
        return False
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True
    if os.name != "nt":
        return False
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    try:
        attrs = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return True
    return bool(attrs & flag)


def _reject_reparse_chain(path: Path) -> None:
    current = path
    while True:
        if _reparse_point(current):
            raise SystemExit(f"Refusing reparse point: {current}")
        parent = current.parent
        if parent == current:
            break
        current = parent


def require_inside(root: Path, target: Path) -> Path:
    """Resolve target and refuse links, junctions, and paths outside root or inside Git."""
    root_resolved = Path(root).resolve()
    _reject_reparse_chain(target if target.exists() or target.is_symlink() else target.parent)
    resolved = target.resolve()
    _reject_reparse_chain(resolved)
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise SystemExit(f"Refusing path outside the vault: {resolved}")
    git_parent = _inside_git(resolved)
    if git_parent is not None:
        raise SystemExit(f"Refusing path inside a Git working tree ({git_parent}): {resolved}")
    return resolved


def vault_root(explicit: str | None = None) -> Path:
    raw = explicit or os.environ.get(ENV_ROOT)
    if not raw:
        raise SystemExit(
            f"{ENV_ROOT} is not set. The vault is not created inside the repository. "
            "See docs/valuation-evidence/PRIVATE_VALUATION_VAULT.md."
        )
    raw_path = Path(raw).expanduser()
    _reject_reparse_chain(raw_path if raw_path.exists() or raw_path.is_symlink() else raw_path.parent)
    root = raw_path.resolve()
    repo = sp.REPO_ROOT.resolve()
    if root == repo or repo in root.parents:
        raise SystemExit(f"Refusing vault inside the Git working tree: {root}")
    git_parent = _inside_git(root)
    if git_parent is not None:
        raise SystemExit(f"Refusing vault inside a Git working tree ({git_parent}): {root}")
    return root


def ensure_layout(root: Path) -> None:
    root = Path(root).resolve()
    _reject_reparse_chain(root)
    git_parent = _inside_git(root)
    if git_parent is not None:
        raise SystemExit(f"Refusing vault inside a Git working tree ({git_parent}): {root}")
    root.mkdir(parents=True, exist_ok=True)
    for name in STAGES:
        dest = root / name
        if dest.exists() or dest.is_symlink():
            require_inside(root, dest)
        else:
            require_inside(root, dest.parent)
            dest.mkdir()
    (root / "export" / "approved").mkdir(parents=True, exist_ok=True)
    (root / "evaluation" / "rejected").mkdir(parents=True, exist_ok=True)
    notice = root / "calibration" / "ADMISSION_CLOSED.txt"
    if not notice.exists():
        notice.write_text(
            "Calibration admission is closed (sales_pipeline.ADMISSION_OPEN is False).\n"
            "Files here are eligible candidates only. They are not an admitted batch\n"
            "and they are not production valuation inputs.\n",
            encoding="utf-8",
        )
    reviewed = root / "verified-sales" / "README.txt"
    if not reviewed.exists():
        reviewed.write_text(
            "Reviewed records. The pipeline state inside each file is authoritative.\n"
            "SOURCE_REVIEWED is not eligible and is not an admitted calibration record.\n",
            encoding="utf-8",
        )
    holdout_note = root / "holdout" / "README.txt"
    if not holdout_note.exists():
        holdout_note.write_text(
            "Private holdout partition. Storing a record here is not a holdout evaluation\n"
            "and does not change the public holdout status file.\n",
            encoding="utf-8",
        )
    security = root / "config" / "SECURITY.md"
    if not security.exists():
        security.write_text(_security_text(root), encoding="utf-8")
    config = root / "config" / "vault.json"
    if not config.exists():
        config.write_text(json.dumps({
            "private_root_env": ENV_ROOT,
            "git_initialized": False,
            "cloud_sync": "disabled",
            "created_at": _now(),
            "encryption": "not confirmed by this tool; enable disk encryption before real records",
        }, indent=2) + "\n", encoding="utf-8")


def _security_text(root: Path) -> str:
    return f"""# Private valuation vault

Path: {root}

This directory is local processing storage. Creating it does not encrypt the disk
and does not create a backup.

Before any real transaction record is imported:

1. Confirm the volume uses device encryption (BitLocker or an equivalent full-disk
   encryption product). A folder sitting on an unencrypted disk is not protected.
2. Keep backups on an encrypted volume or in an encrypted archive. Do not place
   this directory in OneDrive, Dropbox, Google Drive, iCloud, or any other
   automatic cloud-sync folder.
3. Do not initialise Git here. Do not commit, push, or upload these files.
4. Do not store passwords, API keys, or encryption passphrases in this directory
   or in the Sohadot source tree.
5. Licence documents belong in licences/. They are never an export source.
6. Holdout records belong in holdout/. Storing them here does not authorise
   holdout evaluation and does not open calibration admission.

This file is a requirement, not evidence that encryption or a backup exists.
"""


def _audit(root: Path, event: dict) -> None:
    """Append an event that identifies a record without copying its contents."""
    reasons = [
        item for item in (event.get("reasons") or [])
        if isinstance(item, str) and REASON_CODE.fullmatch(item)
    ]
    safe = {
        "at": _now(),
        "event": event.get("event") if isinstance(event.get("event"), str) else None,
        "transaction_id": _safe_id(event.get("transaction_id")),
        "outcome": event.get("outcome") if isinstance(event.get("outcome"), str) else None,
        "state": event.get("state") if isinstance(event.get("state"), str) else None,
        "partition": event.get("partition") if event.get("partition") in PARTITIONS or event.get("partition") is None else None,
        "reasons": reasons,
    }
    path = root / "audit" / "events.jsonl"
    require_inside(root, path if path.exists() or path.is_symlink() else path.parent)
    if path.exists() and _reparse_point(path):
        raise SystemExit(f"Refusing reparse point: {path}")
    line = json.dumps(safe, ensure_ascii=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _link_count(path: Path) -> int:
    try:
        return path.stat().st_nlink
    except OSError as exc:
        raise SystemExit(f"Refusing unreadable vault path: {path}") from exc


def _create_private_temp(temporary: Path) -> int:
    """Create a new file at this path. Do not follow a link or share an outside inode."""
    if temporary.exists() or temporary.is_symlink():
        if _reparse_point(temporary):
            raise SystemExit(f"Refusing reparse point: {temporary}")
        if _link_count(temporary) > 1:
            raise SystemExit(f"Refusing hard link: {temporary}")
        temporary.unlink()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow:
        flags |= nofollow
    try:
        return os.open(temporary, flags, 0o600)
    except OSError as exc:
        raise SystemExit(f"Refusing unsafe temporary file: {temporary}") from exc


def _write_json(root: Path, path: Path, payload, *, exclusive: bool = False) -> None:
    """Write JSON inside the vault. exclusive refuses to replace an existing file."""
    parent = path.parent
    require_inside(root, path if path.exists() or path.is_symlink() else parent)
    if path.exists() or path.is_symlink():
        if _reparse_point(path):
            raise SystemExit(f"Refusing reparse point: {path}")
        if _link_count(path) > 1:
            raise SystemExit(f"Refusing hard link: {path}")
        if exclusive:
            raise SystemExit(f"Refusing to overwrite {path.name}")
    parent.mkdir(parents=True, exist_ok=True)
    require_inside(root, parent)
    temporary = path.with_name(f".{path.name}.partial")
    data = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    fd = None
    try:
        fd = _create_private_temp(temporary)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = None
            handle.write(data)
        if exclusive and (path.exists() or path.is_symlink()):
            raise SystemExit(f"Refusing to overwrite {path.name}")
        if (path.exists() or path.is_symlink()) and (_reparse_point(path) or _link_count(path) > 1):
            raise SystemExit(f"Refusing unsafe destination: {path}")
        os.replace(temporary, path)
    finally:
        if fd is not None:
            os.close(fd)
        if not _reparse_point(temporary) and temporary.exists() and _link_count(temporary) == 1:
            temporary.unlink()


def _structural_errors(record: dict) -> list[str]:
    errors = []
    if not isinstance(record, dict):
        return ["record is not an object"]
    for key in RECORD_KEYS:
        if key not in record:
            errors.append(f"missing {key}")
    pipeline = record.get("pipeline")
    if not isinstance(pipeline, dict):
        errors.append("pipeline block is missing")
        return errors
    for key in PIPELINE_KEYS:
        if key not in pipeline:
            errors.append(f"pipeline.{key} is missing")
    rights = record.get("rights")
    if not isinstance(rights, dict):
        errors.append("rights block is missing")
    return errors


def load_import(path: Path) -> tuple[dict, list[dict]]:
    """Return (header, envelopes). Malformed items stay in the list and are
    rejected later so one bad record does not abort the batch."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Import file cannot be read as JSON: {exc.__class__.__name__}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise SystemExit("Import file must be an object with a records array.")
    header = {
        "synthetic": payload.get("synthetic") is True,
        "dataset_label": payload.get("dataset_label") or "",
        "source_name": path.name,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    envelopes = []
    for index, item in enumerate(payload["records"], start=1):
        if not isinstance(item, dict):
            envelopes.append({"partition": None, "record": item, "index": index, "malformed": True})
            continue
        envelopes.append({
            "partition": item.get("partition"),
            "record": item.get("record"),
            "index": index,
            "malformed": False,
        })
    return header, envelopes


def _stage_for(partition: str, state: str) -> str:
    if partition == "holdout":
        return "holdout"
    if state == "REJECTED":
        return "evaluation/rejected"
    if state == "ELIGIBLE":
        return "calibration"
    return "verified-sales"


def _explicit_grant(entry) -> bool:
    """A grant counts only when status, basis and reference are all present.
    Modelling permission does not satisfy this check."""
    if not isinstance(entry, dict):
        return False
    status = entry.get("status")
    basis_type = entry.get("basis_type")
    basis = entry.get("basis") or ""
    reference = entry.get("reference")
    if status not in sp.reg.GRANTED:
        return False
    if basis_type in (None, "NONE") or len(str(basis).strip()) < 20:
        return False
    if basis_type in sp.reg.RIGHTS_NEEDS_REFERENCE and not reference:
        return False
    return True


def _safe_id(value) -> str | None:
    text = str(value or "")
    if not SAFE_ID.fullmatch(text) or text in (".", ".."):
        return None
    if text.split(".", 1)[0].upper() in RESERVED_WINDOWS_NAMES:
        return None
    return text


def _contains_secret(record: dict) -> bool:
    blob = json.dumps(record, ensure_ascii=True).lower()
    return any(marker in blob for marker in SECRET_MARKERS)


def _rights_errors(record: dict) -> list[str]:
    """Registry rights check. A status string without basis and reference fails."""
    errors: list[str] = []
    sp.reg.check_rights(record.get("rights"), _safe_id(record.get("transaction_id")) or "record", errors)
    return errors


def _downgrade_invalid_rights(record: dict) -> bool:
    if not _rights_errors(record):
        return False
    pipeline = record["pipeline"]
    if pipeline.get("state") == "ELIGIBLE":
        pipeline["state"] = "SOURCE_REVIEWED"
        blockers = list(pipeline.get("blockers") or [])
        if "RIGHTS_NOT_ESTABLISHED" not in blockers:
            blockers.append("RIGHTS_NOT_ESTABLISHED")
        pipeline["blockers"] = sorted(blockers)
    return True


def _redistribution_authorized(rights) -> bool:
    """Individual redistribution needs the registry check and a complete grant.
    Storage or modelling rights do not satisfy it."""
    if _rights_errors({"transaction_id": "export", "rights": rights}):
        return False
    if not isinstance(rights, dict):
        return False
    return _explicit_grant(rights.get("redistribution"))


def _can_assess(record: dict) -> bool:
    rights = record.get("rights")
    if not isinstance(rights, dict):
        return False
    for key in sp.reg.RIGHTS_KEYS:
        entry = rights.get(key)
        if not isinstance(entry, dict) or "status" not in entry:
            return False
    try:
        sp.assess(record)
    except Exception:
        return False
    return True


def _holdout_side(record: dict, partition: str | None = None) -> bool:
    part = partition if partition is not None else (record.get("vault") or {}).get("partition")
    return part == "holdout" or record.get("calibration_role") == "HOLDOUT_CANDIDATE"


def _policy_block(record: dict, partition: str, counterparts: list[dict]) -> str | None:
    """Refuse a same-domain pair that would put one side in calibration and the other in holdout.

    The check runs for both import directions. A holdout partition is not exempt.
    """
    if record.get("calibration_role") == "HOLDOUT_CANDIDATE" and partition != "holdout":
        return "HOLDOUT_CANDIDATE"
    if not counterparts:
        return None
    try:
        related = sp.find_relationships([*counterparts, record])
    except Exception:
        return "HOLDOUT_OVERLAP"
    tid = record.get("transaction_id")
    if any(tid in (left, right) for left, right, _kind in related):
        return "HOLDOUT_OVERLAP"
    return None


def export_decision(record: dict, partition: str) -> dict:
    """Default deny. Storage or modelling rights never authorise publication."""
    pipeline = record.get("pipeline") or {}
    rights = record.get("rights") if isinstance(record.get("rights"), dict) else {}
    reasons = []
    holdout = partition == "holdout" or record.get("calibration_role") == "HOLDOUT_CANDIDATE"
    if holdout:
        reasons.append("HOLDOUT_PARTITION")
    if pipeline.get("state") != "ELIGIBLE":
        reasons.append("NOT_ELIGIBLE")
    if pipeline.get("state") in ("CALIBRATION_ADMITTED", "HOLDOUT_RESERVED"):
        reasons.append("CLOSED_OR_UNAUTHORIZED_STATE")
    if _rights_errors(record):
        reasons.append("RIGHTS_INVALID")
    if not _redistribution_authorized(rights):
        reasons.append("REDISTRIBUTION_NOT_GRANTED")
    if not sp.upstream_rights_ok(pipeline.get("rights_provenance")):
        reasons.append("UPSTREAM_RIGHTS_NOT_CONFIRMED")
    secret = _contains_secret(record)
    if secret:
        reasons.append("SECRET_MATERIAL")
    publication = pipeline.get("publication_authorization")
    derived = aggregate = False
    if not isinstance(publication, dict):
        reasons.append("PUBLICATION_RIGHTS_MISSING")
    else:
        derived = _explicit_grant(publication.get("serve_derived_valuations_publicly"))
        aggregate = _explicit_grant(publication.get("disclose_aggregate_statistics"))
        if not derived:
            reasons.append("DERIVED_PUBLICATION_NOT_GRANTED")
        if not aggregate:
            reasons.append("AGGREGATE_DISCLOSURE_NOT_GRANTED")
    record_export = not any(reason in reasons for reason in (
        "HOLDOUT_PARTITION", "NOT_ELIGIBLE", "CLOSED_OR_UNAUTHORIZED_STATE",
        "RIGHTS_INVALID", "REDISTRIBUTION_NOT_GRANTED", "UPSTREAM_RIGHTS_NOT_CONFIRMED",
        "SECRET_MATERIAL",
    ))
    # Derived publication and aggregate disclosure stay separate from redistribution.
    # An ineligible, blocked, rights-invalid, or upstream-uncleared record cannot
    # receive either publication approval, even when that grant is present.
    publication_blocked = (
        holdout or secret or pipeline.get("state") != "ELIGIBLE"
        or "RIGHTS_INVALID" in reasons or "UPSTREAM_RIGHTS_NOT_CONFIRMED" in reasons
    )
    derived_ok = derived and not publication_blocked
    aggregate_ok = aggregate and not publication_blocked
    return {
        "transaction_id": _safe_id(record.get("transaction_id")),
        "partition": partition,
        "state": pipeline.get("state"),
        "record_export": "ALLOW" if record_export else "DENY",
        "derived_valuation_publication": "ALLOW" if derived_ok else "DENY",
        "aggregate_disclosure": "ALLOW" if aggregate_ok else "DENY",
        "reasons": reasons,
        "rights_status": {
            key: (rights.get(key) or {}).get("status") if isinstance(rights.get(key), dict) else None
            for key in ("storage", "commercial_modelling", "redistribution")
        },
    }


def _existing_ids(root: Path) -> set[str]:
    found = set()
    if not root.exists():
        return found
    for stage in TRANSACTION_STAGES:
        directory = root / stage
        if not directory.exists():
            continue
        require_inside(root, directory)
        for path in directory.glob("*.json"):
            if not path.is_file() or path.is_symlink() or _reparse_point(path):
                raise SystemExit(f"Refusing reparse point: {path}")
            tid = _safe_id(path.stem)
            if tid:
                found.add(tid)
    return found


def _reject(root: Path, rejected: list[dict], index, tid, reasons: list[str], audit_reason: str) -> None:
    rejected.append({"index": index, "transaction_id": _safe_id(tid), "reasons": reasons})
    _audit(root, {
        "event": "import",
        "transaction_id": _safe_id(tid),
        "outcome": "rejected",
        "reasons": [audit_reason],
    })


def import_batch(root: Path, path: Path, *, require_synthetic: bool = False) -> dict:
    header, envelopes = load_import(path)
    if require_synthetic and not header["synthetic"]:
        raise SystemExit("Demo import refused: dataset is not marked synthetic.")
    if header["synthetic"] and "SYNTHETIC" not in header["dataset_label"].upper():
        raise SystemExit("Synthetic dataset_label must say SYNTHETIC.")
    # synthetic is a self-declared file label, not proof the bytes are synthetic.
    # REAL_IMPORT_PERMITTED stays False until licence-document binding is approved.
    if not header["synthetic"]:
        raise SystemExit(
            "Real-data import is disabled. A JSON reference is not a licence, "
            "and binding each rights reference to a document in licences/ is not implemented."
        )
    root = Path(root).resolve()
    ensure_layout(root)
    _write_json(root, root / "sources" / f"{header['source_sha256'][:16]}.json", {
        "sha256": header["source_sha256"],
        "file_name": header["source_name"],
        "synthetic": header["synthetic"],
        "imported_at": _now(),
        "real_import_permitted": REAL_IMPORT_PERMITTED,
    })

    rejected: list[dict] = []
    accepted = []
    accepted_partitions = []
    existing_ids = _existing_ids(root)
    seen = set(existing_ids)
    for envelope in envelopes:
        record = envelope["record"]
        partition = envelope["partition"]
        index = envelope["index"]
        if envelope["malformed"] or not isinstance(record, dict):
            _reject(root, rejected, index, None, ["malformed record"], "MALFORMED")
            continue
        errors = _structural_errors(record)
        if partition not in PARTITIONS:
            errors.append("partition must be calibration or holdout")
        tid = _safe_id(record.get("transaction_id"))
        if tid is None:
            errors.append("transaction_id is missing or unsafe")
        if errors:
            _reject(root, rejected, index, tid, errors, "STRUCTURAL" if tid else "UNSAFE_ID")
            continue
        if tid in seen:
            _reject(root, rejected, index, tid, ["existing transaction cannot be overwritten"], "OVERWRITE_REFUSED")
            continue
        if not _can_assess(record):
            _reject(root, rejected, index, tid, ["record cannot be assessed"], "ASSESSMENT_FAILED")
            continue
        seen.add(tid)
        accepted.append(record)
        accepted_partitions.append(partition)

    existing = collect_stored(root) if root.exists() else []
    stored_holdout = [item for item in existing if _holdout_side(item)]
    stored_other = [item for item in existing if not _holdout_side(item)]
    incoming_holdout = [
        record for record, partition in zip(accepted, accepted_partitions)
        if _holdout_side(record, partition)
    ]
    incoming_other = [
        record for record, partition in zip(accepted, accepted_partitions)
        if not _holdout_side(record, partition)
    ]
    kept_records = []
    kept_partitions = []
    for record, partition in zip(accepted, accepted_partitions):
        if _holdout_side(record, partition):
            counterparts = [*stored_other, *incoming_other]
        else:
            counterparts = [*stored_holdout, *incoming_holdout]
        block = _policy_block(record, partition, counterparts)
        if block:
            _reject(root, rejected, None, record.get("transaction_id"), [block], block)
            continue
        kept_records.append(record)
        kept_partitions.append(partition)

    assessed_by_id = {}
    if kept_records:
        try:
            assessed = sp.assess_all(existing + kept_records)
        except Exception:
            _audit(root, {"event": "import", "transaction_id": None, "outcome": "rejected", "reasons": ["ASSESSMENT_FAILED"]})
            raise SystemExit("Assessment failed before any new transaction file was written.")
        assessed_by_id = {_safe_id(item.get("transaction_id")): item for item in assessed}

    planned = []
    for record, partition in zip(kept_records, kept_partitions):
        tid = _safe_id(record.get("transaction_id"))
        assessed_record = assessed_by_id.get(tid)
        if not isinstance(assessed_record, dict):
            _reject(root, rejected, None, tid, ["record cannot be assessed"], "ASSESSMENT_FAILED")
            continue
        assessed_record = json.loads(json.dumps(assessed_record))
        state = assessed_record["pipeline"]["state"]
        if state in ("CALIBRATION_ADMITTED", "HOLDOUT_RESERVED") or sp.ADMISSION_OPEN:
            raise SystemExit("Refusing to store a closed or unauthorized pipeline state.")
        _downgrade_invalid_rights(assessed_record)
        state = assessed_record["pipeline"]["state"]
        assessed_record["vault"] = {
            "partition": partition,
            "synthetic": True,
            "assessed_at": _now(),
            "admission": "CLOSED",
            "holdout_evaluation": "UNAUTHORIZED",
            "rights_registry_valid": not _rights_errors(assessed_record),
        }
        planned.append((tid, partition, state, assessed_record))

    stored = []
    for tid, partition, state, assessed_record in planned:
        raw_copy = json.loads(json.dumps(assessed_record))
        _write_json(root, root / "raw-sales" / f"{tid}.json", raw_copy, exclusive=True)
        _write_json(root, root / _stage_for(partition, state) / f"{tid}.json", assessed_record, exclusive=True)
        if partition != "holdout" and state == "ELIGIBLE":
            _write_json(root, root / "verified-sales" / f"{tid}.json", assessed_record, exclusive=True)
        stored.append(assessed_record)
        blockers = assessed_record["pipeline"]["rejection_reasons"] or assessed_record["pipeline"]["blockers"]
        _audit(root, {
            "event": "import",
            "transaction_id": tid,
            "outcome": "stored",
            "state": state,
            "partition": partition,
            "reasons": blockers,
        })

    summary = {
        "imported_envelopes": len(envelopes),
        "stored": len(stored),
        "structurally_rejected": len(rejected),
        "synthetic": True,
        "real_import_permitted": REAL_IMPORT_PERMITTED,
    }
    _write_json(root, root / "evaluation" / "last-import.json", {"summary": summary, "rejected": rejected})
    complete = collect_stored(root)
    write_report(root, complete, rejected, all((item.get("vault") or {}).get("synthetic") is True for item in complete))
    return summary


def collect_stored(root: Path) -> list[dict]:
    """One record per id. A holdout copy wins, then calibration, then the rest."""
    chosen = {}
    rank = {"holdout": 3, "calibration": 2, "evaluation/rejected": 1, "verified-sales": 0}
    for stage in ("verified-sales", "evaluation/rejected", "calibration", "holdout"):
        for record in _load_stage(root, stage):
            tid = record.get("transaction_id")
            partition = (record.get("vault") or {}).get("partition") or stage
            current = chosen.get(tid)
            if current is None or rank.get(partition, 0) >= rank.get(current[0], 0):
                chosen[tid] = (partition, record)
    return [item[1] for _, item in sorted(chosen.items(), key=lambda pair: str(pair[0]))]


def _load_stage(root: Path, stage: str) -> list[dict]:
    directory = root / stage
    if not directory.exists():
        return []
    require_inside(root, directory)
    records = []
    for path in sorted(directory.glob("*.json")):
        if path.is_symlink() or _reparse_point(path):
            raise SystemExit(f"Refusing reparse point: {path}")
        require_inside(root, path)
        if _link_count(path) > 1:
            raise SystemExit(f"Refusing hard link: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and "transaction_id" in payload:
            records.append(payload)
    return records


def write_report(root: Path, stored: list[dict], rejected: list[dict], synthetic: bool) -> dict:
    unresolved = set(sp.unresolved_duplicates(stored)) if stored else set()
    eligible = [
        r for r in stored
        if r["pipeline"]["state"] == "ELIGIBLE"
        and r["vault"]["partition"] != "holdout"
        and r.get("calibration_role") != "HOLDOUT_CANDIDATE"
        and r["transaction_id"] not in unresolved
    ]
    holdout = [
        r for r in stored
        if r["vault"]["partition"] == "holdout" or r.get("calibration_role") == "HOLDOUT_CANDIDATE"
    ]
    calibration_ids = {r["transaction_id"] for r in eligible}
    holdout_ids = {r["transaction_id"] for r in holdout}
    reviewed = [r for r in stored if r.get("evidence_status") in ("VERIFIED", "REPORTED", "DISPUTED")]
    rejected_state = [r for r in stored if r["pipeline"]["state"] == "REJECTED"]
    bands = {}
    for record in stored:
        band = sp.price_band((record.get("pipeline") or {}).get("amount_usd"))
        bands[band] = bands.get(band, 0) + 1
    relationships = [
        {"left": left, "right": right, "kind": kind}
        for left, right, kind in sp.find_relationships(stored)
    ]
    report = {
        "generated_at": _now(),
        "synthetic": synthetic,
        "admission_open": sp.ADMISSION_OPEN,
        "holdout_evaluation": "UNAUTHORIZED",
        "imported_records": len(stored) + len(rejected),
        "stored_records": len(stored),
        "structurally_rejected": len(rejected),
        "reviewed_transactions": len(reviewed),
        "eligible_transactions": len(eligible),
        "rejected_transactions": len(rejected_state),
        "missing_completion_evidence": sum(1 for r in stored if "COMPLETION_NOT_EVIDENCED" in r["pipeline"]["blockers"]),
        "missing_sale_date": sum(1 for r in stored if "SALE_DATE_UNKNOWN" in r["pipeline"]["blockers"]),
        "missing_rights": sum(1 for r in stored if "RIGHTS_NOT_ESTABLISHED" in r["pipeline"]["blockers"] or "UPSTREAM_RIGHTS_UNCONFIRMED" in r["pipeline"]["blockers"]),
        "duplicate_relationships": relationships,
        "price_band_distribution": bands,
        "source_concentration": sp.independence_summary([r for r in stored if r["vault"]["partition"] != "holdout"]),
        "holdout_separation": {
            "holdout_count": len(holdout_ids),
            "calibration_count": len(calibration_ids),
            "overlap": sorted(calibration_ids & holdout_ids),
        },
        "unresolved_relationship_ids": sorted(unresolved),
        "blocker_glossary": sp.BLOCKERS,
        "rejection_glossary": sp.REJECTION_REASONS,
    }
    _write_json(root, root / "evaluation" / "quality-report.json", report)
    lines = [
        "# Local valuation quality report",
        "",
        "Private vault report. This file is not a publication.",
        f"Synthetic dataset: {synthetic}. The synthetic flag repeats a self-declared label; it is not cryptographic proof that the records are synthetic. Calibration admission: closed. Holdout evaluation: unauthorized.",
        "",
        f"- Imported records: {report['imported_records']}",
        f"- Reviewed transactions: {report['reviewed_transactions']}",
        f"- Eligible transactions: {report['eligible_transactions']}",
        f"- Rejected transactions: {report['rejected_transactions']}",
        f"- Structurally rejected: {report['structurally_rejected']}",
        f"- Missing completion evidence: {report['missing_completion_evidence']}",
        f"- Missing sale date: {report['missing_sale_date']}",
        f"- Missing or unconfirmed rights: {report['missing_rights']}",
        f"- Holdout records kept apart: {report['holdout_separation']['holdout_count']}",
        f"- Holdout/calibration overlap: {report['holdout_separation']['overlap'] or 'none'}",
        "",
        "## Price bands",
        "",
    ]
    for band, count in sorted(bands.items()):
        lines.append(f"- {band}: {count}")
    lines.extend(["", "## Duplicate and repeat-sale relationships", ""])
    if relationships:
        for item in relationships:
            lines.append(f"- {item['kind']}: {item['left']} / {item['right']}")
    else:
        lines.append("- none")
    concentration = report["source_concentration"]
    lines.extend([
        "",
        "## Source concentration",
        "",
        f"- Priced reviewed records outside the holdout partition: {concentration['records']}",
        f"- Largest source-family share: {concentration['max_family_share']}",
        f"- Largest relay share: {concentration['max_relay_share']}",
        "",
        "## Stored record outcomes",
        "",
    ])
    for record in stored:
        pipeline = record["pipeline"]
        codes = pipeline["rejection_reasons"] or pipeline["blockers"] or []
        phrases = []
        for code in codes:
            text = sp.REJECTION_REASONS.get(code) or sp.BLOCKERS.get(code) or code
            phrases.append(f"{code}: {text}")
        detail = "; ".join(phrases) if phrases else "none"
        lines.append(
            f"- {record['transaction_id']}: {pipeline['state']} "
            f"({record['vault']['partition']}); {detail}"
        )
    if rejected:
        lines.extend(["", "## Structural rejections", ""])
        for item in rejected:
            lines.append(f"- index {item['index']}: {', '.join(item['reasons'])}")
    report_md = root / "evaluation" / "quality-report.md"
    require_inside(root, report_md.parent)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _publication_relationship_denials(stored: list[dict]) -> dict[str, list[str]]:
    """Recalculate cross-record exclusions. Stored pipeline state is not enough."""
    reasons: dict[str, list[str]] = {}

    def add(tid, code: str) -> None:
        if isinstance(tid, str) and tid:
            bucket = reasons.setdefault(tid, [])
            if code not in bucket:
                bucket.append(code)

    if not stored:
        return reasons
    try:
        unresolved = sp.unresolved_duplicates(stored)
        holdout = [item for item in stored if _holdout_side(item)]
        other = [item for item in stored if not _holdout_side(item)]
        related = sp.find_relationships(holdout + other) if holdout and other else []
    except Exception:
        for item in stored:
            add(item.get("transaction_id"), "DUPLICATE_UNRESOLVED")
        return reasons
    for tid in unresolved:
        add(tid, "DUPLICATE_UNRESOLVED")
    holdout_ids = {item.get("transaction_id") for item in holdout}
    for left, right, _kind in related:
        if (left in holdout_ids) != (right in holdout_ids):
            add(left, "HOLDOUT_OVERLAP")
            add(right, "HOLDOUT_OVERLAP")
    return reasons


def export_approved(root: Path) -> dict:
    """Write a manifest and, only where rights allow, a copy under export/approved.

    Holdout, raw sales, licences, and records without an explicit redistribution
    grant are never copied. This command does not touch the Git repository.
    """
    ensure_layout(root)
    approved_dir = root / "export" / "approved"
    require_inside(root, approved_dir)
    candidates = collect_stored(root)
    # One decision per id. Prefer the calibration or holdout copy over a duplicate verified copy.
    chosen = {}
    for record in candidates:
        tid = record.get("transaction_id")
        current = chosen.get(tid)
        partition = (record.get("vault") or {}).get("partition")
        if current is None or partition == "holdout" or (current[0] != "holdout" and partition == "calibration"):
            chosen[tid] = (partition, record)
    decisions = []
    approved_ids = []
    aggregate_ids = []
    relationship_denials = _publication_relationship_denials(candidates)
    for tid, (partition, record) in sorted(chosen.items()):
        decision = export_decision(record, partition or "")
        extra = relationship_denials.get(tid) or []
        if extra:
            decision["record_export"] = "DENY"
            decision["derived_valuation_publication"] = "DENY"
            decision["aggregate_disclosure"] = "DENY"
            for code in extra:
                if code not in decision["reasons"]:
                    decision["reasons"].append(code)
        decisions.append(decision)
        _audit(root, {
            "event": "export",
            "transaction_id": tid,
            "outcome": decision["record_export"],
            "state": decision["state"],
            "partition": partition,
            "reasons": decision["reasons"],
        })
        safe_tid = _safe_id(tid)
        if decision["record_export"] == "ALLOW" and partition != "holdout" and safe_tid and record.get("calibration_role") != "HOLDOUT_CANDIDATE":
            _write_json(root, approved_dir / f"{safe_tid}.json", record)
            approved_ids.append(safe_tid)
        if decision["aggregate_disclosure"] == "ALLOW" and safe_tid:
            aggregate_ids.append(safe_tid)
    for stale in approved_dir.glob("*.json"):
        if stale.stem not in approved_ids:
            require_inside(root, stale)
            if not _reparse_point(stale):
                stale.unlink()
    aggregate_path = root / "export" / "approved-aggregates.json"
    if aggregate_ids:
        _write_json(root, aggregate_path, {
            "synthetic_notice": "Counts only. Individual records are not included.",
            "transaction_ids": aggregate_ids,
            "count": len(aggregate_ids),
            "rights_basis": "disclose_aggregate_statistics explicitly granted on each included record",
        })
    elif aggregate_path.exists():
        aggregate_path.unlink()
    manifest = {
        "generated_at": _now(),
        "published": False,
        "publication_note": "This manifest stays in the private vault. It does not copy files into the public repository.",
        "admission_open": sp.ADMISSION_OPEN,
        "decisions": decisions,
        "approved_record_ids": approved_ids,
        "aggregate_record_ids": aggregate_ids,
        "blocked_locations": ["licences", "raw-sales", "holdout", "sources"],
    }
    _write_json(root, root / "export" / "manifest.json", manifest)
    return manifest


def build_synthetic_import() -> dict:
    """Synthetic cases for the local demonstration. None of these are sales."""

    def right(status, basis_type, basis, reference):
        return {"status": status, "basis_type": basis_type, "basis": basis, "reference": reference}

    granted = right(
        "PERMITTED_WITH_CONDITIONS", "WRITTEN_PERMISSION",
        "SYNTHETIC fixture: venue permission for storage and internal modelling only.",
        "SYN-PERM-STORAGE",
    )
    absent = right(
        "NOT_ESTABLISHED", "NONE",
        "SYNTHETIC fixture: this right was deliberately left unestablished.",
        None,
    )
    public_grant = right(
        "PERMITTED", "WRITTEN_PERMISSION",
        "SYNTHETIC fixture: explicit permission for this named public use only.",
        "SYN-PERM-PUBLIC",
    )

    def base(tid, domain, amount, **over):
        record = {
            "transaction_id": tid, "domain": domain, "sale_price": amount, "currency": "USD",
            "price_scope": "SINGLE_DOMAIN", "bundle": None, "sale_date": "2024-06-01",
            "sale_date_precision": "DAY", "report_date": "2024-06-02", "venue": "MARKETPLACE",
            "transaction_type": "DOMAIN_ONLY", "consideration_type": "CASH",
            "market_side": "INVESTOR_TRADE", "source_name": "Synthetic Venue Ledger",
            "source_url": f"https://synthetic.example/ledger/{tid}",
            "source_type": "MARKETPLACE_RECORD", "source_access_method": "DOCUMENT_REVIEWED",
            "source_accessed_at": "2026-10-23", "review_method": "RAW_TEXT_CHECKED",
            "document_locator": "Synthetic ledger row 1",
            "checked_quote": "SYNTHETIC NOT A REAL SALE",
            "document_sha256": "0" * 64, "additional_sources": [], "leads": [],
            "price_disclosure_status": "EXACT", "price_claims": [], "conflicts": [],
            "valuation_caveats": ["SYNTHETIC — not a real sale"],
            "evidence_status": "VERIFIED", "verification_basis": "Synthetic fixture",
            "verified_at": "2026-10-23", "attesting_party": "VENUE",
            "settlement_evidence": "PARTY_ATTESTATION_ONLY",
            "rights": {
                "citation": dict(granted), "storage": dict(granted),
                "commercial_modelling": dict(granted), "redistribution": dict(absent),
            },
            "calibration_role": "UNDETERMINED",
            "notes": "SYNTHETIC — not a real sale",
        }
        record = sp.pipeline_from_registry(record)
        record["pipeline"].update(
            price_type="COMPLETED_SALE",
            completion_evidence={
                "basis": "VENUE_RECORD_OF_COMPLETION",
                "locator": "Synthetic ledger row 1",
                "quote": "SYNTHETIC sale marked paid",
            },
            sale_date_basis="EXPLICIT_IN_SOURCE",
            source_family="Synthetic Venue",
            relay_publisher=None,
            rights_provenance={
                "granted_by_role": "ORIGINATING_VENUE",
                "grantor": "Synthetic Venue",
                "upstream_origin": None,
                "upstream_rights_confirmed": False,
            },
            duplicate_of=None,
        )
        for key, value in over.items():
            if key in record["pipeline"]:
                record["pipeline"][key] = value
            else:
                record[key] = value
        return record

    valid = base("SYN-TX-VALID", "synthetic-completed.example", 4200)
    duplicate = base(
        "SYN-TX-DUPLICATE", "synthetic-completed.example", 4250,
        sale_date="2024-06-12", duplicate_of="SYN-TX-VALID",
    )
    pending = base("SYN-TX-PENDING", "synthetic-pending.example", 3000, price_type="ANNOUNCED_AGREEMENT")
    unpaid = base("SYN-TX-UNPAID", "synthetic-unpaid.example", 5100, price_type="AUCTION_RESULT_UNPAID")
    invalid_price = base("SYN-TX-BADPRICE", "synthetic-badprice.example", -15, original_amount=-15, amount_usd=-15)
    missing_date = base(
        "SYN-TX-NODATE", "synthetic-nodate.example", 6400,
        sale_date=None, sale_date_precision="UNKNOWN", sale_date_basis="NOT_ESTABLISHED",
    )
    no_rights = base("SYN-TX-NORIGHTS", "synthetic-norights.example", 2700)
    no_rights["rights"]["commercial_modelling"] = dict(absent)
    secondary = base(
        "SYN-TX-SECONDARY", "synthetic-secondary.example", 8300,
        rights_provenance={
            "granted_by_role": "SECONDARY_PUBLISHER",
            "grantor": "Synthetic Trade Sheet",
            "upstream_origin": "Synthetic Venue",
            "upstream_rights_confirmed": False,
        },
        source_family="Synthetic Venue",
        relay_publisher="Synthetic Trade Sheet",
    )
    holdout = base("SYN-TX-HOLDOUT", "synthetic-holdout.example", 9100)
    holdout["rights"]["redistribution"] = dict(public_grant)
    holdout["pipeline"]["publication_authorization"] = {
        "serve_derived_valuations_publicly": dict(public_grant),
        "disclose_aggregate_statistics": dict(public_grant),
    }
    holdout["calibration_role"] = "HOLDOUT_CANDIDATE"
    publishable = base("SYN-TX-PUBLIC", "synthetic-public.example", 15000)
    publishable["rights"]["redistribution"] = dict(public_grant)
    publishable["pipeline"]["publication_authorization"] = {
        "serve_derived_valuations_publicly": dict(public_grant),
        "disclose_aggregate_statistics": dict(public_grant),
    }
    records = [
        {"partition": "calibration", "record": valid},
        {"partition": "calibration", "record": pending},
        {"partition": "calibration", "record": unpaid},
        {"partition": "calibration", "record": duplicate},
        {"partition": "calibration", "record": invalid_price},
        {"partition": "calibration", "record": missing_date},
        {"partition": "calibration", "record": no_rights},
        {"partition": "calibration", "record": secondary},
        {"partition": "holdout", "record": holdout},
        {"partition": "calibration", "record": publishable},
        {"partition": "calibration", "record": {"transaction_id": "SYN-TX-MALFORMED"}},
        "not-a-record",
    ]
    return {
        "synthetic": True,
        "dataset_label": "SYNTHETIC — not real sales. Local vault demonstration only.",
        "records": records,
    }


def _transaction_files(root: Path) -> list[Path]:
    if not Path(root).exists():
        return []
    found = []
    for stage in (*TRANSACTION_STAGES, "export/approved"):
        directory = Path(root) / stage
        if directory.exists() and not _reparse_point(directory):
            found.extend(path for path in directory.glob("*.json") if path.is_file() and not path.is_symlink())
    return found


def demo(root: Path) -> dict:
    """Run the synthetic demonstration only in an empty directory.

    This refuses SOHADOT_PRIVATE_ROOT and any directory that already holds
    transaction files, so it cannot refresh or delete an existing vault.
    """
    root = Path(root).resolve()
    env_root = os.environ.get(ENV_ROOT)
    if env_root and Path(env_root).expanduser().resolve() == root:
        raise SystemExit(
            "Demo cannot use SOHADOT_PRIVATE_ROOT. "
            "Pass --root to an empty disposable directory."
        )
    if _transaction_files(root):
        raise SystemExit("Demo cannot alter a vault that already contains transaction files.")
    ensure_layout(root)
    fixture = root / "sources" / "synthetic-demonstration.json"
    payload = build_synthetic_import()
    _write_json(root, fixture, payload)
    summary = import_batch(root, fixture, require_synthetic=True)
    manifest = export_approved(root)
    return {"import": summary, "approved_record_ids": manifest["approved_record_ids"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local private valuation vault")
    parser.add_argument("--root", help="Override SOHADOT_PRIVATE_ROOT for this command")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("layout")
    import_parser = sub.add_parser("import")
    import_parser.add_argument("--file", required=True, type=Path)
    import_parser.add_argument("--require-synthetic", action="store_true")
    sub.add_parser("report")
    sub.add_parser("export")
    sub.add_parser("demo")
    args = parser.parse_args(argv)
    root = vault_root(args.root)
    if args.command == "layout":
        ensure_layout(root)
        print(root)
    elif args.command == "import":
        summary = import_batch(root, args.file, require_synthetic=args.require_synthetic)
        print(json.dumps(summary, indent=2))
    elif args.command == "report":
        stored = collect_stored(root)
        synthetic = bool(stored) and all((record.get("vault") or {}).get("synthetic") is True for record in stored)
        report = write_report(root, stored, [], synthetic)
        print(root / "evaluation" / "quality-report.md")
        print(json.dumps({"eligible": report["eligible_transactions"], "rejected": report["rejected_transactions"]}, indent=2))
    elif args.command == "export":
        manifest = export_approved(root)
        print(json.dumps({"approved_record_ids": manifest["approved_record_ids"], "published": False}, indent=2))
    elif args.command == "demo":
        result = demo(root)
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
