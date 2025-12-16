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
until the later :doc:`advanced`.

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
    :emphasize-lines: 8

    sane_runner -p .sane/ --run

    2025-12-07 20:36:10 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-07 20:36:10 INFO     [orchestrator]           Searching for workflow files...
    2025-12-07 20:36:10 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-07 20:36:10 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-07 20:36:10 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-07 20:36:10 INFO     [orchestrator]               Found .sane/mango/hosts/forest.py
    2025-12-07 20:36:10 INFO     [orchestrator]           Loading python file .sane/mango/hosts/forest.py as 'mango.hosts.forest'
    2025-12-07 20:36:10 INFO     [sane_runner]            No actions selected
    ...help info...

.. tip:: This output can be reproduced by using the source repo example found at
         ``/home/aislas/frameflow/docs/examples/mango/python_basic_host/.sane``

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
    :emphasize-lines: 8-11, 32, 42-44, 48, 50-54, 61-63

    sane_runner -p .sane/ -sh forest -n -v -r

    2025-12-10 18:41:08 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-10 18:41:08 INFO     [orchestrator]           Searching for workflow files...
    2025-12-10 18:41:08 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-10 18:41:08 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-10 18:41:08 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-10 18:41:08 INFO     [orchestrator]               Found .sane/mango/hosts/forest.py
    2025-12-10 18:41:08 INFO     [orchestrator]               Found .sane/mango/actions/grow.py
    2025-12-10 18:41:08 INFO     [orchestrator]           Loading python file .sane/mango/hosts/forest.py as 'mango.hosts.forest'
    2025-12-10 18:41:08 INFO     [orchestrator]           Loading python file .sane/mango/actions/grow.py as 'mango.actions.grow'
    2025-12-10 18:41:08 INFO     [orchestrator]           No previous save file to load
    2025-12-10 18:41:08 INFO     [orchestrator]           Requested actions:
    2025-12-10 18:41:08 INFO     [orchestrator]             grow_action  
    2025-12-10 18:41:08 INFO     [orchestrator]           and any necessary dependencies
    2025-12-10 18:41:08 INFO     [orchestrator]           Full action set:
    2025-12-10 18:41:08 INFO     [orchestrator]           Full action set:
    2025-12-10 18:41:08 INFO     [orchestrator]             grow_action  
    2025-12-10 18:41:08 INFO     [orchestrator]           Checking host "forest"
    2025-12-10 18:41:08 INFO     [orchestrator]           Running as 'forest'
    2025-12-10 18:41:08 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2025-12-10 18:41:08 INFO     [orchestrator]             Checking environments...
    2025-12-10 18:41:08 INFO     [orchestrator]             Checking resource availability...
    2025-12-10 18:41:08 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-10 18:41:08 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * * 
    2025-12-10 18:41:08 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-10 18:41:08 INFO     [orchestrator]           Saving host information...
    2025-12-10 18:41:08 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2025-12-10 18:41:08 INFO     [orchestrator]           No previous save file to load
    2025-12-10 18:41:08 INFO     [orchestrator]           Using working directory : '/home/aislas/mango'
    2025-12-10 18:41:08 INFO     [orchestrator]           Running actions...
    2025-12-10 18:41:08 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2025-12-10 18:41:08 INFO     [thread_0]  [grow_action::launch]      Action logfile captured at /home/aislas/mango/log/grow_action.log
    2025-12-10 18:41:08 INFO     [thread_0]  [grow_action::launch]      Saving action information for launch...
    2025-12-10 18:41:08 INFO     [thread_0]  [grow_action::launch]      Using working directory : '/home/aislas/mango'
    2025-12-10 18:41:08 INFO     [thread_0]  [grow_action::launch]      Running command:
    2025-12-10 18:41:08 INFO     [thread_0]  [grow_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_grow_action.json
    2025-12-10 18:41:08 INFO     [thread_0]  [grow_action::launch]      Command output will be captured to logfile /home/aislas/mango/log/grow_action.runlog
    2025-12-10 18:41:08 INFO     [thread_0]  [grow_action::launch]      Command output will be printed to this terminal
    2025-12-10 18:41:08 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
    2025-12-10 18:41:08 INFO     [grow_action::launch]    Current directory: /home/aislas/mango
    2025-12-10 18:41:08 INFO     [grow_action::launch]    Loaded Action "grow_action"
    2025-12-10 18:41:08 INFO     [grow_action::launch]    Loaded Host "forest"
    2025-12-10 18:41:08 INFO     [grow_action::launch]    Using Environment "valley"
    2025-12-10 18:41:08 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2025-12-10 18:41:08 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2025-12-10 18:41:08 INFO     [grow_action::run]       Running command:
    2025-12-10 18:41:08 INFO     [grow_action::run]         .sane/mango/scripts/grow.sh 4
    2025-12-10 18:41:08 INFO     [grow_action::run]       Command output will be printed to this terminal
    2025-12-10 18:41:08 STDOUT   [grow_action::run]       Growing with 4 trees with 85% growth rate...
    2025-12-10 18:41:08 STDOUT   [grow_action::run]         Tree 1 grew 6 mangos!
    2025-12-10 18:41:08 STDOUT   [grow_action::run]         Tree 2 grew 6 mangos!
    2025-12-10 18:41:08 STDOUT   [grow_action::run]         Tree 3 grew 4 mangos!
    2025-12-10 18:41:08 STDOUT   [grow_action::run]         Tree 4 grew 6 mangos!
    2025-12-10 18:41:08 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
    2025-12-10 18:41:08 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2025-12-10 18:41:08 INFO     [orchestrator]           Finished running queued actions
    2025-12-10 18:41:08 INFO     [orchestrator]             grow_action: success  
    2025-12-10 18:41:08 INFO     [orchestrator]           All actions finished with success
    2025-12-10 18:41:08 INFO     [orchestrator]           Finished in 0:00:00.183791
    2025-12-10 18:41:08 INFO     [orchestrator]           Logfiles at /home/aislas/mango/log
    2025-12-10 18:41:08 INFO     [orchestrator]           Save file at /home/aislas/mango/tmp/orchestrator.json
    2025-12-10 18:41:08 INFO     [orchestrator]           JUnit file at /home/aislas/mango/log/results.xml
    2025-12-10 18:41:08 INFO     [sane_runner]            Finished

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
    :emphasize-lines: 59, 75, 77-78

    sane_runner -p .sane/ -sh forest -n -v -r

    2025-12-11 16:36:33 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-11 16:36:33 INFO     [orchestrator]           Searching for workflow files...
    2025-12-11 16:36:33 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-11 16:36:33 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-11 16:36:33 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-11 16:36:33 INFO     [orchestrator]               Found .sane/mango/actions/grow.py
    2025-12-11 16:36:33 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
    2025-12-11 16:36:33 INFO     [orchestrator]               Found .sane/mango/hosts/forest.py
    2025-12-11 16:36:33 INFO     [orchestrator]           Loading python file .sane/mango/actions/grow.py as 'mango.actions.grow'
    2025-12-11 16:36:33 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
    2025-12-11 16:36:33 INFO     [orchestrator]           Loading python file .sane/mango/hosts/forest.py as 'mango.hosts.forest'
    2025-12-11 16:36:33 INFO     [orchestrator]           No previous save file to load
    2025-12-11 16:36:33 INFO     [orchestrator]           Requested actions:
    2025-12-11 16:36:33 INFO     [orchestrator]             grow_action     harvest_action  
    2025-12-11 16:36:33 INFO     [orchestrator]           and any necessary dependencies
    2025-12-11 16:36:33 INFO     [orchestrator]           Full action set:
    2025-12-11 16:36:33 INFO     [orchestrator]           Full action set:
    2025-12-11 16:36:33 INFO     [orchestrator]             grow_action     harvest_action  
    2025-12-11 16:36:33 INFO     [orchestrator]           Checking host "forest"
    2025-12-11 16:36:33 INFO     [orchestrator]           Running as 'forest'
    2025-12-11 16:36:33 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2025-12-11 16:36:33 INFO     [orchestrator]             Checking environments...
    2025-12-11 16:36:33 INFO     [orchestrator]             Checking resource availability...
    2025-12-11 16:36:33 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-11 16:36:33 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * * 
    2025-12-11 16:36:33 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-11 16:36:33 INFO     [orchestrator]           Saving host information...
    2025-12-11 16:36:33 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2025-12-11 16:36:33 INFO     [orchestrator]           No previous save file to load
    2025-12-11 16:36:33 INFO     [orchestrator]           Using working directory : '/home/aislas/mango'
    2025-12-11 16:36:33 INFO     [orchestrator]           Running actions...
    2025-12-11 16:36:33 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2025-12-11 16:36:33 INFO     [thread_0]  [grow_action::launch]         Action logfile captured at /home/aislas/mango/log/grow_action.log
    2025-12-11 16:36:33 INFO     [thread_0]  [grow_action::launch]         Saving action information for launch...
    2025-12-11 16:36:33 INFO     [thread_0]  [grow_action::launch]         Using working directory : '/home/aislas/mango'
    2025-12-11 16:36:33 INFO     [thread_0]  [grow_action::launch]         Running command:
    2025-12-11 16:36:33 INFO     [thread_0]  [grow_action::launch]           /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_grow_action.json
    2025-12-11 16:36:33 INFO     [thread_0]  [grow_action::launch]         Command output will be captured to logfile /home/aislas/mango/log/grow_action.runlog
    2025-12-11 16:36:33 INFO     [thread_0]  [grow_action::launch]         Command output will be printed to this terminal
    2025-12-11 16:36:33 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
    2025-12-11 16:36:33 INFO     [grow_action::launch]    Current directory: /home/aislas/mango
    2025-12-11 16:36:33 INFO     [grow_action::launch]    Loaded Action "grow_action"
    2025-12-11 16:36:33 INFO     [grow_action::launch]    Loaded Host "forest"
    2025-12-11 16:36:33 INFO     [grow_action::launch]    Using Environment "valley"
    2025-12-11 16:36:33 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2025-12-11 16:36:33 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2025-12-11 16:36:33 INFO     [grow_action::run]       Running command:
    2025-12-11 16:36:33 INFO     [grow_action::run]         .sane/mango/scripts/grow.sh 4
    2025-12-11 16:36:33 INFO     [grow_action::run]       Command output will be printed to this terminal
    2025-12-11 16:36:33 STDOUT   [grow_action::run]       Growing with 4 trees with 85% growth rate...
    2025-12-11 16:36:33 STDOUT   [grow_action::run]         Tree 1 grew 2 mangos!
    2025-12-11 16:36:33 STDOUT   [grow_action::run]         Tree 2 grew 4 mangos!
    2025-12-11 16:36:33 STDOUT   [grow_action::run]         Tree 3 grew 2 mangos!
    2025-12-11 16:36:33 STDOUT   [grow_action::run]         Tree 4 grew 8 mangos!
    2025-12-11 16:36:33 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
    2025-12-11 16:36:33 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2025-12-11 16:36:33 INFO     [orchestrator]           Running 'harvest_action' on 'forest'
    2025-12-11 16:36:33 INFO     [thread_0]  [harvest_action::launch]      Action logfile captured at /home/aislas/mango/log/harvest_action.log
    2025-12-11 16:36:33 INFO     [thread_0]  [harvest_action::launch]      Saving action information for launch...
    2025-12-11 16:36:33 INFO     [thread_0]  [harvest_action::launch]      Using working directory : '/home/aislas/mango'
    2025-12-11 16:36:33 INFO     [thread_0]  [harvest_action::launch]      Running command:
    2025-12-11 16:36:33 INFO     [thread_0]  [harvest_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_harvest_action.json
    2025-12-11 16:36:33 INFO     [thread_0]  [harvest_action::launch]      Command output will be captured to logfile /home/aislas/mango/log/harvest_action.runlog
    2025-12-11 16:36:33 INFO     [thread_0]  [harvest_action::launch]      Command output will be printed to this terminal
    2025-12-11 16:36:33 INFO     [harvest_action::launch] ***************Inside action_launcher.py***************
    2025-12-11 16:36:33 INFO     [harvest_action::launch] Current directory: /home/aislas/mango
    2025-12-11 16:36:33 INFO     [harvest_action::launch] Loaded Action "harvest_action"
    2025-12-11 16:36:33 INFO     [harvest_action::launch] Loaded Host "forest"
    2025-12-11 16:36:33 INFO     [harvest_action::launch] Using Environment "valley"
    2025-12-11 16:36:33 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2025-12-11 16:36:33 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2025-12-11 16:36:33 INFO     [harvest_action::run]    Running command:
    2025-12-11 16:36:33 INFO     [harvest_action::run]      .sane/mango/scripts/harvest.sh
    2025-12-11 16:36:33 INFO     [harvest_action::run]    Command output will be printed to this terminal
    2025-12-11 16:36:33 STDOUT   [harvest_action::run]    Harvesting mangos...
    2025-12-11 16:36:33 STDOUT   [harvest_action::run]    Collected : 16
    2025-12-11 16:36:33 INFO     [harvest_action::launch] ***************Finished action_launcher.py***************
    2025-12-11 16:36:33 INFO     [orchestrator]           [FINISHED] ** Action 'harvest_action'         completed with 'success'
    2025-12-11 16:36:33 INFO     [orchestrator]           Finished running queued actions
    2025-12-11 16:36:33 INFO     [orchestrator]             grow_action   : success  harvest_action: success  
    2025-12-11 16:36:33 INFO     [orchestrator]           All actions finished with success
    2025-12-11 16:36:33 INFO     [orchestrator]           Finished in 0:00:00.346601
    2025-12-11 16:36:33 INFO     [orchestrator]           Logfiles at /home/aislas/mango/log
    2025-12-11 16:36:33 INFO     [orchestrator]           Save file at /home/aislas/mango/tmp/orchestrator.json
    2025-12-11 16:36:33 INFO     [orchestrator]           JUnit file at /home/aislas/mango/log/results.xml
    2025-12-11 16:36:33 INFO     [sane_runner]            Finished


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
    check out the :doc:`advanced`.

.. We will create the ``.sane/mango/actions/harvest.py`` file and mock up our function:

.. .. code-block:: python
..     :caption: .sane/mango/actions/harvest.py

..     import sane

..     @sane.register
..     def create_harvest_action( orch ):
..       # what to put here...

.. Depending on how thoroughly you read the :py:meth:`Action.load_core_config` documentation
.. presented in the JSON :ref:`json.actions` section, you may recall that the config loading
.. relied almost exclusively on :py:class:`Action` :ref:`action.ui` interaction. Internally,
.. there is some data "massaging" to get JSON ``dict`` values into the right spot, but the
.. content is analogous.

.. Using the API reference links as necessary, let's start to fill out our function with useful
.. details:

.. .. literalinclude:: ../../examples/mango/python_harvest_action/.sane/mango/actions/harvest.py
..     :language: python
..     :caption: .sane/mango/actions/harvest.py
..     :emphasize-lines: 13

.. We won't add any :py:meth:`~Action.resources`, but we will need to create the helper
.. script to do the harvesting:

.. .. literalinclude:: ../../examples/mango/python_harvest_action/.sane/scripts/harvest.sh
..     :language: bash
..     :caption: .sane/scripts/harvest.sh

.. We are ready to run this new action with our previous JSON setup:

.. .. code-block:: none
..     :emphasize-lines: 15, 31, 37

..     sane_runner -p .sane/ --specific_host forest --run -p patch/ -v -n

..     2025-12-05 15:54:13 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
..     2025-12-05 15:54:13 INFO     [orchestrator]           Searching for workflow files...
..     2025-12-05 15:54:13 INFO     [orchestrator]             Searching .sane/ for *.json
..     2025-12-05 15:54:13 INFO     [orchestrator]             Searching .sane/ for *.jsonc
..     2025-12-05 15:54:13 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
..     2025-12-05 15:54:13 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
..     2025-12-05 15:54:13 INFO     [orchestrator]             Searching .sane/ for *.py
..     2025-12-05 15:54:13 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
..     2025-12-05 15:54:13 INFO     [orchestrator]             Searching patch/ for *.json
..     2025-12-05 15:54:13 INFO     [orchestrator]             Searching patch/ for *.jsonc
..     2025-12-05 15:54:13 INFO     [orchestrator]               Found patch/valley_growth.jsonc
..     2025-12-05 15:54:13 INFO     [orchestrator]             Searching patch/ for *.py
..     2025-12-05 15:54:13 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
..     2025-12-05 15:54:13 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
..     2025-12-05 15:54:13 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
..     2025-12-05 15:54:13 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
..     ...
..     2025-12-05 15:54:13 INFO     [orchestrator]           Running 'grow_action' on 'forest'
..     ...
..     2025-12-05 15:54:13 INFO     [grow_action::run]       Running command:
..     2025-12-05 15:54:13 INFO     [grow_action::run]         .sane/scripts/grow.sh 4
..     2025-12-05 15:54:13 INFO     [grow_action::run]       Command output will be printed to this terminal
..     2025-12-05 15:54:13 STDOUT   [grow_action::run]       Growing with 4 trees with 400% growth rate...
..     2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 1 grew 33 mangos!
..     2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 2 grew 21 mangos!
..     2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 3 grew 37 mangos!
..     2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 4 grew 1 mangos!
..     ...
..     2025-12-05 15:54:13 INFO     [orchestrator]           Running 'harvest_action' on 'forest'
..     ...
..     2025-12-05 15:54:13 INFO     [harvest_action::run]    Running command:
..     2025-12-05 15:54:13 INFO     [harvest_action::run]      .sane/scripts/harvest.sh
..     2025-12-05 15:54:13 INFO     [harvest_action::run]    Command output will be printed to this terminal
..     2025-12-05 15:54:13 STDOUT   [harvest_action::run]    Harvesting mangos...
..     2025-12-05 15:54:13 STDOUT   [harvest_action::run]    Collected : 92
..     ...
..     2025-12-05 15:54:13 INFO     [sane_runner]            Finished

.. .. tip:: This output can be reproduced by using the source repo example found at
..           ``docs/examples/mango/python_harvest_action/.sane/``

.. As we are already probably familiar with the runner outupt, the above shows the
.. condensed view of the sections of interest:

.. * The python file is loaded first then immediately processed for registered functions before the JSON files

..   * The dependency of ``"harvest_action"`` on ``"grow_action"`` can be declared before the parent action is created
..   * :py:class:`Action.dependencies` makes no distinction between JSON or python declared actions
.. * The ``"harvest_action"`` is only run after the ``"grow_action"``
.. * The total number of mangos is correct and it's quite the harvest!

.. Hosts
.. -----
.. Using the same guidelines as above (using :py:class:`Host` :ref:`host.ui`) we should
.. be able to create a new host as well:

.. .. literalinclude:: ../../examples/mango/python_desert_host/.sane/mango/hosts/desert.py
..     :language: python
..     :caption: .sane/mango/hosts/desert.py

.. However if we run this we may get some issues...

.. .. code-block:: none
..     :emphasize-lines: 36-38

..     sane_runner -p .sane/ -n -r -sh wasteland -p patch/ -v

..     2025-12-05 16:35:28 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
..     2025-12-05 16:35:28 INFO     [orchestrator]           Searching for workflow files...
..     2025-12-05 16:35:28 INFO     [orchestrator]             Searching .sane/ for *.json
..     2025-12-05 16:35:28 INFO     [orchestrator]             Searching .sane/ for *.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator]             Searching .sane/ for *.py
..     2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/hosts/desert.py
..     2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
..     2025-12-05 16:35:28 INFO     [orchestrator]             Searching patch/ for *.json
..     2025-12-05 16:35:28 INFO     [orchestrator]             Searching patch/ for *.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator]               Found patch/valley_growth.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator]             Searching patch/ for *.py
..     2025-12-05 16:35:28 INFO     [orchestrator]           Loading python file .sane/mango/hosts/desert.py as 'mango.hosts.desert'
..     2025-12-05 16:35:28 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
..     2025-12-05 16:35:28 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator::patch]    Processing patches from patch/valley_growth.jsonc
..     2025-12-05 16:35:28 INFO     [orchestrator::patch]      Applying patch to Host 'forest'
..     2025-12-05 16:35:28 INFO     [forest::patch]              Applying patch to Environment 'valley'
..     2025-12-05 16:35:28 WARNING  [orchestrator::patch]      Host 'host-does-not-exist' does not exist, cannot patch
..     2025-12-05 16:35:28 INFO     [sane_runner]            Changing all actions output to verbose
..     2025-12-05 16:35:28 INFO     [orchestrator]           No previous save file to load
..     2025-12-05 16:35:28 INFO     [orchestrator]           Running actions:
..     2025-12-05 16:35:28 INFO     [orchestrator]             harvest_action  grow_action     
..     2025-12-05 16:35:28 INFO     [orchestrator]           and any necessary dependencies
..     2025-12-05 16:35:28 INFO     [orchestrator]           Full action set:
..     2025-12-05 16:35:28 INFO     [orchestrator]             grow_action     harvest_action  
..     2025-12-05 16:35:28 INFO     [orchestrator]           Checking host "desert"
..     2025-12-05 16:35:28 INFO     [orchestrator]           Running as 'desert'
..     2025-12-05 16:35:28 INFO     [orchestrator]           Checking ability to run all actions on 'desert'...
..     2025-12-05 16:35:28 INFO     [orchestrator]             Checking environments...
..     2025-12-05 16:35:28 CRITICAL [orchestrator]             Missing environments in Host( "desert" )
..     2025-12-05 16:35:28 ERROR    [orchestrator]               Action( "grow_action" ) requires Environment( "valley" )
..     2025-12-05 16:35:28 ERROR    [orchestrator]               Action( "harvest_action" ) requires Environment( "valley" )
..     Traceback (most recent call last):

..       File "/home/aislas/sane_workflows/bin/sane_runner.py", line 322, in <module>
..         main()

..       File "/home/aislas/sane_workflows/bin/sane_runner.py", line 305, in main
..         success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )

..       File "/home/aislas/sane_workflows/sane/orchestrator.py", line 529, in run_actions
..         self.check_host( traversal_list )

..       File "/home/aislas/sane_workflows/sane/orchestrator.py", line 458, in check_host
..         raise Exception( f"Missing environments {missing_env}" )

..     Exception: Missing environments [('grow_action', 'valley'), ('harvest_action', 'valley')]


.. .. tip:: This output can be reproduced by using the source repo example found at
..           ``docs/examples/mango/python_desert_host/.sane/``

.. We did not implement the ``"valley"`` environment which both actions explicitly
.. call for, and our ``"dunes"`` environment has no aliases.

.. Register Order
.. --------------
.. We can perform object patching using the python interface as well, with even more
.. powerful control with the caveat that JSON objects are always loaded afterwards.
.. All we need to do is call :py:func:`@sane.register <sane.register>` with a lower
.. priority than the function that created the object.

.. To demonstrate, let's fix our ``"desert"`` environment issue with a "patch" python
.. file we will put in the ``patch/`` folder:


.. .. literalinclude:: ../../examples/mango/python_desert_patch/patch/desert_valley.py
..     :language: python
..     :caption: patch/desert_valley.py

.. However if we run this we may get some issues...

.. .. code-block:: none
..     :emphasize-lines: 18-19, 37-39

..     sane_runner -p .sane/ -n -r -sh wasteland -p patch/ -v

..     2025-12-05 16:51:32 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
..     2025-12-05 16:51:32 INFO     [orchestrator]           Searching for workflow files...
..     2025-12-05 16:51:32 INFO     [orchestrator]             Searching .sane/ for *.json
..     2025-12-05 16:51:32 INFO     [orchestrator]             Searching .sane/ for *.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator]             Searching .sane/ for *.py
..     2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
..     2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/hosts/desert.py
..     2025-12-05 16:51:32 INFO     [orchestrator]             Searching patch/ for *.json
..     2025-12-05 16:51:32 INFO     [orchestrator]             Searching patch/ for *.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator]               Found patch/valley_growth.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator]             Searching patch/ for *.py
..     2025-12-05 16:51:32 INFO     [orchestrator]               Found patch/desert_valley.py
..     2025-12-05 16:51:32 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
..     2025-12-05 16:51:32 INFO     [orchestrator]           Loading python file .sane/mango/hosts/desert.py as 'mango.hosts.desert'
..     2025-12-05 16:51:32 INFO     [orchestrator]           Loading python file patch/desert_valley.py as 'desert_valley'
..     2025-12-05 16:51:32 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator::patch]    Processing patches from patch/valley_growth.jsonc
..     2025-12-05 16:51:32 INFO     [orchestrator::patch]      Applying patch to Host 'forest'
..     2025-12-05 16:51:32 INFO     [forest::patch]              Applying patch to Environment 'valley'
..     2025-12-05 16:51:32 WARNING  [orchestrator::patch]      Host 'host-does-not-exist' does not exist, cannot patch
..     2025-12-05 16:51:32 INFO     [sane_runner]            Changing all actions output to verbose
..     2025-12-05 16:51:32 INFO     [orchestrator]           No previous save file to load
..     2025-12-05 16:51:32 INFO     [orchestrator]           Running actions:
..     2025-12-05 16:51:32 INFO     [orchestrator]             harvest_action  grow_action     
..     2025-12-05 16:51:32 INFO     [orchestrator]           and any necessary dependencies
..     2025-12-05 16:51:32 INFO     [orchestrator]           Full action set:
..     2025-12-05 16:51:32 INFO     [orchestrator]             grow_action     harvest_action  
..     2025-12-05 16:51:32 INFO     [orchestrator]           Checking host "desert"
..     2025-12-05 16:51:32 INFO     [orchestrator]           Running as 'desert'
..     2025-12-05 16:51:32 INFO     [orchestrator]           Checking ability to run all actions on 'desert'...
..     2025-12-05 16:51:32 INFO     [orchestrator]             Checking environments...
..     2025-12-05 16:51:32 INFO     [orchestrator]             Checking resource availability...
..     2025-12-05 16:51:32 CRITICAL [desert]                       Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 50, used: 0 }}
..     Traceback (most recent call last):

..       File "/home/aislas/sane_workflows/bin/sane_runner.py", line 322, in <module>
..         main()

..       File "/home/aislas/sane_workflows/bin/sane_runner.py", line 305, in main
..         success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )

..       File "/home/aislas/sane_workflows/sane/orchestrator.py", line 529, in run_actions
..         self.check_host( traversal_list )

..       File "/home/aislas/sane_workflows/sane/orchestrator.py", line 465, in check_host
..         can_run = host.resources_available( self.actions[node].resources( self.current_host ), requestor=self.actions[node] )

..       File "/home/aislas/sane_workflows/sane/resources.py", line 637, in resources_available
..         raise Exception( msg )

..     Exception: Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 50, used: 0 }}

.. .. tip:: This output can be reproduced by using the source repo example found at
..           ``docs/examples/mango/python_desert_patch/.sane/``

.. Our "patch" python file does in fact get loaded after ``.sane/mango/hosts/desert.py``!
.. We got a *little* bit further, but now we see the err of our ways in not adding
.. the appriopriate resources. How would we ever grow mangos on ``"cacti"``?!?


.. Python Modules
.. --------------
.. The final beginner section of the tutorial will cover how to reference python files
.. within other python files in your workflow.

.. For this example, we shall have some really useful helper functions in ``.sane/custom/funcs.py``:

.. .. literalinclude:: ../../examples/mango/python_imports/.sane/mango/custom/funcs.py
..     :language: python
..     :caption: .sane/mango/custom/funcs.py

.. And let's modify our ``"desert"`` host to use this function:

.. .. literalinclude:: ../../examples/mango/python_imports/.sane/mango/hosts/desert.py
..     :language: python
..     :caption: .sane/mango/hosts/desert.py
..     :emphasize-lines: 3

.. Now if we run this:

.. .. code-block:: none
..     :emphasize-lines: 14

..     sane_runner -p .sane/ -n -r -sh sahara -v

..     2025-12-05 17:24:58 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
..     2025-12-05 17:24:58 INFO     [orchestrator]           Searching for workflow files...
..     2025-12-05 17:24:58 INFO     [orchestrator]             Searching .sane/ for *.json
..     2025-12-05 17:24:58 INFO     [orchestrator]             Searching .sane/ for *.jsonc
..     2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
..     2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
..     2025-12-05 17:24:58 INFO     [orchestrator]             Searching .sane/ for *.py
..     2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/hosts/desert.py
..     2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
..     2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/custom/funcs.py
..     2025-12-05 17:24:58 INFO     [orchestrator]           Loading python file .sane/mango/hosts/desert.py as 'mango.hosts.desert'
..     2025-12-05 17:24:58 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
..     2025-12-05 17:24:58 INFO     [orchestrator]           Loading python file .sane/mango/custom/funcs.py as 'mango.custom.funcs'
..     2025-12-05 17:24:58 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
..     2025-12-05 17:24:58 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
..     2025-12-05 17:24:58 INFO     [sane_runner]            Changing all actions output to verbose
..     2025-12-05 17:24:58 INFO     [orchestrator]           No previous save file to load
..     2025-12-05 17:24:58 INFO     [orchestrator]           Running actions:
..     2025-12-05 17:24:58 INFO     [orchestrator]             harvest_action  grow_action     
..     2025-12-05 17:24:58 INFO     [orchestrator]           and any necessary dependencies
..     2025-12-05 17:24:58 INFO     [orchestrator]           Full action set:
..     2025-12-05 17:24:58 INFO     [orchestrator]             grow_action     harvest_action  
..     2025-12-05 17:24:58 INFO     [orchestrator]           Checking host "sonoran"
..     2025-12-05 17:24:58 INFO     [orchestrator]           Checking host "sahara"
..     2025-12-05 17:24:58 INFO     [orchestrator]           Running as 'sahara'
..     2025-12-05 17:24:58 INFO     [orchestrator]           Checking ability to run all actions on 'sahara'...
..     2025-12-05 17:24:58 INFO     [orchestrator]             Checking environments...
..     2025-12-05 17:24:58 INFO     [orchestrator]             Checking resource availability...
..     2025-12-05 17:24:58 CRITICAL [sahara]                       Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 0, used: 0 }}
..     Traceback (most recent call last):

..       File "/home/aislas/frameflow/bin/sane_runner.py", line 322, in <module>
..         main()

..       File "/home/aislas/frameflow/bin/sane_runner.py", line 305, in main
..         success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )

..       File "/home/aislas/frameflow/sane/orchestrator.py", line 529, in run_actions
..         self.check_host( traversal_list )

..       File "/home/aislas/frameflow/sane/orchestrator.py", line 465, in check_host
..         can_run = host.resources_available( self.actions[node].resources( self.current_host ), requestor=self.actions[node] )

..       File "/home/aislas/frameflow/sane/resources.py", line 637, in resources_available
..         raise Exception( msg )

..     Exception: Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 0, used: 0 }}

.. .. tip:: This output can be reproduced by using the source repo example found at
..           ``docs/examples/mango/python_imports/.sane/``

.. We still have no trees, **but** our ``"cacti"`` amount corresponds to the ``.sane/mango/custom/funcs.py``
.. ``num_cacti_in_region()`` function. Note that even though the ``.sane/mango/custom/funcs.py``
.. module is loaded after the ``mango.hosts.desert`` module, the import still happens correctly.

.. This is because anything provided as a ``-p``/``--path`` argument is added to the
.. `sys.path`_ for module searching. So ``.sane/mango/custom/funcs.py`` can be imported
.. in our ``desert.py`` file as ``mango.custom.funcs``.

.. toctree::
   :maxdepth: 2
