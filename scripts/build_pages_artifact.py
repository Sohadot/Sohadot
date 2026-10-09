#!/usr/bin/env python3
"""Build the filtered GitHub Pages artifact from deploy/pages-manifest.json.

The site used to be deployed by uploading the whole checkout, which published
scripts, tests, internal documentation and research files alongside the site.
This script copies only the files the manifest marks for publication into an
output directory (default `_site/`) and checks the result:

  1. classification: publication is an explicit inventory of exact paths
     (pages, site files, assets, JavaScript, runtime data, and linked
     exceptions); there are no publish globs. Every tracked file must be
     listed or excluded. A new, unclassified file fails the build until it
     is deliberately classified;
  2. required files (CNAME, index, 404, sitemap, ...) are present;
  3. byte parity: every published file is identical to the committed file;
  4. links: every local reference in published HTML, CSS, JS, JSON-LD and
     the sitemap resolves inside the artifact. A reference that resolves in
     the old whole-repository deployment but not in the artifact is a
     regression and fails the build. References already broken in the old
     deployment are reported, not hidden;
  5. exclusion: no excluded path is present in the artifact.

Usage:
  python3 scripts/build_pages_artifact.py [--out _site] [--report report.json]
Exits 0 and prints PASS, or prints each problem prefixed "FAIL:" and exits 1.
Excluding files from the artifact does not make them private: the
repository itself is public.
"""
import argparse
import fnmatch
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "deploy" / "pages-manifest.json"
SITE_HOSTS = {"sohadot.com", "www.sohadot.com"}
# Paths the old deployment never shipped (actions/upload-pages-artifact skips them).
OLD_DEPLOY_SKIPS = (".git/", ".github/")

ATTR_RE = re.compile(r"""\b(?:href|src|action|poster|data-src)\s*=\s*(["'])(.*?)\1""", re.I | re.S)
SRCSET_RE = re.compile(r"""\bsrcset\s*=\s*(["'])(.*?)\1""", re.I | re.S)
META_URL_RE = re.compile(r"""<meta[^>]+content\s*=\s*(["'])(https?://(?:www\.)?sohadot\.com[^"']*)\1""", re.I)
CSS_URL_RE = re.compile(r"""url\(\s*(["']?)([^)"']+)\1\s*\)""", re.I)
ABS_SITE_RE = re.compile(r"""https?://(?:www\.)?sohadot\.com(/[^\s"'<>)\\]*)?""", re.I)
JS_PATH_RE = re.compile(r"""(["'`])(/(?:[A-Za-z0-9._~-]+/)*[A-Za-z0-9._~-]+\.(?:json|js|css|png|jpe?g|svg|webp|ico|csv|txt|xml|html|woff2?))(?:\?[^"'`]*)?\1""")
SITEMAP_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)


def tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True).stdout
    return sorted(p for p in out.decode("utf-8").split("\0") if p)


def matches(path, pattern):
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    if "/" not in pattern:
        return "/" not in path and fnmatch.fnmatchcase(path, pattern)
    return fnmatch.fnmatchcase(path, pattern)


PUBLISH_LISTS = ("pages", "site_files", "assets", "javascript", "runtime_data")


def publish_inventory(manifest):
    """Explicit list of files to publish. There are deliberately no globs."""
    inventory = {}
    for key in PUBLISH_LISTS:
        for path in manifest.get(key, []):
            inventory.setdefault(path, []).append(key)
    for path in manifest.get("publish_exceptions", {}):
        inventory.setdefault(path, []).append("publish_exceptions")
    return inventory


def check_manifest(manifest, files):
    problems = []
    inventory = publish_inventory(manifest)
    tracked = set(files)
    for path, lists in sorted(inventory.items()):
        if len(lists) > 1:
            problems.append(f"{path}: listed more than once ({', '.join(lists)})")
        if path not in tracked:
            problems.append(f"{path}: listed for publication but not a tracked file")
        if any(ch in path for ch in "*?["):
            problems.append(f"{path}: publication entries must be exact paths, not patterns")
    for path in manifest.get("pages", []):
        if not path.endswith(".html"):
            problems.append(f"{path}: 'pages' may only list .html files")
    for path in manifest.get("runtime_data", []):
        if not path.startswith("data/"):
            problems.append(f"{path}: 'runtime_data' may only list files under data/")
    for path in manifest.get("publish_exceptions", {}):
        if not any(matches(path, p) for p in manifest["exclude"]):
            problems.append(f"{path}: publish exception is not inside an excluded area; list it normally")
    return problems


def classify(files, manifest):
    published, excluded, problems = [], [], []
    inventory = publish_inventory(manifest)
    exceptions = manifest.get("publish_exceptions", {})
    for path in files:
        listed = path in inventory
        exc = [p for p in manifest["exclude"] if matches(path, p)]
        if listed and exc and path not in exceptions:
            problems.append(f"{path}: listed for publication but also matches exclude {exc}")
        elif listed:
            published.append(path)
        elif exc:
            excluded.append(path)
        else:
            problems.append(f"{path}: not classified in deploy/pages-manifest.json (list it for publication or exclude it)")
    return published, excluded, problems


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_refs(rel, text):
    """Local references in a published text file, as raw strings."""
    refs = set()
    suffix = PurePosixPath(rel).suffix.lower()
    if suffix in {".html", ".htm"}:
        for m in ATTR_RE.finditer(text):
            refs.add(html.unescape(m.group(2)))
        for m in SRCSET_RE.finditer(text):
            for part in html.unescape(m.group(2)).split(","):
                if part.strip():
                    refs.add(part.strip().split()[0])
        for m in META_URL_RE.finditer(text):
            refs.add(m.group(2))
        for m in ABS_SITE_RE.finditer(text):
            refs.add(m.group(0))
        for m in CSS_URL_RE.finditer(text):
            refs.add(m.group(2))
        for m in JS_PATH_RE.finditer(text):
            refs.add(m.group(2))
    elif suffix == ".css":
        refs.update(m.group(2) for m in CSS_URL_RE.finditer(text))
    elif suffix == ".js":
        refs.update(m.group(2) for m in JS_PATH_RE.finditer(text))
        refs.update(m.group(0) for m in ABS_SITE_RE.finditer(text))
    elif suffix == ".xml" or rel == "llms.txt":
        refs.update(m.group(0) for m in ABS_SITE_RE.finditer(text))
    return refs


def resolve(ref, from_rel):
    """Map a reference to a site path, or None if it is not local."""
    ref = ref.strip()
    if not ref or ref.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:", "{", "$")) or "${" in ref:
        return None
    parts = urlsplit(ref)
    if parts.scheme in ("http", "https"):
        if parts.hostname not in SITE_HOSTS:
            return None
        path = parts.path or "/"
    elif parts.scheme or ref.startswith("//"):
        return None
    else:
        path = parts.path
        if not path:
            return None
        if not path.startswith("/"):
            base = PurePosixPath("/" + from_rel).parent
            path = str(base / path)
    path = unquote(path)
    # Normalise ./ and ../ segments.
    segs = []
    for seg in path.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if segs:
                segs.pop()
            continue
        segs.append(seg)
    trailing = path.endswith("/")
    return "/" + "/".join(segs) + ("/" if trailing and segs else "")


def exists_in(site_path, files):
    """GitHub Pages resolution: exact file, dir/index.html, or extensionless .html."""
    rel = site_path.lstrip("/")
    if rel == "":
        return "index.html" in files
    if site_path.endswith("/"):
        return rel + "index.html" in files
    return rel in files or rel + ".html" in files or rel + "/index.html" in files


def check_links(published, root):
    """Return {(source, ref, site_path)} for every local reference."""
    refs = set()
    for rel in published:
        if PurePosixPath(rel).suffix.lower() not in {".html", ".htm", ".css", ".js", ".xml"} and rel != "llms.txt":
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for ref in extract_refs(rel, text):
            site_path = resolve(ref, rel)
            if site_path:
                refs.add((rel, ref, site_path))
    return refs


def build(out_dir, report_path=None, manifest=None, files=None, source_root=None):
    manifest = manifest or json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    files = files if files is not None else tracked_files()
    source_root = Path(source_root) if source_root else REPO_ROOT
    published, excluded, problems = classify(files, manifest)
    fails = check_manifest(manifest, files) + list(problems)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for rel in published:
        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / rel, dest)

    artifact = sorted(str(p.relative_to(out_dir)).replace("\\", "/") for p in out_dir.rglob("*") if p.is_file())
    artifact_set = set(artifact)

    for req in manifest["required"]:
        if req not in artifact_set:
            fails.append(f"required file missing from artifact: {req}")
    for rel in published:
        if sha256(source_root / rel) != sha256(out_dir / rel):
            fails.append(f"byte parity failed: {rel}")
    exceptions = manifest.get("publish_exceptions", {})
    for rel in artifact:
        if rel not in exceptions and any(matches(rel, p) for p in manifest["exclude"]):
            fails.append(f"excluded path present in artifact: {rel}")
    for rel in exceptions:
        if rel not in files:
            fails.append(f"publish exception is not a tracked file: {rel}")
    if set(artifact) != set(published):
        fails.append("artifact contents differ from the published file list")

    old_deploy = {f for f in files if not f.startswith(OLD_DEPLOY_SKIPS)}
    refs = check_links(published, out_dir)
    regressions, preexisting = [], []
    for source, ref, site_path in sorted(refs):
        if exists_in(site_path, artifact_set):
            continue
        if exists_in(site_path, old_deploy):
            regressions.append(f"{source}: {ref} -> {site_path}")
        else:
            preexisting.append(f"{source}: {ref} -> {site_path}")
    fails.extend(f"link regression (resolved before filtering, broken after): {r}" for r in regressions)
    # Exceptions stay minimal: each must be linked from a published page.
    referenced = {site_path.lstrip("/") for _, _, site_path in refs}
    for rel in exceptions:
        if rel not in referenced:
            fails.append(f"publish exception {rel} is no longer referenced by any published page; remove it")

    sitemap = (out_dir / "sitemap.xml").read_text(encoding="utf-8") if "sitemap.xml" in artifact_set else ""
    sitemap_urls = SITEMAP_LOC_RE.findall(sitemap)
    for url in sitemap_urls:
        site_path = resolve(url, "sitemap.xml")
        if not site_path or not exists_in(site_path, artifact_set):
            fails.append(f"sitemap URL does not resolve in artifact: {url}")

    report = {
        "manifest_version": manifest["version"],
        "tracked_files": len(files),
        "published_files": len(published),
        "excluded_files": len(excluded),
        "old_deployment_files": len(old_deploy),
        "removed_from_deployment": sorted(old_deploy - set(published)),
        "published_html_routes": sorted(p for p in published if p.endswith(".html")),
        "publish_exceptions": sorted(exceptions),
        "local_references_checked": len(refs),
        "sitemap_urls_checked": len(sitemap_urls),
        "preexisting_broken_references": preexisting,
        "link_regressions": regressions,
        "artifact_sha256": hashlib.sha256("\n".join(f"{p} {sha256(out_dir / p)}" for p in artifact).encode()).hexdigest(),
    }
    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return fails, report


def main():
    parser = argparse.ArgumentParser(description="Build the filtered GitHub Pages artifact")
    parser.add_argument("--out", default=str(REPO_ROOT / "_site"))
    parser.add_argument("--report", help="write a JSON build report to this path")
    args = parser.parse_args()
    fails, report = build(Path(args.out).resolve(), args.report)
    for f in fails:
        print(f"FAIL: {f}")
    for p in report["preexisting_broken_references"]:
        print(f"NOTE: reference already broken before filtering: {p}")
    if fails:
        sys.exit(1)
    print(f"PASS: Pages artifact built — {report['published_files']} files published, "
          f"{report['excluded_files']} excluded, {len(report['removed_from_deployment'])} removed from deployment, "
          f"{report['local_references_checked']} local references and {report['sitemap_urls_checked']} sitemap URLs resolve; "
          f"{len(report['preexisting_broken_references'])} pre-existing broken references noted")


if __name__ == "__main__":
    main()
