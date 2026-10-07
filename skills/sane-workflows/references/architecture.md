# Architecture and execution model

## Core objects

- `Orchestrator`: discovers workflow files, constructs objects, validates the selected closure, schedules ready actions, persists state, and writes aggregate JUnit results.
- `Action`: one DAG node. It declares parents, environment, resource needs, working directory, configuration, and JSON-serializable outputs.
- `Host`: execution target and resource provider. It owns environments and decides whether an action can run locally or through a nonlocal provider.
- `Environment`: reproducible process setup composed from a base environment, scripts, Lmod operations, and explicit environment-variable operations.

`sane workflow` is the normal entrypoint. An action's actual work runs in a separate process via serialized instance data. Therefore custom classes and values crossing that boundary must be importable/serializable, and mutations made only in the child do not become orchestrator state unless captured through the framework's output/state mechanism.

## Discovery and construction

Given one or more `-p/--path` roots, the runner recursively finds applicable `.py`, `.json`, and `.jsonc` files. Paths are searched in supplied order and are added to `sys.path`.

Construction order:

1. Import Python files as modules.
2. Call functions decorated with `@sane.register` in descending priority.
3. Read JSON/JSONC files, constructing hosts before actions and collecting patches.
4. Apply patches in descending priority.

This means a Python-defined custom class is available before JSON resolves its `"type"`. A workflow should not be mutated after loading completes.

## DAG semantics

Each action lists the parent actions it depends on. `child.add_dependencies(parent)` means the child waits for the parent. Supported dependency modes in the baseline are `afterok` (default), `afternotok`, `afterany`, and `after`; use the enum where code clarity benefits, or the documented string form in configuration.

Dependency validity is checked after all actions load, which allows definitions to be split and ordered freely. Diagnose unknown IDs and cycles at graph construction, not at action instantiation.

Selecting a leaf action also selects required ancestors. Filters use Python `re.match`, not arbitrary substring matching. Multiple filters are inclusive (an action may match any filter).

Useful commands:

```bash
sane workflow -p .sane -l
sane workflow -p .sane -l -vg -a leaf_action
sane workflow -p .sane -d -n -vg -a leaf_action -v
sane workflow -p .sane -r -a leaf_action -v
```

`-r`, `-d`, and `-l` are mutually exclusive. Use `-sh/--specific_host` when automatic host selection obscures diagnosis.

## Lifecycle and process boundary

Typical sequence:

1. Load workflow and resolve selected dependency closure.
2. Select/validate host, environments, and resources.
3. Host `pre_launch()` once.
4. For each ready action, action `pre_launch()` in orchestrator context.
5. In the action process: environment setup, `pre_run()`, `run()`, `post_run()`.
6. Reload action outputs into the orchestrator.
7. Call action `post_launch(retval, content)` while state is `RUNNING`.
8. Publish action state as `FINISHED`.
9. Host completion/watchdog handling and `post_launch()`.
10. Save state and aggregate JUnit results.

Returning `False` from action `post_launch` marks failure. For remote wrappers, this hook follows submission; the host handles job completion and reloads outputs before its completion hook.

Use launch hooks for orchestrator-side validation/metadata and run hooks for work scoped to the action process. `Action.launch()` is framework machinery and must not be overridden in ordinary subclasses.

## State and outputs

The default save directory is `./tmp`; the main file is normally `orchestrator.json`, with action/host intermediates. Results aggregate across saved workflow history. A successful prior action may not rerun, and its persisted outputs may be used.

- `--new` prevents loading cached state for that invocation.
- `--save_location` isolates state for testing.
- Put save and log locations outside every recursively searched `-p` root. Otherwise generated state JSON may be discovered as workflow input on the next invocation.
- Do not hand-edit save files during ordinary debugging.

Set producer values in `action.outputs`. Direct children receive producer information through `dependencies[producer_id]["outputs"]`. In dereference syntax:

```python
consumer.add_dependencies(producer.id)
consumer.config["input"] = "${{ dependencies.producer.outputs.artifact }}"
```

The producer ID can itself be selected indirectly:

```python
consumer.config["producer"] = producer.id
consumer.config["input"] = "${{ dependencies.${{ config.producer }}.outputs.artifact }}"
```

The base `Action.run()` dereferences `config`; dependency info is dereferenced in the producer's context. Custom attributes are not automatically dereferenced: call `self.dereference(...)` at the lifecycle point where the referenced runtime data exists.
