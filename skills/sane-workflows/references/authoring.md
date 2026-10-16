# Authoring workflows

## Choose Python, JSON, or both

- Use JSON/JSONC for declarative hosts, actions, environments, resource policies, and patches.
- Use Python for generated action families, conditional construction, reusable subclasses, and complex validation.
- A mixed design is normal: Python defines types/actions; JSON supplies site policy and patches.

Keep workflow files under a dedicated root such as `.sane/<project>/` because every matching Python/JSON file beneath supplied roots is discovered.

## Minimal Python workflow

```python
import sane

@sane.register(priority=10)
def local_host(orch):
    host = sane.Host("workstation")
    host.add_resources({"cpus": 8, "memory": "16gb"})
    env = sane.Environment("default", aliases=["generic"])
    host.add_environment(env)
    host.default_env = env.name
    orch.add_host(host)

@sane.register
def actions(orch):
    prepare = sane.Action("prepare")
    prepare.environment = "generic"
    prepare.config.update({"command": "echo", "arguments": ["prepared"]})
    prepare.outputs["artifact"] = "build/input.dat"
    prepare.add_resource_requirements({"cpus": 1})

    consume = sane.Action("consume")
    consume.environment = "generic"
    consume.add_dependencies(prepare.id)
    consume.config.update({
        "command": "echo",
        "arguments": ["${{ dependencies.prepare.outputs.artifact }}"],
    })
    consume.add_resource_requirements({"cpus": 2})

    orch.add_action(prepare)
    orch.add_action(consume)
```

Confirm exact method signatures against the pinned source when adapting older/newer revisions.

## Custom action pattern

```python
import sane

class ManifestAction(sane.Action):
    def __init__(self, id):
        super().__init__(id)
        self.source_dir = "."
        self.manifest = "manifest.txt"

    def load_extra_options(self, options, origin, **kwargs):
        self.source_dir = options.pop("source_dir", self.source_dir)
        self.manifest = options.pop("manifest", self.manifest)
        super().load_extra_options(options, origin, **kwargs)

    def pre_launch(self):
        self.source_dir = self.dereference(self.source_dir)
        if not self.source_dir:
            raise ValueError("source_dir must not be empty")

    def run(self):
        retval, _ = self.execute_subprocess(
            "find", [self.source_dir, "-type", "f"], verbose=True
        )
        if retval == 0:
            self.outputs["manifest"] = self.manifest
        return retval
```

Important practices:

- Initialize subclass fields before loading options.
- Consume every supported custom key with `pop` and forward `**kwargs` to `super`. Option loading passes keywords such as `overwrite=True` during patch application; an older two-argument override will raise `TypeError` when patched.
- Validate data that exists before launch in `pre_launch`; resolve dependency-created files in `pre_run`.
- Return a process-style integer from `run` (`0` means success). In this baseline, `execute_subprocess` returns `(return_code, captured_output)`, so unpack it.
- Use `execute_subprocess` for consistent logging/command behavior when appropriate.
- Do not override `launch` or mutate state/status to emulate success.

JSON can instantiate an imported custom type with a fully qualified name relative to a supplied workflow root. A shortened type is acceptable only when resolution is unambiguous.

The base JSON action schema does not provide an arbitrary `outputs` option in the documented template. When a producer must publish outputs, define it in Python or a custom action whose option loader explicitly supports that configuration.

## Generated families and policy patches

Use `itertools.product` to generate systematic IDs and action matrices. Keep algorithmic defaults in Python, then use JSON patches for host/site policy such as queue-specific time or memory. Avoid burying site paths and accounts inside reusable action classes.

Patches apply after all object creation and can target concrete IDs or supported filter syntax. The JSON `"patches"` value is a list of patch objects. Each object may specify a priority; higher priorities apply first. For example:

```json
{
  "patches": [
    {
      "priority": 10,
      "actions": {
        "consume": {"resources": {"cpus": 4}}
      }
    }
  ]
}
```

Patch loading passes `overwrite=True`, so existing resource capacities and requests can be replaced. Verify effective resources as well as target matches with list/graph or dry-run output; a patch that matched nothing may only warn. Multiple patches with the same priority in one file replace earlier entries; combine them or use distinct priorities.

## Validation examples

Choose the command that answers the current validation question; these examples are not a required sequence.

```bash
sane workflow -p .sane -l
sane workflow -p .sane -l -vg -a target
sane workflow -p .sane -d -n -vg -v -a target
sane workflow -p .sane -r -n -v -a one_small_action
```

Use a separate `--save_location` for experiments that must not affect an existing run history. Place it, and any explicit log location, outside every recursively scanned `-p` root.
