# GitHub Pages publication

`deploy/pages-manifest.json` is the explicit, approved inventory of what
sohadot.com publishes. It lists exact paths, with no publish globs:

| List | Contents |
| --- | --- |
| `pages` | Every public HTML route |
| `site_files` | CNAME, `.nojekyll`, robots, sitemap, `llms.txt`, favicon, verification files, security.txt |
| `assets`, `javascript` | Images and scripts the pages load |
| `runtime_data` | Data files the pages fetch at runtime or reference as public data (`llms.txt`, KB links) |
| `publish_exceptions` | 11 repository files under `docs/` and `scripts/` that public pages link to on sohadot.com. Each must remain linked. |

Everything else is matched by `exclude`. The four generator inputs
(`valuation_comps_seed.json`, `keywords_seed.json`, `drops_candidates.csv`,
`site-navigation.json`) are excluded: no page fetches them, and the site
serves their generated outputs.

The deploy workflow (`.github/workflows/static.yml`) runs
`scripts/build_pages_artifact.py`, which builds `_site/` and fails on:
- an unclassified tracked file (a new page, asset or data file must be added
  to the inventory deliberately);
- a pattern instead of an exact path;
- a file listed twice, or listed and excluded at once;
- a missing required file;
- an excluded path in the artifact;
- a byte-parity mismatch;
- a local link or sitemap URL that worked in the old whole-repository
  deployment but would break;
- an exception no page links to any more.

**Privacy:** excluding a file from the Pages artifact keeps it off
sohadot.com only. The GitHub repository is public, so anything private must
never be committed.
