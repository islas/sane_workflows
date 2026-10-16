---
name: sane-workflows
description: Read, design, implement, review, customize, and diagnose workflows built with the sane-workflows Python package and its stateful DAG architecture, including Python/JSON definitions, custom actions, local hosts, PBS hosts, environments, resources, outputs, and dependency failures. Use for SANE workflow code or logs; do not use for unrelated DAG engines.
---

# SANE Workflows

Work against the user's installed or pinned SANE version. The reference baseline for this skill is the PR #83 merge (commit `d0901c62`, 2026-10-07), whose package metadata reports `1.2.0-rc.6`. This commit includes changes after the `v1.2.0-rc.6` tag; use the commit when reproducing the baseline. Prerelease APIs can move: inspect the project's lockfile/metadata and local `sane` source before changing code when a different revision is present. Do not silently rewrite working code to the baseline.

## Consult references as needed

Use existing context first. If guidance is missing, start with the most relevant reference and read only the sections needed for the current decision. Consult additional references only to resolve specific unanswered questions.

- Workflow creation or modification: [authoring.md](references/authoring.md).
- Discovery, dependencies, outputs, lifecycle, or saved state: [architecture.md](references/architecture.md).
- Host environments, resource requests, or PBS submission: [hosts-environments-resources.md](references/hosts-environments-resources.md).
- Runtime monitoring and failure investigation: [diagnostics.md](references/diagnostics.md). Read the relevant section for the current monitoring or diagnostic question.
- WRF implementation examples: [wrf-case-study.md](references/wrf-case-study.md), when an example would clarify the implementation. Its conventions are examples, not requirements.
- Provenance and upstream links: [sources.md](references/sources.md).

Use `sane workflow` to run or validate workflows and `sane view` to inspect saved results at this baseline. The deprecated `sane_runner` and `sane_view` commands remain available; retain them when working against an older pinned version that lacks the unified CLI.

## Operating method

1. Establish the SANE version, entrypoint, workflow roots, selected host, selected actions, and saved-state behavior. On follow-ups, reuse established setup and validation results; revisit what the request or changed files affect. Ask only for missing information that materially affects the result.
2. Locate workflows using user-provided paths or runner configuration. Otherwise, search for `.sane/` directories or Python/JSON definitions within the relevant project. Exclude generated builds, logs, and saved state from definition discovery. Identify relevant files before reading targeted sections; expand only to resolve a specific uncertainty. If output is truncated, narrow the query rather than increasing the output limit.
3. When adapting a workflow, trace the existing action or small dependency chain most similar to the requested behavior and check current script options before carrying forward legacy settings. Expand into application source, additional examples, or path-filtered history to answer a specific unresolved question; let that question determine the paths and scope inspected.
4. Preserve ownership boundaries: the orchestrator schedules actions and tracks dependency completion; hosts manage environments and resources; actions declare requirements and perform work. Do not mutate internal action state or status.
5. Use public interfaces relevant to the task and supported lifecycle hooks for custom execution behavior. Do not override `Action.launch()`.
6. Account for the selected actions’ dependency closure, including environments, resources, and producer outputs; inspecting these dependencies does not require executing them all. Choose validation that answers the remaining question: graph or dry-run for structure and resources, focused execution for runtime behavior. Stop when that question is answered; broaden or repeat only when changed behavior, new evidence, or the user’s requested scope requires it. Report what remains unverified.
7. For long-running actions, retain the job/session identifier and keep logs on disk. Prefer completion/failure notifications; otherwise, reduce polling while healthy. Inspect logs only for a specific diagnostic question or user request. Progress updates do not require log inspection.
8. When validation fails, identify the earliest failing layer and whether it results from the change. Fix issues within scope. For unrelated blockers, preserve concise evidence, report what remains unverified, and continue independent work. Broaden investigation or repair only when needed for the requested outcome or explicitly requested.
9. When changing files, preserve local style and mixed Python/JSON boundaries. Explain any version-specific inference.

## Non-negotiable invariants

- Every runnable action needs a matching host environment; a useful host needs at least one non-base environment, usually via `default_env`.
- Dependencies point from a child action to its parent prerequisites and must remain acyclic.
- Direct dependency information is available through `dependencies.<id>.outputs...`; spell `outputs` in the plural at this baseline.
- Values placed in `outputs` must be JSON-serializable and valid by successful action completion. Custom action instances and other state crossing the launcher boundary must also satisfy the baseline serializer/import requirements.
- Custom `load_extra_options(self, options, origin, **kwargs)` implementations consume handled keys with `pop(...)` and forward `**kwargs` to `super().load_extra_options(options, origin, **kwargs)`. Preserve keyword forwarding in any overridden option-loading method.
- Resource requests must describe real critical usage. An undeclared resource is not scheduled or protected from oversubscription.
- Environment scripts must be silent because SANE captures and reapplies environment differences.
- Relative command/script paths are resolved from the workflow/action working directory, not from the defining file.
- Saved state can suppress reruns and preserve old outputs. Use `--new` or an isolated save location only when the user's intent permits a fresh evaluation. Keep save/log directories outside every recursively scanned `-p` root, or generated JSON may be reloaded as workflow configuration.

## Response expectations

For generated code, provide the necessary files and an exact validation command. For review or diagnosis, distinguish observations from inference and explain how the root failure affects downstream actions. State validation limits: a PBS dry-run checks submission construction, not scheduler acceptance or application results.

When handing off unfinished work, summarize completed checks, unresolved questions, any live job/session identifier, and the next command needed to resume.
