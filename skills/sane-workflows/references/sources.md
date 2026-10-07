# Sources and baseline

Reference baseline: PR #83 merge commit `d0901c62de418c065656cf37f7235e77e4b92334`, merged 2026-10-07 into `releases/1.2.0`. Package metadata reports `1.2.0-rc.6`, but the merge includes changes after that release tag.

Validation on 2026-10-07: all 72 upstream unit tests passed at the merge checkout (`python -m unittest discover -s tests`). The proposed skill passed frontmatter validation; its relative reference links, JSON patch example, and 14 CLI examples checked successfully. Focused checks confirmed custom-loader keyword forwarding, resource replacement by patches, and the same-file priority collision described in `authoring.md`. No live PBS job was submitted.

Primary sources:

- Repository: https://github.com/islas/sane_workflows
- Documentation: https://sane-workflows.readthedocs.io/en/latest/
- Baseline source: https://github.com/islas/sane_workflows/tree/d0901c62de418c065656cf37f7235e77e4b92334
- Baseline merge PR: https://github.com/islas/sane_workflows/pull/83
- Relevant changes: PR #79 (list-form patches), #80 (option-loader keywords), #81–82 (resource replacement), #77 (completion ordering), and #83 (unified CLI)
- Tutorial source: `docs/source/tutorial/` at the baseline commit
- Demo source: `demo/` at the baseline commit
- API implementation: `sane/` at the baseline commit
- Tests: `tests/` at the baseline commit
- WRF repository: https://github.com/wrf-model/WRF
- WRF develop implementation: `.sane/wrf/` on the `develop` branch
- Open WRF restart PR #2383: https://github.com/wrf-model/WRF/pull/2383

When online research is available, prefer these primary sources. For a user's project, its pinned installed source is authoritative over this baseline. Compare prerelease tag ordering semantically; do not assume the Read the Docs header or default branch equals the requested prerelease.
