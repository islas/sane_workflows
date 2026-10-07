# Hosts, environments, and resources

## Local host

A normal `Host` is also a resource provider. Declare the capacity that SANE must schedule, add at least one environment, and set a default if actions may omit or alias their environment.

```jsonc
{
  "hosts": {
    "local": {
      "aliases": ["localhost"],
      "resources": {"cpus": 12, "memory": "32gb"},
      "mapping": {"cpus": ["cpu", "ncpus"], "memory": ["mem"]},
      "environments": {
        "default": {
          "aliases": ["generic"],
          "env_vars": [
            {"cmd": "set", "var": "OMP_NUM_THREADS", "val": "1"}
          ]
        }
      },
      "default_env": "default"
    }
  }
}
```

Resource values are nonnegative integers with optional binary scale and optional unit designator, such as `4`, `12gb`, or `512mb`. Check the pinned parser for accepted spellings before normalizing user data.

## PBS host with local throttling and Lmod

```jsonc
{
  "hosts": {
    "cluster": {
      "type": "PBSHost",
      "resources": {
        "cpu": {
          "nodes": 20,
          "exclusive": true,
          "queues": ["main"],
          "resources": {"cpus": 128, "memory": "256gb"}
        },
        "cpudev": {
          "nodes": 1,
          "exclusive": false,
          "queues": ["develop"],
          "resources": {"cpus": 256, "memory": "235gb"}
        }
      },
      "local_resources": {"cpus": 8},
      "mapping": {
        "ncpus": ["cpu", "cpus", "ncpu"],
        "mem": ["memory"]
      },
      "base_env": {
        "lmod_path": "/path/to/lmod/init/env_modules_python.py",
        "env_scripts": ["/etc/profile.d/modules.sh"]
      },
      "environments": {
        "gnu": {
          "aliases": ["gcc"],
          "lmod_cmds": [
            {"cmd": "purge"},
            {"cmd": "load", "args": ["gcc", "mpi", "netcdf", "cmake"]}
          ]
        }
      },
      "default_env": "gnu",
      "account": "PROJECT123"
    }
  }
}
```

The base environment runs before the selected named environment. In the baseline, environment setup order is scripts, Lmod commands, then explicit environment-variable commands. `local_resources` limits actions marked `local=True` so login-node work does not oversubscribe the host.

PBS queue and account must resolve from the host or action request before submission. An action can override generic resources for one host:

```python
action.add_resource_requirements({
    "cpus": 8,
    "memory": "16gb",
    "cluster": {
        "cpus": 32,
        "memory": "64gb",
        "queue": "main",
        "timelimit": "00:30:00"
    }
})
```

In JSON, place the same nested mapping under `"resources"`. A host-specific `select` string can override PBS select construction verbatim; use it only when normal resource deduction cannot express the request, because it bypasses much of the mapping logic.

A scheduled action and a login-node-local consumer can be declared together as:

```jsonc
"actions": {
  "scheduled_build": {
    "environment": "gnu",
    "config": {"command": "./scripts/build.sh", "arguments": []},
    "resources": {
      "cpus": 8,
      "memory": "16gb",
      "cluster": {
        "cpus": 32,
        "memory": "64gb",
        "queue": "main",
        "timelimit": "00:30:00"
      }
    }
  },
  "local_compare": {
    "local": true,
    "environment": "gnu",
    "dependencies": {"scheduled_build": "afterok"},
    "config": {"command": "./scripts/compare.sh", "arguments": []},
    "resources": {"cpus": 2, "memory": "2gb"}
  }
}
```

For an exclusive node set, SANE may acquire/account a full node internally even when the emitted PBS `select` retains the action's requested CPU/memory values. Do not assume `exclusive: true` by itself adds a scheduler-specific whole-node directive; inspect the generated submit arguments and apply site policy where required.

## Resource mapping

Mapping keys are canonical host/PBS resource names and values are accepted aliases. Both host resources and action requests are normalized. Keep aliases non-overlapping. This lets reusable actions request `cpus`/`memory` while the PBS site emits `ncpus`/`mem`. When changing resource mappings, check the generated submission line in a dry-run.

## Resource replacement

Use `overwrite=True` with `add_resources` or `add_resource_requirements` to replace existing values; direct calls retain them by default. JSON patches pass `overwrite=True` through option loading, so check effective capacities and requests after patching.

For older pinned versions, inspect the signatures: resource providers used the keyword `override`.

## Environment scripts and Lmod

- `env_scripts`: source setup scripts by executing them and applying the environment delta. Scripts must be silent; unexpected stdout can corrupt parsing.
- `lmod_path`: path to Lmod's Python integration module, not merely the `module` shell function.
- `lmod_cmds`: ordered module operations. Site-specific `--force purge` patterns can be expressed by setting `cmd` and `args` exactly as required by Lmod.
- `env_vars`: ordered `set`, `unset`, `append`, or `prepend` operations. Categories group operations but do not replace careful ordering.

Environment names and aliases are matched against `Action.environment`. A base environment alone does not satisfy the baseline requirement for a runnable selected environment.

## Resource correctness checklist

Use the questions relevant to the resource behavior being changed or investigated.

- Do action names normalize to resources the host actually provides?
- Are counts per action realistic, including MPI ranks, OpenMP threads, memory, GPUs, and walltime?
- For exclusive node sets, does the request intentionally consume whole-node capacity?
- Does the requested queue accept the chosen homogeneous node set?
- Are `queue` and `account` resolved after host-specific overrides?
- Are local helper/comparison actions marked local and covered by `local_resources`?
- Does the application itself honor the allocated values passed through dereferencing?

## Safe PBS shape validation

From a non-cluster machine, force the PBS host so automatic host matching does not hide it, and keep generated state/logs outside the workflow root:

```bash
sane workflow -p .sane -d -n -vg -v -a local_compare \
  -sh cluster -sl /tmp/sane-pbs-state -ll /tmp/sane-pbs-logs
```

Inspect the logged `qsub` arguments for queue, account, walltime, `select`, resource names, and the launcher command. Baseline PBS dry-runs may include watchdog polling delays and simulate a job ID/success.

A dry-run does **not** execute or verify environment scripts, Lmod paths/module names, `qsub` availability, scheduler acceptance, remote filesystem paths, application behavior, or output correctness. Listing/graphing validates only discovery and DAG construction; dry-run adds host/resource resolution and wrapper/submission shape.
