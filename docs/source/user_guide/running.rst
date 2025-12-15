*****************
Running Workflows
*****************
.. py:module:: sane

As the primary goal is to spend more time running workflows than writing them,
this section is listed first. An example workflow is provided in the `source repo`_
in the `demo folder`_.


Runner
======
SANE workflows provides a single entry point for executing workflows: ``sane_runner``. 

This python executable facilitates the creation of an :py:class:`Orchestrator`, passing options and initializing the
orchestrator instance, then performing the user requested commands. All documentation moving forward will use
``sane_runner`` and runner interchangeably to refer to this entry point.

It is not *strictly necessary* to use the provided entry point, and one *could* directly use the :py:class:`Orchestrator`
however it is **highly recommended** that users first use ``sane_runner``, directly setting up their own orchestrator instance
only when the runner features are insufficient. 

The next sections assume the exclusive usage of the runner.

.. _running.paths:

Paths
=====
Running workflows always starts with listing the paths to your files. Without this information, it is impossible to know
what tasks are in your workflow. These are provided to the runner with the ``-p``/``--path`` option with multiple paths
able to be listed by using the option multiple times:

.. code:: console

  sane_runner -p workflow_path -p other_path ...<other options>


Once provided, these paths will be searched *in order* for all applicable files. Once found, these files are processed
as follows:

1. Python files loaded as modules
2. Execute all Python functions decorated with :py:func:`@sane.register <sane.register>` according to priority in descending order (highest priority first)
3. Read each JSON file, creating :py:class:`Hosts <Host>` and :py:class:`Actions <Action>` as necessary in that order, storing any patches
4. Execute all JSON patches found according to priority in descending order (highest priority first)

At the end of this processing a workflow is fully ready to use and **SHOULD NOT** be further modified by the user.

As an example, here is an excerpt from running the demo workflow found in the `source repo`_ with lines highlighting the
start of each of the above steps:

.. code-block:: ruby
   :linenos:
   :emphasize-lines: 17, 21, 25, 34

    sane_runner -p demo/ -a action_000 -r
    2025-11-18 12:36:19 INFO     [sane_runner]            Logging output to /home/aislas/frameflow/log/runner.log
    2025-11-18 12:36:19 INFO     [orchestrator]           Searching for workflow files...
    2025-11-18 12:36:19 INFO     [orchestrator]             Searching demo/ for *.json
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/custom_def_usage.json
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/simple_action.json
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/hpc_host.json
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/patches.json
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/resource_action.json
    2025-11-18 12:36:19 INFO     [orchestrator]             Searching demo/ for *.jsonc
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/simple_host.jsonc
    2025-11-18 12:36:19 INFO     [orchestrator]             Searching demo/ for *.py
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/my_workflow.py
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/simple_host.py
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/actual_workflow.py
    2025-11-18 12:36:19 INFO     [orchestrator]               Found demo/custom_defs.py
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading python file demo/my_workflow.py as 'my_workflow'
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading python file demo/simple_host.py as 'simple_host'
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading python file demo/actual_workflow.py as 'actual_workflow'
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading python file demo/custom_defs.py as 'custom_defs'
    2025-11-18 12:36:19 INFO     [orchestrator::register] Creation of universe
    2025-11-18 12:36:19 INFO     [orchestrator::register] Creation of world
    2025-11-18 12:36:19 INFO     [orchestrator::register] Hello world from my_workflow
    2025-11-18 12:36:19 INFO     [orchestrator::register] <class 'custom_defs.MyAction'>
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading config file demo/custom_def_usage.json
    2025-11-18 12:36:19 WARNING  [fib_seq_fixed]            Unused keys in config : ['unused_action_param']
    2025-11-18 12:36:19 WARNING  [orchestrator]             Unused keys in config : ['unused_orch_param']
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading config file demo/simple_action.json
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading config file demo/hpc_host.json
    2025-11-18 12:36:19 INFO     [example_pbs]              Adding homogeneous node resources for 'cpu'
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading config file demo/patches.json
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading config file demo/resource_action.json
    2025-11-18 12:36:19 INFO     [orchestrator]           Loading config file demo/simple_host.jsonc
    2025-11-18 12:36:19 INFO     [orchestrator::patch]    Processing patches from demo/patches.json
    2025-11-18 12:36:19 INFO     [orchestrator::patch]      Applying patch to Host 'unique_host_config'
    2025-11-18 12:36:19 INFO     [orchestrator::patch]      Applying patch to Action 'fib_seq_fixed'
    2025-11-18 12:36:19 INFO     [orchestrator::patch]      Applying patch to Action 'fib_seq_calc_mult'
    2025-11-18 12:36:19 INFO     [orchestrator::patch]      Applying patch filter 'action_09[0-5]' to [6] Actions
    2025-11-18 12:36:19 WARNING  [orchestrator::patch]      Unused keys in patch : ['unused_patch_param']


Selecting Actions
=================
Once paths have been supplied to the runner, users can select which actions to run or simply run the whole workflow. The
default is to find and run every action found, and thus the whole workflow.

The two options to control which actions to use are ``-a``/``--actions`` and ``-f``/``--filter``. These are mutually exclusive
and only one of these options may be used at a time.

The ``--actions`` option allows explicitly listing a series of actions, space-delimited, to be executed.
.. code::

   sane_runner -p demo -a action_000 action_001 ... action_099

The ``--filter`` option allows a single Python :py:mod:`re` regular expression (regex) filter to be used to select which actions
to be executed. There are no extra flags added to this regex (i.e. no case insensitive ``re.I``) and actions are included
if ``re.match( filter, action.id )`` is not ``None``.
.. code::

   sane_runner -p demo -f "^action_0[0-9]5"

The default is ``--filter ".*"``

Execution
=========
There are three main commands provided by the runner:

1. ``-r``/``--run``
2. ``-d``/``--dry-run``
3. ``-l``/``--list``

Like the ``--actions`` and ``--filter`` options for selection actions, the options for selecting commands are mutually
exclusive and only one may be used at a time. Each of these commands **always** operates on the set of selected actions.
This means that if you specify a small set of actions, such as ``-a action_000 action_001``, then use ``--list`` you will
only see these actions listed.

The ``--run`` command will fully run the selected actions and any dependencies of those actions as necessary. 

The ``--dry-run`` command will emulate the ``--run`` as best as possible, but all actions' ``launch()`` execution will be
stubbed and only echo what would have been run.

The ``--list`` command will just echo back out the selected actions. This can be helpful for inspecting what actions are
available in a workflow by not specifying any action selection.

Results
=======
The results of a workflow run are always written at the end of running actions, regardless of ``--run`` or ``--dry-run``.

These results are the aggregate results of the workflow run history, not just the current invocation. If a different subset
of actions was previously run from this workflow, the results of those actions will be accumulated with the current results.

Results are written in a JUnit XML file in the log directory:

.. code-block:: ruby
   :linenos:
   :emphasize-lines: 4

   ...
   2025-10-08 18:22:56 INFO     [orchestrator]       All actions finished with success
   2025-10-08 18:22:56 INFO     [orchestrator]       Save file at /home/aislas/sane_workflows/tmp/orchestrator.json
   2025-10-08 18:22:56 INFO     [orchestrator]       JUnit file at /home/aislas/sane_workflows/log/results.xml
   2025-10-08 18:22:56 INFO     [sane_runner]        Finished 

.. _running.saves:

Saves
=====
To prevent the re-running of actions that have already completed, SANE workflows record the workflow state alongside the
aggregate results. The default save location is ``./tmp``, but can be changed via the ``-sl``/``--save_location`` option.

Under this folder the primary save file, ``orchestrator.json``, is kept as well as the intermediary save state files for
actions and hosts. Users should generally avoid modifying any of the files in this directory.

To start a workflow from scratch and clear the saved info users can either remove the save location directory or use the
``-n``/``--new`` to not load the cache.

Advanced Usage
==============

.. _running.specific_host:

Specific Host
-------------
The ``-sh``/``--specific_host`` option allows users to select a host by name or alias instead of the default find method.

View Graph
----------
The ``-vg``/``--view_graph`` option will print out the action set and dependencies graph in a CLI-friendly manner.

The output of this graph can be read using the following legend:

====== =========== ===========
symbol meaning     description
====== =========== ===========
``•``  action      Represents a node in the DAG at this line
``┗➢`` dependency  The node at this line is dependent on the node ``•`` above this symbol
``|``  link        The node above this symbol is a dependency of nodes further down
``╌``  link        The dependencies to the left of this are required for the node at this line
``✧``  end         A node specifically requested to be printed, vs implicitly due to dependencies
====== =========== ===========

As an example, if ``sane_runner -p demo -l -a action_005 action_015 action_025`` is run and the output graph is:

.. code-block:: none
   :emphasize-lines: 7, 8

    Action Graph:
      • action_000
      │ • action_001
      │ │ • action_005 ✧
      │ │ • action_010
      │ │ │ • action_011
      ┗➢┺➢│╌│╌• action_015 ✧
          ┗➢┺➢• action_025 ✧

The following have no dependencies:

* ``action_000``
* ``action_001``
* ``action_005``
* ``action_010``
* ``action_011``

| Action ``action_015`` is dependent on ``action_000`` and ``action_001``.
| Action ``action_025`` is dependent on ``action_010`` and ``action_011``.

.. _running.verbose:

Verbose
-------
The ``-v``/``--verbose`` option forces actions' output to be echoed to the terminal in addition to the already
captured output in the actions' logfile.

Debug
-----
The ``-g``/``--debug_level`` option directly sets the Python `logging level`_. As such, the default is ``20``, corresponding
to normal ``INFO`` levels. Partial debug levels (between 10 and 20) are used within the code and thus can be used to increase
granularity.

Virtual Relaunch
----------------
The ``-vr``/``--virtual_relaunch`` option is a powerful option when paired with :py:class:`~resources.NonLocalProvider` hosts. By providing
a set of runtime resources at the command line, the user-requested action set is bundled and *"relaunched"* to the runner
under a single in situ action that has the resource requirements specified with this option.

A more concrete example of this usage would be an HPCHost that takes actions and submits each of them as a job to the host's
scheduler. Rather than have each action submitted as individual jobs, potentially leading to waiting in the scheduler queue
between action dependencies, we can launch the workflow itself as the job, forcing the actions to work within the new
resource constraints we supplied.

So instead of:

.. code:: none

   sane_runner -p demo -l -a action_005 action_015 action_025
   ...job status...
   Job ID          Username Queue    Jobname                  S ...
   --------------- -------- -------- ------------------------ - ...
   3582344.desche* aislas   cpu      sane.workflow.action_000 Q ...
   3582345.desche* aislas   cpu      sane.workflow.action_001 Q ...
   3582346.desche* aislas   cpu      sane.workflow.action_005 Q ...
   3582347.desche* aislas   cpu      sane.workflow.action_010 Q ...
   3582348.desche* aislas   cpu      sane.workflow.action_011 Q ...
   3582349.desche* aislas   cpu      sane.workflow.action_015 H ...
   3582350.desche* aislas   cpu      sane.workflow.action_025 H ...

We can do:

.. code:: none

   sane_runner -p demo -l -a action_005 action_015 action_025 -vr '{"cpus" : 20}'
   ...job status...
   Job ID          Username Queue    Jobname                        S ...
   --------------- -------- -------- ------------------------       - ...
   3582344.desche* aislas   cpu      sane.workflow.virtual_relaunch Q ...

Where the ``sane.workflow.virtual_relaunch`` job will run ``sane_runner -p demo -l -a action_005 action_015 action_025``

The benefit of this relaunch system, aside from the aggregation of actions, is that it allows us to generally group actions
but allow the host to inform us how that aggregation will look based on the resources specific to the host.
