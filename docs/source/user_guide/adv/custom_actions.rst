.. _advanced.custom_actions:
.. py:module:: sane
    :no-index:

Custom Actions
==============

This guide explains how to derive your own workflow actions from :py:class:`sane.Action`,
how to make them configurable from both Python and JSON, and how the SANE runtime executes them.

This material is intended to be a standalone advanced user guide. If you want
more introductory coverage of Python or JSON workflows, see the
:doc:`/tutorial/python` and :doc:`/tutorial/json` sections.

.. note::
    Users should *aim* to **never** directly manage or change :py:attr:`Action.state`,
    :py:attr:`Action.status`, or anything within the Action :ref:`action.internal`.
    These attributes and methods are provided for advanced usage far beyond normal
    custom workflow classes. If you find yourself using them beyond read-only,
    consider the design of your custom :py:class:`Action` and workflow.

.. warning::
    Users should **NEVER** try to manage host-managed resources or dependency completion
    & state. It is the responsibility of the :py:class:`Host` and :py:class:`Orchestrator`
    to guarantee the correctness of each, respectively.

Why derive :py:class:`sane.Action`?
-----------------------------------

Use a custom :py:class:`sane.Action` subclass when the default action behavior
is not enough for your workflow. In SANE, the default :py:meth:`~sane.Action.run`
executes a command from :py:attr:`~sane.Action.config` using
:py:meth:`~sane.Action.execute_subprocess`, but a custom class can instead:

* implement domain-specific logic in :py:meth:`~sane.Action.run`
* generate structured :py:attr:`~sane.Action.outputs`
* expose new top-level options through :py:meth:`~sane.options.OptionLoader.load_extra_options`
* manage more complex setup, resources usage, and host-specific information

A derived action is still a workflow object, so it must be added to the
:py:class:`sane.Orchestrator` to participate in the workflow.

Tyically Overriden Methods
--------------------------

For most custom :py:class:`Action` classes, the common extension points are those
listed under *Customizable Functions* in the Action :ref:`action.ui`:

* :py:meth:`~sane.Action.run`
* :py:meth:`~sane.Action.load_extra_options`
* :py:meth:`~sane.Action.pre_run`
* :py:meth:`~sane.Action.post_run`
* :py:meth:`~sane.Action.pre_launch`
* :py:meth:`~sane.Action.post_launch`


.. danger::
    Do not override :py:meth:`~sane.Action.launch`. It contains the workflow
    framework for subprocess execution, logging, state tracking, and :py:class:`Orchestrator`
    wake-up.

The typical pattern is:

#. Create a subclass of :py:class:`sane.Action`.
#. Add any custom attributes in :py:meth:`__init__`.
#. Override :py:meth:`~sane.Action.load_extra_options` to support custom JSON/Python options.
#. Override :py:meth:`~sane.Action.run` to perform your work.
#. Add an instance of the new Action type to the :py:class:`Orchestrator`.

Using Custom :py:class:`Action`
-------------------------------

The following example shows a minimal custom action that writes a message to
standard output multiple times.

.. code-block:: python

    import sane

    class RepeatMessageAction( sane.Action ):
      def __init__( self, id ):
        super().__init__( id )
        self.message = "Hello"
        self.count = 1

      def load_extra_options( self, options, origin ):
        self.message = options.pop( "message", self.message )
        self.count = options.pop( "count", self.count )
        super().load_extra_options( options, origin )

      def run( self ) -> int:
        for i in range( self.count ):
          self.log( f"[{self.id}] {self.message}" )
        self.outputs[ "lines_written" ] = self.count
        # This is the exit code of the subprocess
        return 0

Key things to note in the above example:

* ``RepeatMessageAction`` inherits from :py:class:`sane.Action`.
* ``load_extra_options`` consumes custom keys from the ``options`` dictionary.
* ``super().load_extra_options(options, origin)`` preserves the base class option loading behavior.
* ``run`` is the actual place where the action does work.
* ``self.outputs`` can be used to publish results for later dependencies.

Using a custom action from Python
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A custom action may be configured directly from Python without JSON. The workflow
merely needs to instantiate the class, call :py:meth:`~sane.options.OptionLoader.load_options`
or otherwise modify the instance, and add the action to the :py:class:`Orchestrator`.

.. code-block:: python

    import sane

    @sane.register
    def workflow( orch ):
      action = RepeatMessageAction( "repeat_message" )
      action.load_options(
        {
          "message" : "SANE is running custom actions",
          "count"   : 3
        }
      )
      orch.add_action( action )


Using a custom action from JSON
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Custom action subclasses can also be instantiated from JSON configuration.
SANE resolves the ``"type"`` field using :py:meth:`~sane.options.OptionLoader.search_type`:

.. code-block:: json

    {
      "actions":
      {
        "repeat_message":
        {
          "type"              : "my_project.actions.RepeatMessageAction",
          "environment"       : "gnu",
          "message"           : "custom action via json",
          "count"             : 4,
          "dependencies"      : { "prepare": "afterok" }
        }
      }
    }


Advanced runtime hooks
----------------------

SANE separates workflow launch-time behavior from subprocess runtime behavior.
Action execution is divided into two phases:

#. | :py:meth:`~sane.Action.pre_launch` / :py:meth:`~sane.Action.post_launch`
   | Per-action lifecycle methods executed in the orchestrator context 

  - called in the main process around :py:meth:`~sane.Action.launch`
  - useful for saving metadata or validating the action before the subprocess starts
  
#. | :py:meth:`~sane.Action.pre_run` / :py:meth:`~sane.Action.post_run`
   | Per-action execution methods executed in a separate subprocess context 

  - called inside the isolated action subprocess around :py:meth:`~sane.Action.run`
  - useful for Action-subprocess scoped work such as preparing a temporary workspace or post processing data outside the run method.


The following diagram illustrates the SANE workflow execution model.
A single host executes its runtime hook methods once per workflow, while
multiple actions each independently execute their runtime hook methods.

.. graphviz::


   digraph sane_workflow_lifecycle {
       rankdir=TB;
       node [shape=box, style=rounded];
       ranksep=.25;
       load    [label="Load Workflow JSON"];
       build   [label="Instantiate Hosts & Actions"];
       resolve [label="Resolve Dependency Graph"];

       hpre  [label="Host.pre_launch()"];
       hpost [label="Host.post_launch()"];

       load -> build -> resolve -> hpre;
       subgraph cluster_actions {
           labeljust="l"
           label="Per-Action Lifecycle\n(Parallel for Each Action)";
           style=dashed;

           subgraph cluster_action_a {
               labeljust="r"
               label="Action A Lifecycle";
               style=rounded;

               a_preL  [label="Action A: pre_launch()"];
               a_postL [label="Action A: post_launch()"];

               subgraph cluster_action_a_exec {
                   label="Execution Phase (Subprocess Context)";
                   style=dotted;
                   fontsize=10;

                   a_pre  [label="pre_run()"];
                   a_run  [label="run()"];
                   a_post [label="post_run()"];

                   a_pre -> a_run -> a_post;
               }

               a_preL -> a_pre;
               a_post -> a_postL;
           }

           subgraph cluster_action_b {
               labeljust="l"
               label="Action B Lifecycle";
               style=rounded;

               b_preL  [label="Action B: pre_launch()"];
               b_postL [label="Action B: post_launch()"];

               subgraph cluster_action_b_exec {
                   label="Execution Phase (Subprocess Context)";
                   style=dotted;
                   fontsize=10;

                   b_pre  [label="pre_run()"];
                   b_run  [label="run()"];
                   b_post [label="post_run()"];

                   b_pre -> b_run -> b_post;
               }

               b_preL -> b_pre;
               b_post -> b_postL;
           }
       }

       hpre -> a_preL;
       hpre -> b_preL;

       a_postL -> hpost;
       b_postL -> hpost;
   }

.. hint::
    The shared :py:class:`Action` mutex is held during ``*_launch()`` calls, so other
    running :py:class:`Action` objects will not interfere.

Execution phases and contexts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The workflow execution follows a defined lifecycle. Each action participates in
two phases:

**Orchestrator Phase** (main workflow process):
  The :py:class:`Orchestrator` calls :py:meth:`~sane.Action.pre_launch`, then spawns a new
  subprocess to execute the action, and finally calls :py:meth:`~sane.Action.post_launch`
  with the subprocess results. The :py:class:`Orchestrator` holds the action state
  and may manage multiple actions in parallel.

**Subprocess Phase** (isolated action process):
  The action subprocess calls :py:meth:`~sane.Action.pre_run`, then
  :py:meth:`~sane.Action.run`, and finally :py:meth:`~sane.Action.post_run`.
  The :py:class:`Environment` is already set up at this point, and the :py:class:`Action` has
  access to its own isolated runtime and environment variables.

Runtime Hook Examples
^^^^^^^^^^^^^^^^^^^^^

**pre_launch**
  Called before the action subprocess starts. Use this to:

  * Validate inputs or configuration before spending resources on execution
  * Prepare existing data files or temporary directories
  * Log metadata about the action


**Example: validation in pre_launch**

Here, ``pre_launch`` validates that required input files exist before the
subprocess is spawned:

.. code-block:: python

    class FileProcessorAction( sane.Action ):
      def __init__( self, id ):
        super().__init__( id )
        self.input_file = None

      def load_extra_options( self, options, origin ):
        self.input_file = options.pop( "input_file", self.input_file )
        super().load_extra_options( options, origin )

      def pre_launch( self ):
        """Validate input file exists before launching subprocess"""
        import os
        if self.input_file is None:
          self.log( "No input_file specified", level=40 )
          return False
        if not os.path.isfile( self.input_file ):
          self.log( f"Input file not found: {self.input_file}", level=40 )
          return False
        self.log( f"Input file validated: {self.input_file}", level=20 )
        return True

      def run( self ) -> int:
        # At this point, we know the file exists
        with open( self.input_file, 'r' ) as f:
          lines = len( f.readlines() )
        self.outputs[ "lines" ] = lines
        return 0


**post_launch**
  Called after the action subprocess finishes with the return code and captured
  output. Use this to:

  * Process or summarize action results further
  * Save intermediate outputs to shared storage
  * Clean up non-host-managed resources allocated in ``pre_launch``
  * Handle errors and decide whether to mark the action as success or failure beyond exit code from run

  Return ``False`` from ``post_launch`` to mark the action as failed.


**Example: result processing in post_launch**

Here, ``post_launch`` processes the subprocess output and saves a summary:

.. code-block:: python

    class TestAction( sane.Action ):
      def run( self ) -> int:
        # Use *_exec_raw() functions to allow subprocess STDOUT to be logged with
        # timestamps + context or if preferred just raw output
        self.push_exec_raw( False )
        # Run tests and capture stdout
        retval, content = self.execute_subprocess(
          "python", [ "-m", "pytest", "--tb=short", "tests/" ],
          capture=True,
          verbose=True
        )
        self.pop_exec_raw()
        self.outputs[ "test_output" ] = content
        return retval

      def post_launch( self, retval, content ):
        """Process test results and save summary"""
        if retval == 0:
          self.log( "All tests passed", level=20 )
          self.outputs[ "summary" ] = "PASS"
        else:
          self.log( "Some tests failed", level=40 )
          self.outputs[ "summary" ] = "FAIL"
          # You could write a report here beyond the simple XML/JSON/CLI reports SANE provides
        return True  # Mark action as success even on test failure



**pre_run**
  Called within the subprocess before :py:meth:`~sane.Action.run`. Use this to:

  * Set up the subprocess environment (e.g., create temp directories)
  * Source additional environment scripts
  * Validate the runtime environment

**post_run**
  Called within the subprocess after :py:meth:`~sane.Action.run` with the
  return code. Use this to:

  * Clean up temporary files created in ``pre_run``
  * Process output captured by ``run``
  * Log final results

**Example: environment setup in pre_run / post_run**

Here, ``pre_run`` sets up a temporary working directory within the subprocess -
note that these methods all execute in the same context one immediately after the other:

.. code-block:: python

    class ScratchWorkAction( sane.Action ):
      def pre_run( self ):
        """Create a temporary scratch directory for this action"""
        import tempfile
        import os
        # Assigning a new variable at this scope for run() is okay because
        # this is executing within the same process scope
        self.scratch = tempfile.mkdtemp( prefix=self.id )
        self.log( f"Created scratch directory: {self.scratch}" )

      def run( self ) -> int:
        # self.scratch was setup in pre_run()
        work_file = os.path.join( self.scratch, "intermediate.txt" )
        # Use scratch directory for temp work
        with open( work_file, 'w' ) as f:
          f.write( "intermediate results" )
        self.outputs[ "work_file" ] = work_file
        return 0

      def post_run( self, retval ):
        """Clean up the scratch directory"""
        import shutil
        import os
        if hasattr( self, "scratch" ) and os.path.isdir( self.scratch ):
          shutil.rmtree( self.scratch )
          self.log( f"Cleaned up scratch directory: {self.scratch}" )


Dependency and output access
----------------------------

At runtime, the :py:class:`Action` dependencies are available through the
:py:attr:`~sane.Action.dependencies` property. Each dependency entry contains the
parent Action's :py:meth:`~sane.Action.info`.

This is useful when implementing Actions that consume the results of prior
steps. The default dereferencing syntax also supports expressions such as:

* ``${{ dependencies.prepare.outputs.some_file }}``
* ``${{ dependencies.prepare.config.foo }}``

This can be extremely useful when chaining custom :py:class:`Action` classes together
to consume the values of predecessors.

.. important::
    Any changes that you make to the :py:class:`Action` object within any of the
    ``*run()`` methods *will not* be visible in the main process (and thus not propagate
    as dependency :py:meth:`~sane.Action.info` or ``post_launch()``) **EXCEPT**
    :py:attr:`Action.outputs`.

    The :py:attr:`Action.outputs` attribute is serialized right after :py:meth:`Action.post_run()`
    and read back in on :py:class:`Action` completion.


Summary
-------
A custom :py:class:`sane.Action` subclass gives you the most flexible way to add
workflow-specific behavior to your SANE workflow. Use the action hooks for runtime control,
load extra options to support JSON and Python inputs, and keep in mind when & where
a particular method executes during the workflow.

* Override :py:meth:`~sane.Action.run` for custom work, and **NEVER** modify :py:meth:`~sane.Action.launch`
* Use :py:attr:`~sane.Action.outputs` to publish results for later actions.
* Use ``*_launch()`` methods for context in the main process
* Use ``*_run()`` methods for context in the :py:meth:`Action.run()` subprocess
* Extend JSON interface with your custom class by using :py:meth:`~sane.Action.load_extra_options`.
* Use :py:meth:`~sane.Action.execute_subprocess` instead of raw subprocess calls if you want SANE logging integration.

Remember - for simple command-based actions, the inherited default :py:meth:`~sane.Action.run`
may be sufficient with ``config["command"]`` and ``config["arguments"]``.


.. toctree::
    :maxdepth: 2
