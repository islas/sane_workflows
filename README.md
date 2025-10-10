# SANE Workflows
[![](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/) [![unittest](https://github.com/islas/sane_workflows/actions/workflows/unittest.yml/badge.svg)](https://github.com/islas/sane_workflows/actions/workflows/unittest.yml)

Simple Action 'n Environment Workflow

SANE is a DAG-based action workflow runner augmented with environments provided
by hosts.

It provides:
  * DAG-based action mapping, with statefulness to preserve runs
  * both python and JSON config based workflow management
  * sourcing workflows from multiple directories
  * resource management between host and actions
  * HPC-resource enabled hosts (PBS base fully implemented)
  * environment variable manipulation via shell scripts, lmod, and explicit setting
  * extensible `Host`, `Environment`, and `Action` classes that can be derived from
    * derived classes allowed within user workflow directories
    * derived classes accessible within user JSON configs
  * a priority-based python registration decorator
  * a priority-based JSON patching feature

## Overview

Below is a high level overview of how running a workflow works. Many of the complex
nuances, such as type finding, HPC submission, resource management, etc., are left out.

The focus should instead be:
  * a single _orchestrator_ manages the workflow
  * a node in the DAG-workflow is an _action_
  * a _host_ provides _environments_ for an _action_
  * _actions_ are run independently in an order informed by DAG dependencies
  * an _action_ itself is `run()` in a totally separate subprocess (not python subprocess!)
  * instance information is transferred via python pickling

![SANE Overview](https://github.com/islas/sane_workflows/blob/main/docs/images/sane_overview.png?raw=true)

## Python Usage
To utilize `sane` in a python setting, create a python file (module) and import the
`sane` package. Assuming you are running via the provided entry point `sane_runner.py`,
you do not need to ensure `sane` is within your `PYTHONPATH`. Afterwards, to add,
remove, or modify the _orchestrator_ use the `@sane.register(priority=0)` decorator.
Providing a priority is optional, and if no priority is given, no `()` call is necessary,
as seen below. The _orchestrator_ is provided as the single argument to the decorated
function.

```python
import sane

@sane.register
def my_workflow( orch ):
  my_action = sane.Action( "id" )
  orch.add_action( my_action )
```

If a priority is given, functions will be evaluated in descending order (highest
priority first)
```python
import sane

@sane.register
def last( orch ):
  # defaul priority is 0
  pass

@sane.register( priority=5 )
def second( orch ):
  pass

@sane.register( 99 )
def first( orch ):
  pass
```

## JSON Usage
To utilize `sane` in a JSON config file setting, create a JSON file (config) that
contains at least one of the keys : `"hosts"`, `"actions"`, or `"patches"`. Refer
to the [`docs/template.jsonc`](docs/template.jsonc) on what default fields are appropriate. 
Note that if you define your own type (and thus add your own `load_extra_config()`),
additional fields may be provided in the config.
```jsonc
{
  "hosts" :
  {
    "dummy" : { "environment" : "generic" }
  },
  "actions" :
  {
    "my_action" :
    {
      "config" : { "command" : "echo", "arguments" : [ 1 ] },
      "environment" : "generic"
    }
  }
}
```

By default, you may utilize _action_ attributes inside of the generic `"config" : {}`
dictionary field. The attributes are automatically scoped to the current _action_
and are accessed via YAML-like dereferencing (`${{}}`):
```jsonc
// ... previous config
  "actions" :
  {
    "my_action" :
    {
      "config" : { "command" : "echo", "arguments" : [ "${{ id }}" ] }
    }
  }
// ... rest of config
```

## Running a workflow
To run a workflow, place all your `.py` and `.json[c]` files into any directory
layout you want, but try to isolate your workflow files from other non-workflow
`.py` and `.json[c]` files as all matching files under listed directories are 
loaded. Supplementary files, like shell scripts (`.sh`), will not be loaded.

Provide the paths of your workflow with `-p`/`--path`, then list or filter for
whichever _actions_ you want to operate with, along with the `-r` flag to run these
_actions_:
```bash
<path to sane_workflows>/bin/sane_runner.py -p <workflow path> [-p <other path>] -a my_action -r
```
> [!NOTE]
> All paths provided are added to `sys.path` for importing of modules. Thus, when
> using custom classes within your workflow, `import` their module as if from the
> workflow path, e.g. `-p .workflow` for `.workflow/custom_actions/my_action_def.py`
> as `import custom_actions.my_action_def`

You will get output that looks like so:
```
./bin/sane_runner.py -p demo/ -a action_000 -r
2025-10-08 18:22:56 INFO     [sane_runner]        Logging output to /home/aislas/frameflow/log/runner.log
2025-10-08 18:22:56 INFO     [orchestrator]       Searching for workflow files...
2025-10-08 18:22:56 INFO     [orchestrator]         Searching demo/ for *.json
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/custom_def_usage.json
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/simple_action.json
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/resource_action.json
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/hpc_host.json
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/patches.json
2025-10-08 18:22:56 INFO     [orchestrator]         Searching demo/ for *.jsonc
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/simple_host.jsonc
2025-10-08 18:22:56 INFO     [orchestrator]         Searching demo/ for *.py
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/my_workflow.py
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/simple_host.py
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/actual_workflow.py
2025-10-08 18:22:56 INFO     [orchestrator]           Found demo/custom_defs.py
2025-10-08 18:22:56 INFO     [orchestrator]       Loading python file demo/my_workflow.py as 'my_workflow'
2025-10-08 18:22:56 INFO     [orchestrator]       Loading python file demo/simple_host.py as 'simple_host'
2025-10-08 18:22:56 INFO     [orchestrator]       Loading python file demo/actual_workflow.py as 'actual_workflow'
2025-10-08 18:22:56 INFO     [orchestrator]       Loading python file demo/custom_defs.py as 'custom_defs'
2025-10-08 18:22:56 INFO     [orchestrator::register] Creation of universe
2025-10-08 18:22:56 INFO     [orchestrator::register] Creation of world
2025-10-08 18:22:56 INFO     [orchestrator::register] Hello world from my_workflow
2025-10-08 18:22:56 INFO     [orchestrator::register] <class 'custom_defs.MyAction'>
2025-10-08 18:22:56 INFO     [orchestrator]       Loading config file demo/custom_def_usage.json
2025-10-08 18:22:56 WARNING  [fib_seq_fixed]        Unused keys in config : ['unused_action_param']
2025-10-08 18:22:56 WARNING  [orchestrator]         Unused keys in config : ['unused_orch_param']
2025-10-08 18:22:56 INFO     [orchestrator]       Loading config file demo/simple_action.json
2025-10-08 18:22:56 INFO     [orchestrator]       Loading config file demo/resource_action.json
2025-10-08 18:22:56 INFO     [orchestrator]       Loading config file demo/hpc_host.json
2025-10-08 18:22:56 INFO     [example_pbs]          Adding homogeneous node resources for 'cpu'
2025-10-08 18:22:56 INFO     [orchestrator]       Loading config file demo/patches.json
2025-10-08 18:22:56 INFO     [orchestrator]       Loading config file demo/simple_host.jsonc
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch to Host 'unique_host_config'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch to Action 'fib_seq_fixed'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch to Action 'fib_seq_calc_mult'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch filter to Action 'action_090'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch filter to Action 'action_091'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch filter to Action 'action_092'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch filter to Action 'action_093'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch filter to Action 'action_094'
2025-10-08 18:22:56 INFO     [orchestrator::patch] Applying patch filter to Action 'action_095'
2025-10-08 18:22:56 WARNING  [orchestrator::patch] Unused keys in patch : ['unused_patch_param']
2025-10-08 18:22:56 INFO     [orchestrator]       No previous save file to load
2025-10-08 18:22:56 INFO     [orchestrator]       Running actions:
2025-10-08 18:22:56 INFO     [orchestrator]         action_000  
2025-10-08 18:22:56 INFO     [orchestrator]       and any necessary dependencies
2025-10-08 18:22:56 INFO     [orchestrator]       Full action set:
2025-10-08 18:22:56 INFO     [orchestrator]         action_000  
2025-10-08 18:22:56 INFO     [orchestrator]       Checking host "generic"
2025-10-08 18:22:56 INFO     [orchestrator]       Running as 'generic'
2025-10-08 18:22:56 INFO     [orchestrator]       Checking ability to run all actions on 'generic'...
2025-10-08 18:22:56 INFO     [orchestrator]         Checking environments...
2025-10-08 18:22:56 INFO     [orchestrator]         Checking resource availability...
2025-10-08 18:22:56 INFO     [orchestrator]       * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
2025-10-08 18:22:56 INFO     [orchestrator]       * * * * * * * * * *            All prerun checks for 'generic' passed           * * * * * * * * * * 
2025-10-08 18:22:56 INFO     [orchestrator]       * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
2025-10-08 18:22:56 INFO     [orchestrator]       Saving host information...
2025-10-08 18:22:56 INFO     [orchestrator]       Setting state of all inactive actions to pending
2025-10-08 18:22:56 INFO     [orchestrator]       No previous save file to load
2025-10-08 18:22:56 INFO     [orchestrator]       Using working directory : '/home/aislas/frameflow'
2025-10-08 18:22:56 INFO     [orchestrator]       Running actions...
2025-10-08 18:22:56 INFO     [orchestrator]       Running 'action_000' on 'generic'
2025-10-08 18:22:56 INFO     [action_000[thread_0]] Saving action information for launch...
2025-10-08 18:22:56 INFO     [action_000[thread_0]] Using working directory : '/home/aislas/frameflow'
2025-10-08 18:22:56 INFO     [action_000[thread_0]] Running command:
2025-10-08 18:22:56 INFO     [action_000[thread_0]]   /home/aislas/frameflow/sane/action_launcher.py /home/aislas/frameflow /home/aislas/frameflow/tmp/action_action_000.json
2025-10-08 18:22:56 INFO     [action_000[thread_0]] Command output will be captured to logfile /home/aislas/frameflow/log/action_000.log
2025-10-08 18:22:56 INFO     [orchestrator]       FINISHED Action 'action_000'             completed with 'success'
2025-10-08 18:22:56 INFO     [orchestrator]       Finished running queued actions
2025-10-08 18:22:56 INFO     [orchestrator]         action_000: success  
2025-10-08 18:22:56 INFO     [orchestrator]       All actions finished with success
2025-10-08 18:22:56 INFO     [orchestrator]       Save file at /home/aislas/frameflow/tmp/orchestrator.json
2025-10-08 18:22:56 INFO     [orchestrator]       JUnit file at /home/aislas/frameflow/log/results.xml
2025-10-08 18:22:56 INFO     [sane_runner]        Finished
```
> [!TIP]
> The above is generated from the `demo/` folder in the repository. It should
> provide a decent starting example of what a workflow may look like.
