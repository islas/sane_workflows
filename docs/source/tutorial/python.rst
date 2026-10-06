Python Interfacing
==================
.. |alt_doc| replace:: :doc:`json`
.. include:: common/primer.rst

Preface
-------
The python interface of SANE workflows offers a well documented
API with type hints if your development environment supports it.

Starting within the python interface opens up a world of possibilities
in complex workflow design, but we shall keep it simple for now
until the later :ref:`advanced` topics.

.. attention:: Before we begin, it is **important** to understand that to get the
               :py:class:`Orchestrator` to interact with our python code, we should
               use :py:func:`@sane.register <sane.register>` `decorator`_.

               If you are unfamiliar with `decorators <decorator>`_, that is okay -
               it is not critically necessary to understand them make use of SANE.

Orchestrator
------------
We should only use the the :py:class:`Orchestrator` :ref:`orch.ui` to interact with
the instance we are handed in by the :py:func:`@sane.register <sane.register>` decorator.

The same advice of using the *User Interface* generally goes for all classes,
but especially the :py:class:`Orchestrator`.

.. hint:: We only need :py:func:`@sane.register <sane.register>` on the calls
          that we want the :py:class:`Orchestrator` to directly call. Any other
          helper functions or classes we need can be written normally.


Let's take a look at the :deco:`sane.register` to see how to use it.

.. collapse:: Quick Reference (click to open/close)

  .. autodecorator:: sane.register
      :no-index:

|

As we can see, our main interaction with SANE will be via functions
with this ``@sane.register`` syntax above the function itself, where
the function takes a single required positional argument (this will be
the :py:class:`Orchestrator`)

.. code-block:: python
    :emphasize-lines: 3

    import sane

    @sane.register
    def workflow( orch ):
      # hmmm.. what now..?

Hosts
-----
To begin our workflow, let's create the ``.sane/mango/hosts/forest.py``
file and make a host in this file.

.. code-block:: none
    :emphasize-lines: 4

    .sane/
    └── mango
        └── hosts
            └── forest.py

We will start by creating a :py:class:`Host` object and adding it to the :py:class:`Orchestrator`.

.. code-block:: python
    :caption: ``.sane/mango/hosts/forest.py``

    import sane

    @sane.register
    def create_forest_host( orch ):
      forest = sane.Host( "forest" )
      orch.add_host( forest )

.. important:: For objects to show up in the workflow you **MUST** add them to the
               :py:class:`Orchestrator` instance provided (``orch``). Otherwise,
               your function will just create an object and "leave" it there doing
               nothing after returning from the function call.
               
               You can add to the ``orch`` at any time, before or after configuring
               your :py:class:`Host` or :py:class:`Action`, but the object must
               be added eventually. **It is recommended to add your object just after
               creation so that any internal logic (i.e. logging) can be setup immediately.**

As far as creating a host we are basically done... Well, not really. It is a valid
host, but it does not provided much. Additionally, when running a workflow, the
expectation is that any :py:class:`Action` will always run in an :py:class:`Environment`,
even if one is not needed. Thus, hosts must provide at least one :py:class:`Environment`
to even be somewhat useful.

Let's continue to flesh out this :py:class:`Host`.

If you click on the class name you will be taken to the API reference documentation,
or alternatively click this :py:class:`Host` :ref:`host.ui` link to see the API
calls we care about. There are quite a few, so to start simple we will focus on
:py:meth:`Host.add_resources` and :py:meth:`Host.add_environment`.

Resources & Environments
^^^^^^^^^^^^^^^^^^^^^^^^
Take a quick look at the API documentation for :py:meth:`Host.add_resources`:

.. collapse:: Quick Reference (click to open/close):

  .. automethod:: sane.Host.add_resources
      :no-index:

  .. autoclass:: sane.resources.Resource
      :no-index:
      :special-members:

|

.. include:: common/host_res.rst

.. code-block:: python
    :caption: ``.sane/mango/hosts/forest.py``
    :emphasize-lines: 8

    import sane

    @sane.register
    def create_forest_host( orch ):
      forest = sane.Host( "forest" )
      orch.add_host( forest )

      forest.add_resources( { "trees" : 12 } )

Next, we need an :py:class:`Environment` to work with. 

.. important:: Currently, actions *ALWAYS* need to run with an :py:class:`Environment` set up.
               Therefore, hosts **must** have at least one :py:class:`Environment` declared
               that isn't the :py:attr:`~Host.base_env`

If we look at the :py:class:`Environment` :ref:`env.ui` we can see what function
calls are available to use.

.. collapse:: Quick Reference (click to open/close)

  .. automethod:: Host.add_environment
      :no-index:

  .. automethod:: Environment.setup_env_vars
      :no-index:

|

.. include:: common/env_var_demo.rst

Once again, keeping things simple, we will focus only on the necessary functions
to get this workflow going. We will be using the :py:meth:`Environment.setup_env_vars`
method, then after :py:meth:`Host.add_environment`.

Our final file setup should look something like so:

.. literalinclude:: ../../examples/mango/python_basic_host/.sane/mango/hosts/forest.py
    :caption: ``.sane/mango/hosts/forest.py``
    :language: python
    :name: forest.py

.. include:: common/host_uneventful.rst

.. code-block:: none
   :emphasize-lines: 9, 11

    sane workflow -p .sane/ -sh forest -n -v -r

    2026-10-02 12:28:19 INFO     [sane]                   Logging output to /home/aislas/mango/python_basic_host/log/runner.log
    2026-10-02 12:28:19 INFO     [orchestrator]           Searching for workflow files...
    2026-10-02 12:28:19 INFO     [orchestrator]             Searching .sane/ for *.json
    2026-10-02 12:28:19 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2026-10-02 12:28:19 INFO     [orchestrator]             Searching .sane/ for *.py
    2026-10-02 12:28:19 INFO     [orchestrator]               Found .sane/mango/hosts/forest.py
    2026-10-02 12:28:19 INFO     [orchestrator]           Loading python file .sane/mango/hosts/forest.py as 'mango.hosts.forest'
    2026-10-02 12:28:19 INFO     [sane]                   Using action filter '.*'
    2026-10-02 12:28:19 INFO     [sane]                   No actions selected
    usage: sane workflow [-h] [-p PATH] [-w WORKING_DIR] [-s SEARCH_PATTERN]
                         [-a ACTIONS [ACTIONS ...]] [-f FILTER] [-r | -l | -d]
                         [-sh SPECIFIC_HOST] [-sl SAVE_LOCATION]
                         [-ll LOG_LOCATION] [-v] [-g [DEBUG_LEVEL]] [-vg] [-fl]
                         [-m MODE] [-n] [--patch PATCH] [-vr VIRTUAL_RELAUNCH]
                         [-ml MAIN_LOG] [-vh VIRTUAL_HOST]
    ...remaining help omitted...

.. tip:: This output can be reproduced by using the source repo example found at
         ``docs/examples/mango/python_basic_host/.sane``

The default search patterns found our file and loaded it, but nothing was done since
no actions were found.

Actions
-------
Let's now try to create our first python-based :py:class:`Action`!

We will create the ``.sane/mango/actions/grow.py`` file, as well as create a helper
script at ``.sane/mango/scripts/grow.sh``:

.. code-block:: none
    :emphasize-lines: 4, 8

    .sane/
    └── mango
        ├── actions
        │   └── grow.py
        ├── hosts
        │   └── forest.py
        └── scripts
            └── grow.sh

We will start by creating our ``.sane/mango/actions/grow.py`` file:

.. code-block:: python
    :caption: ``.sane/mango/actions/grow.py``

    import sane

    @sane.register
    def create_grow_action( orch ):
      grow = sane.Action( "grow_action" )
      orch.add_action( grow )

      #...


Similar to the :py:class:`Host` creation, take a look at the :py:class:`Action`
:ref:`action.ui` to get an idea of the API available to use. Most important
to us will be:

* :py:attr:`~Action.config` (``config["command"]`` and ``config["arguments"]`` since we are using the default :py:meth:`Action.run`)
* :py:attr:`~Action.environment`
* :py:meth:`~Action.add_dependencies`
* :py:meth:`~Action.add_resource_requirements`

We shall go over the relevance of each of these.

:py:attr:`~Action.config`
^^^^^^^^^^^^^^^^^^^^^^^^^
.. include:: common/act_config.rst

Let's quickly modify our ``.sane/mango/actions/grow.py``:

.. code-block:: python
    :caption: ``.sane/mango/actions/grow.py``

    import sane

    @sane.register
    def create_grow_action( orch ):
      grow = sane.Action( "grow_action" )
      orch.add_action( grow )

      grow.config["command"]   = ".sane/mango/scripts/grow.sh"
      grow.config["arguments"] = [ 4 ] # this must be a list

As for the contents of ``.sane/mango/scripts/grow.sh`` let's use:

.. literalinclude:: ../../examples/mango/python_grow_action/.sane/mango/scripts/grow.sh
    :caption: ``.sane/mango/scripts/grow.sh``
    :language: bash

.. include:: common/act_admon_cmd.rst

:py:attr:`~Action.environment`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. include:: common/act_env.rst

Let's update our ``.sane/mango/actions/grow.py`` again, saying we need a ``"valley"``
environment (recall `forest.py`_):

.. code-block:: python
    :caption: ``.sane/mango/actions/grow.py``

    import sane

    @sane.register
    def create_grow_action( orch ):
      grow = sane.Action( "grow_action" )
      orch.add_action( grow )

      grow.config["command"]   = ".sane/mango/scripts/grow.sh"
      grow.config["arguments"] = [ 4 ] # this must be a list

      grow.environment = "valley"

:py:meth:`~Action.add_resource_requirements`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. collapse:: Quick Reference (click to open/close)

  .. automethod:: Action.add_resource_requirements
      :no-index:

|

.. include:: common/act_res.rst

To grow our *mangos* we will need ``"trees"`` (recall `forest.py`_):

.. literalinclude:: ../../examples/mango/python_grow_action/.sane/mango/actions/grow.py
    :language: python
    :caption: ``.sane/mango/actions/grow.py``

:py:meth:`~Action.add_dependencies`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is the first :py:class:`Action` in our workflow, so it will not have any
dependencies. See the :ref:`python.adding_deps` for details on adding dependencies.

Final :py:class:`Action` Result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Our final ``.sane/mango/actions/grow.py`` should now look like:

.. literalinclude:: ../../examples/mango/python_grow_action/.sane/mango/actions/grow.py
    :language: python
    :caption: ``.sane/mango/actions/grow.py``
    :name: grow.py


Running
-------

Now that we have everything set up, we should be able to run. We will be using the
following *optional* flags:

* ``-sh`` :ref:`running.specific_host` option to ensure our host is selected
* ``-n`` :ref:`New Run <running.saves>` option to always rerun our workflow entirely
* ``-v``  :ref:`running.verbose` option to get full output in one location rather than split amongst multiple files

.. code-block:: none
   :emphasize-lines: 10, 11, 33, 43, 44, 45, 47, 49, 50, 51, 52, 53, 54, 62, 63, 64

    sane workflow -p .sane/ -sh forest -n -v -r

    2026-10-02 12:28:19 INFO     [sane]                   Logging output to /home/aislas/mango/python_grow_action/log/runner.log
    2026-10-02 12:28:19 INFO     [orchestrator]           Searching for workflow files...
    2026-10-02 12:28:19 INFO     [orchestrator]             Searching .sane/ for *.json
    2026-10-02 12:28:19 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2026-10-02 12:28:19 INFO     [orchestrator]             Searching .sane/ for *.py
    2026-10-02 12:28:19 INFO     [orchestrator]               Found .sane/mango/actions/grow.py
    2026-10-02 12:28:19 INFO     [orchestrator]               Found .sane/mango/hosts/forest.py
    2026-10-02 12:28:19 INFO     [orchestrator]           Loading python file .sane/mango/actions/grow.py as 'mango.actions.grow'
    2026-10-02 12:28:19 INFO     [orchestrator]           Loading python file .sane/mango/hosts/forest.py as 'mango.hosts.forest'
    2026-10-02 12:28:19 INFO     [sane]                   Using action filter '.*'
    2026-10-02 12:28:19 INFO     [sane]                     Found [1] Actions
    2026-10-02 12:28:19 INFO     [orchestrator]           No previous save file to load
    2026-10-02 12:28:19 INFO     [orchestrator]           Requested actions:
    2026-10-02 12:28:19 INFO     [orchestrator]             grow_action
    2026-10-02 12:28:19 INFO     [orchestrator]           and any necessary dependencies
    2026-10-02 12:28:19 INFO     [orchestrator]           Full action set:
    2026-10-02 12:28:19 INFO     [orchestrator]             grow_action
    2026-10-02 12:28:19 INFO     [orchestrator]           Checking host "forest"
    2026-10-02 12:28:19 INFO     [orchestrator]           Running as 'forest'
    2026-10-02 12:28:19 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2026-10-02 12:28:19 INFO     [orchestrator]             Checking environments...
    2026-10-02 12:28:19 INFO     [orchestrator]             Checking resource availability...
    2026-10-02 12:28:19 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
    2026-10-02 12:28:19 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * *
    2026-10-02 12:28:19 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
    2026-10-02 12:28:19 INFO     [orchestrator]           Saving host information...
    2026-10-02 12:28:19 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2026-10-02 12:28:19 INFO     [orchestrator]           No previous save file to load
    2026-10-02 12:28:19 INFO     [orchestrator]           Using working directory : '/home/aislas/mango/python_grow_action'
    2026-10-02 12:28:19 INFO     [orchestrator]           Running actions...
    2026-10-02 12:28:19 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2026-10-02 12:28:19 INFO     [orchestrator]           ...IDLE... Listening for next wake event
    2026-10-02 12:28:19 INFO     [thread_0]  [grow_action::launch]      Action logfile captured at /home/aislas/mango/python_grow_action/log/grow_action.log
    2026-10-02 12:28:19 INFO     [thread_0]  [grow_action::launch]      Saving action information for launch...
    2026-10-02 12:28:19 INFO     [thread_0]  [grow_action::launch]        Save complete
    2026-10-02 12:28:19 INFO     [thread_0]  [grow_action::launch]      Using working directory : '/home/aislas/mango/python_grow_action'
    2026-10-02 12:28:19 INFO     [thread_0]  [grow_action::launch]      Running command:
    2026-10-02 12:28:19 INFO     [thread_0]  [grow_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango/python_grow_action /home/aislas/mango/python_grow_action/tmp/action_grow_action.json
    2026-10-02 12:28:19 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
    2026-10-02 12:28:19 INFO     [grow_action::launch]    Current directory: /home/aislas/mango/python_grow_action
    2026-10-02 12:28:19 INFO     [grow_action::launch]    Loaded Action "grow_action"
    2026-10-02 12:28:19 INFO     [grow_action::launch]    Loaded Host "forest"
    2026-10-02 12:28:19 INFO     [grow_action::launch]    Using Environment "valley"
    2026-10-02 12:28:19 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2026-10-02 12:28:19 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2026-10-02 12:28:19 INFO     [grow_action::run]       Running command:
    2026-10-02 12:28:19 INFO     [grow_action::run]         .sane/mango/scripts/grow.sh 4
    2026-10-02 12:28:19 STDOUT   [grow_action::run]       Growing with 4 trees with 85% growth rate...
    2026-10-02 12:28:19 STDOUT   [grow_action::run]         Tree 1 grew 5 mangos!
    2026-10-02 12:28:19 STDOUT   [grow_action::run]         Tree 2 grew 1 mangos!
    2026-10-02 12:28:19 STDOUT   [grow_action::run]         Tree 3 grew 6 mangos!
    2026-10-02 12:28:19 STDOUT   [grow_action::run]         Tree 4 grew 1 mangos!
    2026-10-02 12:28:19 INFO     [grow_action::launch]    Saving outputs to : /home/aislas/mango/python_grow_action/tmp/grow_action_outputs.json
    2026-10-02 12:28:19 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
    2026-10-02 12:28:20 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2026-10-02 12:28:20 INFO     [orchestrator]           Finished running queued actions
    2026-10-02 12:28:20 INFO     [orchestrator]             grow_action: success
    2026-10-02 12:28:20 INFO     [orchestrator]           All actions finished with success
    2026-10-02 12:28:20 INFO     [orchestrator]           Finished in 0:00:00.300554
    2026-10-02 12:28:20 INFO     [orchestrator]           Logfiles at /home/aislas/mango/python_grow_action/log
    2026-10-02 12:28:20 INFO     [orchestrator]           Save file at /home/aislas/mango/python_grow_action/tmp/orchestrator.json
    2026-10-02 12:28:20 INFO     [orchestrator]           JUnit file at /home/aislas/mango/python_grow_action/log/results.xml
    2026-10-02 12:28:20 INFO     [sane]                   Finished

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/python_grow_action/.sane/``

A quick walkthrough of the above output, focusing on the highlighted regions:

1. The :py:class:`Orchestrator` finds and loads our python files
2. The :py:class:`Orchestrator`, after verifying the selected :py:class:`Host`, runs our :py:class:`Action` on the host
3. During execution inside our :py:class:`Action` (``action_launcher.py``):
    a. The :py:class:`Action` loading itself and the :py:class:`Host`
    b. Sets up the :py:class:`Environment`
    c. Calls our ``config["command"]`` with ``config["arguments"]``
    d. Outputs the command output with log tag ``STDOUT`` (stderr also goes here)
4. Final logs and results information is left at the bottom for our convenience

Special notes:

* Everything betwwen ``***...Inside action_launcher.py...***`` and ``***...Finished action_launcher.py...***`` for
  a respective :py:class:`Action` is actually the direct output of the :py:meth:`Action.run`
* (3.a) occurs because the ``action_launcher.py`` (:py:meth:`Action.run`) occurs in a totally separate
  subprocess
* (3.d) captures all command output (stdout and stderr)

Extending the workflow
----------------------
Now that we have a basis for creating our workflow, let's harvest our *mangos*.
We will be adding a ``.sane/mango/actions/harvest.py`` file and supporting 
``.sane/mango/scripts/harvest.sh`` script:

.. code-block:: none
    :emphasize-lines: 5, 10

    .sane/
    └── mango
        ├── actions
        │   ├── grow.py
        │   └── harvest.py
        ├── hosts
        │   └── forest.py
        └── scripts
            ├── grow.sh
            └── harvest.sh

.. _python.adding_deps:

Adding :py:attr:`Action.dependencies`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. collapse:: Quick Reference (click to open/close)

  .. automethod:: Action.add_dependencies
      :no-index:

|

.. include:: common/act_dep.rst

If we were to add depedencies to an :py:class:`Action`, we could do it in one of
three ways, using :py:class:`DependencyType`:

.. collapse:: Quick Reference (click to open/close)

  .. autoclass:: DependencyType
      :no-index:
      :members:
      :exclude-members: __new__
      :member-order: bysource

|

Assuming the following functional basis:

.. code-block:: python
    :caption: Example Python dependency base

    import sane

    @sane.register
    def foo( orch )
      a = sane.Action( "a" )
      b = sane.Action( "b" )
      c = sane.Action( "c" )
      d = sane.Action( "d" )
      orch.add_action( a )
      orch.add_action( b )
      orch.add_action( c )
      orch.add_action( d )

This method relies on default assignment of :py:attr:`DependencyType.AFTEROK`:
  .. code-block:: python
      :caption: Example Python dependency using *only* :py:attr:`Action.id`

      # ...python file excerpt...
      b.add_dependencies( "a" )
      d.add_dependencies( "b", "c" )

This method relies on the string values of :py:class:`DependencyType`:
  .. code-block:: python
      :caption: Example Python dependency using (:py:attr:`Action.id` : ``str``) tuple

      # ...python file excerpt...
      b.add_dependencies( ( "a", "afterok" ) )
      d.add_dependencies( ( "b", "afterok" ), ( "c", "afternotok" ) )

This method relies on the enum values of :py:class:`DependencyType`:
  .. code-block:: python
      :caption: Example Python dependency using (:py:attr:`Action.id` : :py:class:`DependencyType`) tuple

      # ...python file excerpt...
      b.add_dependencies( ( "a", sane.DependencyType.AFTEROK ) )
      d.add_dependencies( ( "b", sane.DependencyType.AFTEROK ), ( "c", sane.DependencyType.AFTERNOTOK ) )

These methods are intermixable, even with the same call:

  .. code-block:: python
      :caption: Example Python dependency using all methods

      # ...python file excerpt...
      b.add_dependencies( "a" )
      d.add_dependencies( "a", ( "b", "afternotok" ), ( "c", sane.DependencyType.AFTERNOTOK ) )

New files
^^^^^^^^^
We can model the new ``"harvest_action"`` after the `grow.py`_ example, but change a few things
such as the script we will run and adding a dependency to our initial ``"grow_action"``:

.. literalinclude:: ../../examples/mango/python_harvest_action/.sane/mango/actions/harvest.py
    :language: python
    :caption: ``.sane/mango/actions/harvest.py``
    :name: harvest.py
    :emphasize-lines: 8, 14

And our helper script as:

.. literalinclude:: ../../examples/mango/python_harvest_action/.sane/mango/scripts/harvest.sh
    :language: bash
    :caption: ``.sane/mango/scripts/harvest.sh``
    :name: harvest.sh

Note that we listed the dependencies using the :py:attr:`Action.id` string value,
and not the :py:class:`Action` object created in `grow.py`_ directly.

.. include:: common/harvest_dep_caveat.rst

Let's run with new action:

.. code-block:: none
   :emphasize-lines: 60, 76, 77, 78

    sane workflow -p .sane/ -sh forest -n -v -r

    2026-10-02 12:28:20 INFO     [sane]                   Logging output to /home/aislas/mango/python_harvest_action/log/runner.log
    2026-10-02 12:28:20 INFO     [orchestrator]           Searching for workflow files...
    2026-10-02 12:28:20 INFO     [orchestrator]             Searching .sane/ for *.json
    2026-10-02 12:28:20 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2026-10-02 12:28:20 INFO     [orchestrator]             Searching .sane/ for *.py
    2026-10-02 12:28:20 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
    2026-10-02 12:28:20 INFO     [orchestrator]               Found .sane/mango/actions/grow.py
    2026-10-02 12:28:20 INFO     [orchestrator]               Found .sane/mango/hosts/forest.py
    2026-10-02 12:28:20 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
    2026-10-02 12:28:20 INFO     [orchestrator]           Loading python file .sane/mango/actions/grow.py as 'mango.actions.grow'
    2026-10-02 12:28:20 INFO     [orchestrator]           Loading python file .sane/mango/hosts/forest.py as 'mango.hosts.forest'
    2026-10-02 12:28:20 INFO     [sane]                   Using action filter '.*'
    2026-10-02 12:28:20 INFO     [sane]                     Found [2] Actions
    2026-10-02 12:28:20 INFO     [orchestrator]           No previous save file to load
    2026-10-02 12:28:20 INFO     [orchestrator]           Requested actions:
    2026-10-02 12:28:20 INFO     [orchestrator]             grow_action     harvest_action
    2026-10-02 12:28:20 INFO     [orchestrator]           and any necessary dependencies
    2026-10-02 12:28:20 INFO     [orchestrator]           Full action set:
    2026-10-02 12:28:20 INFO     [orchestrator]             grow_action     harvest_action
    2026-10-02 12:28:20 INFO     [orchestrator]           Checking host "forest"
    2026-10-02 12:28:20 INFO     [orchestrator]           Running as 'forest'
    2026-10-02 12:28:20 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2026-10-02 12:28:20 INFO     [orchestrator]             Checking environments...
    2026-10-02 12:28:20 INFO     [orchestrator]             Checking resource availability...
    2026-10-02 12:28:20 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
    2026-10-02 12:28:20 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * *
    2026-10-02 12:28:20 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
    2026-10-02 12:28:20 INFO     [orchestrator]           Saving host information...
    2026-10-02 12:28:20 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2026-10-02 12:28:20 INFO     [orchestrator]           No previous save file to load
    2026-10-02 12:28:20 INFO     [orchestrator]           Using working directory : '/home/aislas/mango/python_harvest_action'
    2026-10-02 12:28:20 INFO     [orchestrator]           Running actions...
    2026-10-02 12:28:20 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2026-10-02 12:28:20 INFO     [orchestrator]           ...IDLE... Listening for next wake event
    2026-10-02 12:28:20 INFO     [thread_0]  [grow_action::launch]         Action logfile captured at /home/aislas/mango/python_harvest_action/log/grow_action.log
    2026-10-02 12:28:20 INFO     [thread_0]  [grow_action::launch]         Saving action information for launch...
    2026-10-02 12:28:20 INFO     [thread_0]  [grow_action::launch]           Save complete
    2026-10-02 12:28:20 INFO     [thread_0]  [grow_action::launch]         Using working directory : '/home/aislas/mango/python_harvest_action'
    2026-10-02 12:28:20 INFO     [thread_0]  [grow_action::launch]         Running command:
    2026-10-02 12:28:20 INFO     [thread_0]  [grow_action::launch]           /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango/python_harvest_action /home/aislas/mango/python_harvest_action/tmp/action_grow_action.json
    2026-10-02 12:28:20 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
    2026-10-02 12:28:20 INFO     [grow_action::launch]    Current directory: /home/aislas/mango/python_harvest_action
    2026-10-02 12:28:20 INFO     [grow_action::launch]    Loaded Action "grow_action"
    2026-10-02 12:28:20 INFO     [grow_action::launch]    Loaded Host "forest"
    2026-10-02 12:28:20 INFO     [grow_action::launch]    Using Environment "valley"
    2026-10-02 12:28:20 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2026-10-02 12:28:20 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2026-10-02 12:28:20 INFO     [grow_action::run]       Running command:
    2026-10-02 12:28:20 INFO     [grow_action::run]         .sane/mango/scripts/grow.sh 4
    2026-10-02 12:28:20 STDOUT   [grow_action::run]       Growing with 4 trees with 85% growth rate...
    2026-10-02 12:28:20 STDOUT   [grow_action::run]         Tree 1 grew 7 mangos!
    2026-10-02 12:28:20 STDOUT   [grow_action::run]         Tree 2 grew 2 mangos!
    2026-10-02 12:28:20 STDOUT   [grow_action::run]         Tree 3 grew 6 mangos!
    2026-10-02 12:28:20 STDOUT   [grow_action::run]         Tree 4 grew 1 mangos!
    2026-10-02 12:28:20 INFO     [grow_action::launch]    Saving outputs to : /home/aislas/mango/python_harvest_action/tmp/grow_action_outputs.json
    2026-10-02 12:28:20 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
    2026-10-02 12:28:20 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2026-10-02 12:28:20 INFO     [orchestrator]           Running 'harvest_action' on 'forest'
    2026-10-02 12:28:20 INFO     [orchestrator]           ...IDLE... Listening for next wake event
    2026-10-02 12:28:20 INFO     [thread_0]  [harvest_action::launch]      Action logfile captured at /home/aislas/mango/python_harvest_action/log/harvest_action.log
    2026-10-02 12:28:20 INFO     [thread_0]  [harvest_action::launch]      Saving action information for launch...
    2026-10-02 12:28:20 INFO     [thread_0]  [harvest_action::launch]        Save complete
    2026-10-02 12:28:20 INFO     [thread_0]  [harvest_action::launch]      Using working directory : '/home/aislas/mango/python_harvest_action'
    2026-10-02 12:28:20 INFO     [thread_0]  [harvest_action::launch]      Running command:
    2026-10-02 12:28:20 INFO     [thread_0]  [harvest_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango/python_harvest_action /home/aislas/mango/python_harvest_action/tmp/action_harvest_action.json
    2026-10-02 12:28:20 INFO     [harvest_action::launch] ***************Inside action_launcher.py***************
    2026-10-02 12:28:20 INFO     [harvest_action::launch] Current directory: /home/aislas/mango/python_harvest_action
    2026-10-02 12:28:20 INFO     [harvest_action::launch] Loaded Action "harvest_action"
    2026-10-02 12:28:20 INFO     [harvest_action::launch] Loaded Host "forest"
    2026-10-02 12:28:20 INFO     [harvest_action::launch] Using Environment "valley"
    2026-10-02 12:28:20 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2026-10-02 12:28:20 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2026-10-02 12:28:20 INFO     [harvest_action::run]    Running command:
    2026-10-02 12:28:20 INFO     [harvest_action::run]      .sane/mango/scripts/harvest.sh
    2026-10-02 12:28:20 STDOUT   [harvest_action::run]    Harvesting mangos...
    2026-10-02 12:28:20 STDOUT   [harvest_action::run]    Collected : 16
    2026-10-02 12:28:20 INFO     [harvest_action::launch] Saving outputs to : /home/aislas/mango/python_harvest_action/tmp/harvest_action_outputs.json
    2026-10-02 12:28:20 INFO     [harvest_action::launch] ***************Finished action_launcher.py***************
    2026-10-02 12:28:20 INFO     [orchestrator]           [FINISHED] ** Action 'harvest_action'         completed with 'success'
    2026-10-02 12:28:20 INFO     [orchestrator]           Finished running queued actions
    2026-10-02 12:28:20 INFO     [orchestrator]             grow_action   : success  harvest_action: success
    2026-10-02 12:28:20 INFO     [orchestrator]           All actions finished with success
    2026-10-02 12:28:20 INFO     [orchestrator]           Finished in 0:00:00.427453
    2026-10-02 12:28:20 INFO     [orchestrator]           Logfiles at /home/aislas/mango/python_harvest_action/log
    2026-10-02 12:28:20 INFO     [orchestrator]           Save file at /home/aislas/mango/python_harvest_action/tmp/orchestrator.json
    2026-10-02 12:28:20 INFO     [orchestrator]           JUnit file at /home/aislas/mango/python_harvest_action/log/results.xml
    2026-10-02 12:28:20 INFO     [sane]                   Finished

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/python_harvest_action/.sane/``

Again, reviewing the highlighted regions:

* Our ``"harvest_action"`` is only executed *after* the ``"grow_action"`` has completed
* The ``config["command"]`` is executed (this time with no ``config["arguments"]``)
* The ``STDOUT`` shows that we harvested ``16`` *mangos*. Quite the haul!


.. admonition:: ✨ Congratulations! ✨

    You've gone through the basic python interface tutorial and are ready to make
    some workflows!

    If you're looking to add more control to your workflows or for an extra challenge,
    check out the :ref:`advanced`.

.. toctree::
   :maxdepth: 2
