# GitHub Pages publication

`deploy/pages-manifest.json` is the explicit list of what sohadot.com
publishes. The deploy workflow (`.github/workflows/static.yml`) runs
`scripts/build_pages_artifact.py`, which:

1. copies only `publish` files and `publish_exceptions` into `_site/`;
2. fails if any tracked file is unclassified, if a required file is missing,
   if an excluded path appears in the artifact, if a local link or sitemap
   URL that worked in the old whole-repository deployment would break, or if
   an exception is no longer linked from a published page;
3. uploads `_site/` instead of the whole repository.

`publish_exceptions` are individual repository files (some `docs/*.md` and
`scripts/*.py`) that public pages link to on sohadot.com. They stay published
so those links keep working. Linking to the GitHub copies instead would
remove them, but that changes public pages and needs a separate decision.

**Adding a page or directory:** add it to `publish` in the same pull request.
The build fails until every tracked file is classified.

**Privacy:** excluding a file from the Pages artifact keeps it off
sohadot.com only. The GitHub repository is public, so anything private must
never be committed.
