# WRF case study: advanced patterns

This reference summarizes `wrf-model/WRF` develop and open PR #2383 as inspected on 2026-09-17. It is implementation evidence, not a promise that WRF paths or SANE prerelease behavior remain unchanged. This historical WRF inspection has not been refreshed with the PR #83 baseline update; check option-loader keyword forwarding and list-form patches before adapting those examples to the new SANE commit.

## Develop-branch patterns

The `.sane/wrf` tree separates:

- `hosts/`: Derecho PBS capacity, Lmod environments, host paths, and policy patches;
- `tests/builds/`: generated CMake/Make action matrices;
- `tests/regtests/`: generated initialize/run/compare DAGs;
- `custom_actions/`: domain-specific WRF setup and execution;
- `scripts/`: shell entrypoints that remain usable outside the Python class.

### Generated builds

Build actions are produced with `itertools.product` across compiler environments, build modes, parallel modes, cores, and cases. IDs encode the permutation. Each action selects an environment, requests CPUs, puts dereferenced CPU counts into build arguments, and publishes the build/install directory through `outputs`.

This separates reusable test definitions from site policy. Derecho JSON patches generated build IDs with host-specific CPU counts and time limits.

### Regression DAG

For each WRF case/namelist:

1. a build action is an ancestor;
2. one `InitWRF` action prepares inputs;
3. serial/MPI/OpenMP `RunWRF` actions depend on build and initialization;
4. a local comparison action depends on all run variants and consumes their output directories;
5. a local sync action depends on all comparisons, providing one selectable case-level leaf.

The implementation layers dictionaries using deep copies and `recursive_update`, then calls `load_options`. Copy before merge: mutating shared defaults can leak configuration across hundreds of generated actions.

Nested dereferencing allows the selected build ID to be held in config:

```python
"${{ dependencies.${{ config.build }}.outputs.build_dir }}"
```

Comparison arguments are generated from multiple direct dependency outputs. Local comparison/sync steps use the PBS host's `local_resources`, avoiding unnecessary scheduler jobs while throttling login-node activity.

### Custom action lifecycle

`WRFBase` publishes configurable attributes as outputs, consumes custom options, and uses:

- `pre_launch` for case/config validation and MPI/OpenMP argument injection;
- `pre_run` for paths/files created by dependencies, environment adjustment, and run-directory setup;
- `execute_subprocess` for symlink/copy setup;
- inheritance so `InitWRF` and `RunWRF` specialize only their differences.

`RunWRF` inspects direct dependency outputs and inherits missing fields from one suitable initializer. This is useful when the consumer can infer configuration from a producer, but it should fail clearly when multiple dependencies could ambiguously supply the same data.

## Open PR #2383 patterns

The restart-test PR adds a namelist parser/serializer, configurable namelist patches, additional input paths, a `RunWRFRestart` subclass that performs and compares a restart run, host config for restart datasets, and memory resource mapping/site-policy patches.

The new `restart.py` constructs a two-stage workflow per case: initializer → restart action, with both depending directly or transitively on the build. The restart action inherits most runtime fields through initializer outputs while retaining explicit build output access for `diffwrf`.

Lessons for other workflows:

- Put domain behavior in focused action subclasses, not host definitions.
- Keep site paths/account/module policy in hosts and patches.
- Publish only the producer data consumers actually need.
- Resolve early metadata in `pre_launch`, dependency-created filesystem state in `pre_run`.
- Use subclassing for true lifecycle specialization; use generated plain actions for parameter matrices.
- Preserve external shell scripts when they are independently testable and operationally useful.
- A custom action that runs multiple commands must propagate the first nonzero return and avoid marking outputs valid prematurely.

## Review cautions

- WRF uses project-specific paths, accounts, queue names, compiler modules, and scripts; never copy them as generic defaults.
- Some values are intentionally host-configured and accessed through `host_info.config`.
- Generated IDs are API-like because filters, patches, and dependencies refer to them; changing their format has broad consequences.
- PR code is unmerged and may change. Compare the current PR head and target base before using it to justify an edit.
