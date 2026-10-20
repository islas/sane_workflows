# Runtime monitoring and failure diagnosis

## Monitor long-running actions

Use completion/failure notifications from the available execution interface when supported. Otherwise, check concise action or scheduler status and increase polling intervals while the job remains healthy. A wait returning without completion does not itself justify reading application logs.

Use known typical duration and the selected host’s effective timelimit to guide monitoring. Check whether the limit is enforced; runtime limits generally start after scheduling and do not bound queue time. A timelimit is not an expected completion time.

Quiet logs alone do not establish a stall. Investigate when status reports a problem, an expected progress signal stops, or execution exceeds a supported expectation. Read bounded new output around the relevant event rather than repeatedly rereading logs.

On completion, check the exit status and artifacts needed to answer the validation question. Preserve the job/session identifier, log location, and resume command if work continues later.

## Separate workflow failures from application failures

Start with the earliest failing layer below. Check whether SANE supplied the intended command, working directory, environment, resources, and dependency outputs. An application error may result from incorrect workflow setup; its presence alone does not identify which layer needs repair.

When the invocation is correct, investigate the application’s first causal error without assuming SANE internals are involved. Use a focused command or target when it can reproduce the problem without rebuilding the dependency chain.

Classifying the failure does not expand the task’s repair scope. Fix workflow defects within scope. For unrelated application or platform blockers, preserve evidence, explain which checks are blocked, and continue independent work. Prepare a proposed fix when requested; follow the user’s existing review and authorization boundaries.

## Start with the earliest failing layer

1. **Discovery/import**: missing file, invalid JSONC, Python import error, custom type unavailable.
2. **Construction/options**: duplicate ID, unused keys, wrong option spelling, patch misses target.
3. **Graph**: unknown dependency, cycle, unexpected dependency mode or selection closure.
4. **Host/environment**: wrong host selected, environment name/alias absent, Lmod path/script failure.
5. **Resources/submission**: unmapped resource, insufficient capacity, missing queue/account, malformed PBS select or submit output.
6. **Action launch**: serialization/importability, working directory, permissions, missing executable/script.
7. **Action execution**: hook exception, command exit code, application error, expected output absent.
8. **Persistence**: stale state skipped work, prior output loaded, action/host save mismatch.

Downstream actions may be skipped correctly after a parent failure. Report the first causal error and then its DAG consequences.

## Evidence collection

Collect evidence relevant to the suspected failing layer, starting with information already available. Possible sources include:

- exact command line and SANE version/commit;
- workflow roots and current/working directory;
- `-l -vg` output for the selected target;
- selected host and matching environment;
- targeted excerpts from the runner log and failing action log (normally `<action-id>.log` under the configured log location; application scripts may write additional logs);
- PBS submit command, returned job ID, scheduler state, stdout/stderr, and exit status;
- save location and whether `--new` was used;
- producer output values when dereferencing a dependency.

Inspect saved state in the default `./tmp` directory:

```bash
sane view status
sane view summary
sane view logs --errors
```

Supply a save directory only when the workflow saved state elsewhere. `logs` lists paths; `--errors` includes failed actions only. Consult subcommand `--help` for reporting options.

Increase detail with `-v` and a lower numeric `-g/--debug_level` as needed. Preserve logs before rerunning.

## Symptom map

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Action not listed | wrong `-p`, import failed, registration not executed, filter uses `re.match` | discovery log, registration decorator, filter anchor |
| Custom JSON type not found | module outside supplied root, bad qualified name, import failure | Python load precedes JSON; compare module namespace |
| `Unused keys in dict` | misspelled option or subclass did not `pop` it | `load_extra_options` chain and exact key |
| `TypeError` for unexpected `overwrite` keyword | custom option-loader override lacks `**kwargs` | update overridden loading signatures and forward keywords to `super` |
| Dependency missing/cycle | ID typo, generated ID mismatch, back-edge | graph all ancestors; compare IDs literally |
| Action unexpectedly did not rerun | saved success state | save location, prior state, rerun with isolated state/`--new` if authorized |
| Dereference remains literal | wrong attribute path, custom attribute never explicitly dereferenced, resolution too early | `outputs` plural; lifecycle timing; dependency is direct |
| Dependency output absent | producer never set/saved it, producer failed, non-JSON-serializable value, stale cache | producer action log, saved outputs, fresh isolated run |
| No matching environment | action name/alias mismatch or only base environment exists | host environments and `default_env` |
| Lmod import/setup failure | `lmod_path` points to shell init rather than Python module, module conflict | base script, Python module path, command order |
| Environment script failure | script exits nonzero or prints output | run it in a clean shell; require silent success |
| Host says resource unavailable | missing mapping, unit mismatch, request exceeds node set | normalized request and host capacities |
| PBS missing queue/account | neither host nor host-specific action request supplies it | resolved action resources before submission |
| PBS submitted but workflow waits/fails | scheduler query/parse mismatch, remote job failed, output unavailable | job ID, query commands, scheduler stdout/stderr |
| Command not found | relative path based on working directory, file not executable, environment PATH | resolved working directory and permissions |
| Hook works locally but fails in action | process boundary, missing import/serialization, runtime-only environment | launcher log and picklability/importability |

## Controlled reproduction

Use a temporary save location and smallest dependency-complete target:

```bash
sane workflow -p .sane -l -vg -a failing_leaf
sane workflow -p .sane -d -n -v -a failing_leaf \
  --save_location /tmp/sane-debug-state
```

The temporary state/log location must not be under any supplied `-p` root, because discovery recursively loads JSON/JSONC/Python files and can mistake generated state for workflow input.

`--new` prevents loading old state but may write the new run back to the same save location. Use a new save location when old evidence must be preserved. List/graph and dry-run can validate dependency structure and environment/resource selection, but cannot prove that a producer's runtime-generated output key or file will exist.

For missing outputs, distinguish the visible failure from the contract defect: the consumer may raise during dereferencing even though the root cause is a producer that completed successfully without publishing the required key.

If evidence points to the execution framework, replace the application command in an isolated copy with a minimal observable command to test that hypothesis. Do not convert a production PBS run into a real submission merely to test a theory. Mock scheduler commands or use dry-run for submission construction.

## Diagnose custom hooks

- `pre_launch`: values available in the orchestrator process; validate declared configuration and resolve host metadata.
- `pre_run`: dependency-created files and action environment should exist; prepare runtime directories.
- `run`: return an integer and use framework subprocess helpers consistently.
- `post_run`: finalize child-process work and outputs.
- `post_launch`: inspect reloaded outputs in orchestrator context; return `False` to mark failure. See [architecture.md](architecture.md) for completion timing.

If a subclass overrides a hook, check whether it calls `super()` in the necessary order. Never “fix” a failure by forcing internal state/status.

## Error-report format

State the failing action and earliest failing layer; direct evidence; root cause or ranked hypotheses; smallest corrective change; exact verification command; and whether saved state must be isolated or invalidated.
