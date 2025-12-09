Python Interfacing
==================
.. py:module:: sane
    :no-index:

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

We will start by creating a :py:class:`Host` object and adding it to the :py:class:`Orchestrator`

.. code-block:: python

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
               be added eventually.

As far as creating a host we are basically done... Well, not really. It is a valid
host, but it does not provided much. Additionally, when running a workflow, the
expectation is that any :py:class:`Action` will always run on in an :py:class:`Environment`,
even if one is not needed. Thus, hosts must provide at least one :py:class:`Environment`
to even be somewhat useful.

Let's continue to flesh out this :py:class:`Host`. If you click on the class name
you will be taken to the API reference documentation, or alternatively click this
:py:class:`Host` :ref:`host.ui` link to see the API calls we care about. There are
quite a few, so to start simple we will focus on :py:meth:`Host.add_resources`
and :py:meth:`Host.add_environment`.

Resources & Environment
^^^^^^^^^^^^^^^^^^^^^^^
For adding resources, looking at the API we would see that :py:meth:`Host.add_resources`
uses :py:attr:`sane.resources.Resource` syntax as a :external:py:class:`dict` input:

.. collapse:: Quick Reference (click to open/close):

  .. automethod:: sane.Host.add_resources
      :no-index:

  .. autoclass:: sane.resources.Resource
      :no-index:
      :special-members:

|

The simple explanation is that the resource must be a non-negative integer
followed by optional binary scaling ( 'k' : 1024, 'm' : 1024 :sup:`2`, and so on), and
an optional unit designator.


So we have a ``forest`` :py:class:`Host` and want to add resources for our ``mango``
project workflow... Let's add ``"trees"`` (these could nominally be ``"cpus"``
or whatever resource your :py:class:`Action` would take to run):


.. code-block:: python
    :emphasize-lines: 8

    import sane

    @sane.register
    def create_forest_host( orch ):
      forest = sane.Host( "forest" )
      orch.add_host( forest )

      forest.add_resources( { "trees" : 12 } )

Next, we need an :py:class:`Environment` to work with. For demonstrative purposes,
we will say that our environments have different ``GROWTH_RATE`` values can be
used within the workflow.

If we look at the :py:class:`Environment` :ref:`env.ui` we can see what function
calls are available to use. Once again, keeping things simple, we will focus only
on the necessary functions to get this workflow going. We will be using the
:py:meth:`Environment.setup_env_vars` method, then after :py:meth:`Host.add_environment`.

.. collapse:: Quick Reference (click to open/close)

  .. automethod:: Host.add_environment
      :no-index:

  .. automethod:: Environment.setup_env_vars
      :no-index:

|

Our final file setup should look something like so:

.. literalinclude:: ../../examples/mango/python_basic_host/.sane/mango/hosts/forest.py
    :caption: .sane/mango/hosts/forest.py
    :language: python


If we were to run this host, however, we would get some lackluster output:

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
script at ``.sane/scripts/grow.sh``:

.. code-block:: none
    :emphasize-lines: 4, 8

    .sane/
    ├── mango
    │   ├── actions
    │   │   └── grow.py
    │   └── hosts
    │       └── forest.py
    └── scripts
        └── grow.sh

Similar to the :py:class:`Host` creation, take a look at the :py:class:`Action`
:ref:`action.ui` to get an idea of the API available to use. Most important
to us will be:

* :py:attr:`config` (``config["command"]`` and ``config["arguments"]`` since we are using the default :py:meth:`Action.run`)
* :py:attr:`environment`
* :py:meth:`~Action.add_dependencies`
* :py:meth:`~Action.add_resource_requirements`

Let's quickly go over the relevance of each of these

:py:attr:`config`
^^^^^^^^^^^^^^^^^

Arguably the most versatile field in the default :py:class:`Action`, this generic
``dict`` is meant to hold anything `picklable`_ that your action may need in running.
Later (during :ref:`advanced.dereferencing`) we will learn to more effectively use
this general data container.

For now, the main use is in the ``config["command"]`` and ``config["arguments"]``
keys which are used by the default :py:meth:`Action.run`. As their names imply,
during :py:class:`Action` execution, the ``config["command"]`` and ``config["arguments"]``
will be used as the command and arguments to execute for that action, respectively.

.. note:: The string provided to ``config["command"]`` must be an executable. Commands
          from your ``PATH`` will work, but if you use a script it must have the
          executable property. Try running:

          .. code-block:: none

              chmod +x <command script>

          if you are having issues getting your :py:class:`Action` to run your ``config["command"]``



.. code-block:: python
    :caption: .sane/mango/actions/harvest.py

    import sane

    @sane.register
    def create_grow_action( orch ):
      grow = sane.Action( "grow_action" )
      orch.add_action( grow )

      grow.config["command"] = ".sane/scripts/grow.sh"




.. code-block:: python
    :caption: .sane/mango/actions/harvest.py

    import sane

    @sane.register
    def create_harvest_action( orch ):
      # what to put here...








































We will create the ``.sane/mango/actions/harvest.py`` file and mock up our function:

.. code-block:: python
    :caption: .sane/mango/actions/harvest.py

    import sane

    @sane.register
    def create_harvest_action( orch ):
      # what to put here...

Depending on how thoroughly you read the :py:meth:`Action.load_core_config` documentation
presented in the JSON :ref:`json.actions` section, you may recall that the config loading
relied almost exclusively on :py:class:`Action` :ref:`action.ui` interaction. Internally,
there is some data "massaging" to get JSON ``dict`` values into the right spot, but the
content is analogous.

Using the API reference links as necessary, let's start to fill out our function with useful
details:

.. literalinclude:: ../../examples/mango/python_harvest_action/.sane/mango/actions/harvest.py
    :language: python
    :caption: .sane/mango/actions/harvest.py
    :emphasize-lines: 13

We won't add any :py:meth:`~Action.resources`, but we will need to create the helper
script to do the harvesting:

.. literalinclude:: ../../examples/mango/python_harvest_action/.sane/scripts/harvest.sh
    :language: bash
    :caption: .sane/scripts/harvest.sh

We are ready to run this new action with our previous JSON setup:

.. code-block:: none
    :emphasize-lines: 15, 31, 37

    sane_runner -p .sane/ --specific_host forest --run -p patch/ -v -n

    2025-12-05 15:54:13 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-05 15:54:13 INFO     [orchestrator]           Searching for workflow files...
    2025-12-05 15:54:13 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-05 15:54:13 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-05 15:54:13 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-05 15:54:13 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-05 15:54:13 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-05 15:54:13 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
    2025-12-05 15:54:13 INFO     [orchestrator]             Searching patch/ for *.json
    2025-12-05 15:54:13 INFO     [orchestrator]             Searching patch/ for *.jsonc
    2025-12-05 15:54:13 INFO     [orchestrator]               Found patch/valley_growth.jsonc
    2025-12-05 15:54:13 INFO     [orchestrator]             Searching patch/ for *.py
    2025-12-05 15:54:13 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
    2025-12-05 15:54:13 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-05 15:54:13 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-05 15:54:13 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
    ...
    2025-12-05 15:54:13 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    ...
    2025-12-05 15:54:13 INFO     [grow_action::run]       Running command:
    2025-12-05 15:54:13 INFO     [grow_action::run]         .sane/scripts/grow.sh 4
    2025-12-05 15:54:13 INFO     [grow_action::run]       Command output will be printed to this terminal
    2025-12-05 15:54:13 STDOUT   [grow_action::run]       Growing with 4 trees with 400% growth rate...
    2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 1 grew 33 mangos!
    2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 2 grew 21 mangos!
    2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 3 grew 37 mangos!
    2025-12-05 15:54:13 STDOUT   [grow_action::run]         Tree 4 grew 1 mangos!
    ...
    2025-12-05 15:54:13 INFO     [orchestrator]           Running 'harvest_action' on 'forest'
    ...
    2025-12-05 15:54:13 INFO     [harvest_action::run]    Running command:
    2025-12-05 15:54:13 INFO     [harvest_action::run]      .sane/scripts/harvest.sh
    2025-12-05 15:54:13 INFO     [harvest_action::run]    Command output will be printed to this terminal
    2025-12-05 15:54:13 STDOUT   [harvest_action::run]    Harvesting mangos...
    2025-12-05 15:54:13 STDOUT   [harvest_action::run]    Collected : 92
    ...
    2025-12-05 15:54:13 INFO     [sane_runner]            Finished

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/python_harvest_action/.sane/``

As we are already probably familiar with the runner outupt, the above shows the
condensed view of the sections of interest:

* The python file is loaded first then immediately processed for registered functions before the JSON files

  * The dependency of ``"harvest_action"`` on ``"grow_action"`` can be declared before the parent action is created
  * :py:class:`Action.dependencies` makes no distinction between JSON or python declared actions
* The ``"harvest_action"`` is only run after the ``"grow_action"``
* The total number of mangos is correct and it's quite the harvest!

Hosts
-----
Using the same guidelines as above (using :py:class:`Host` :ref:`host.ui`) we should
be able to create a new host as well:

.. literalinclude:: ../../examples/mango/python_desert_host/.sane/mango/hosts/desert.py
    :language: python
    :caption: .sane/mango/hosts/desert.py

However if we run this we may get some issues...

.. code-block:: none
    :emphasize-lines: 36-38

    sane_runner -p .sane/ -n -r -sh wasteland -p patch/ -v

    2025-12-05 16:35:28 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-05 16:35:28 INFO     [orchestrator]           Searching for workflow files...
    2025-12-05 16:35:28 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-05 16:35:28 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/hosts/desert.py
    2025-12-05 16:35:28 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
    2025-12-05 16:35:28 INFO     [orchestrator]             Searching patch/ for *.json
    2025-12-05 16:35:28 INFO     [orchestrator]             Searching patch/ for *.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator]               Found patch/valley_growth.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator]             Searching patch/ for *.py
    2025-12-05 16:35:28 INFO     [orchestrator]           Loading python file .sane/mango/hosts/desert.py as 'mango.hosts.desert'
    2025-12-05 16:35:28 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
    2025-12-05 16:35:28 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator::patch]    Processing patches from patch/valley_growth.jsonc
    2025-12-05 16:35:28 INFO     [orchestrator::patch]      Applying patch to Host 'forest'
    2025-12-05 16:35:28 INFO     [forest::patch]              Applying patch to Environment 'valley'
    2025-12-05 16:35:28 WARNING  [orchestrator::patch]      Host 'host-does-not-exist' does not exist, cannot patch
    2025-12-05 16:35:28 INFO     [sane_runner]            Changing all actions output to verbose
    2025-12-05 16:35:28 INFO     [orchestrator]           No previous save file to load
    2025-12-05 16:35:28 INFO     [orchestrator]           Running actions:
    2025-12-05 16:35:28 INFO     [orchestrator]             harvest_action  grow_action     
    2025-12-05 16:35:28 INFO     [orchestrator]           and any necessary dependencies
    2025-12-05 16:35:28 INFO     [orchestrator]           Full action set:
    2025-12-05 16:35:28 INFO     [orchestrator]             grow_action     harvest_action  
    2025-12-05 16:35:28 INFO     [orchestrator]           Checking host "desert"
    2025-12-05 16:35:28 INFO     [orchestrator]           Running as 'desert'
    2025-12-05 16:35:28 INFO     [orchestrator]           Checking ability to run all actions on 'desert'...
    2025-12-05 16:35:28 INFO     [orchestrator]             Checking environments...
    2025-12-05 16:35:28 CRITICAL [orchestrator]             Missing environments in Host( "desert" )
    2025-12-05 16:35:28 ERROR    [orchestrator]               Action( "grow_action" ) requires Environment( "valley" )
    2025-12-05 16:35:28 ERROR    [orchestrator]               Action( "harvest_action" ) requires Environment( "valley" )
    Traceback (most recent call last):

      File "/home/aislas/sane_workflows/bin/sane_runner.py", line 322, in <module>
        main()

      File "/home/aislas/sane_workflows/bin/sane_runner.py", line 305, in main
        success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )

      File "/home/aislas/sane_workflows/sane/orchestrator.py", line 529, in run_actions
        self.check_host( traversal_list )

      File "/home/aislas/sane_workflows/sane/orchestrator.py", line 458, in check_host
        raise Exception( f"Missing environments {missing_env}" )

    Exception: Missing environments [('grow_action', 'valley'), ('harvest_action', 'valley')]


.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/python_desert_host/.sane/``

We did not implement the ``"valley"`` environment which both actions explicitly
call for, and our ``"dunes"`` environment has no aliases.

Register Order
--------------
We can perform object patching using the python interface as well, with even more
powerful control with the caveat that JSON objects are always loaded afterwards.
All we need to do is call :py:func:`@sane.register <sane.register>` with a lower
priority than the function that created the object.

To demonstrate, let's fix our ``"desert"`` environment issue with a "patch" python
file we will put in the ``patch/`` folder:


.. literalinclude:: ../../examples/mango/python_desert_patch/patch/desert_valley.py
    :language: python
    :caption: patch/desert_valley.py

However if we run this we may get some issues...

.. code-block:: none
    :emphasize-lines: 18-19, 37-39

    sane_runner -p .sane/ -n -r -sh wasteland -p patch/ -v

    2025-12-05 16:51:32 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-05 16:51:32 INFO     [orchestrator]           Searching for workflow files...
    2025-12-05 16:51:32 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-05 16:51:32 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
    2025-12-05 16:51:32 INFO     [orchestrator]               Found .sane/mango/hosts/desert.py
    2025-12-05 16:51:32 INFO     [orchestrator]             Searching patch/ for *.json
    2025-12-05 16:51:32 INFO     [orchestrator]             Searching patch/ for *.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator]               Found patch/valley_growth.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator]             Searching patch/ for *.py
    2025-12-05 16:51:32 INFO     [orchestrator]               Found patch/desert_valley.py
    2025-12-05 16:51:32 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
    2025-12-05 16:51:32 INFO     [orchestrator]           Loading python file .sane/mango/hosts/desert.py as 'mango.hosts.desert'
    2025-12-05 16:51:32 INFO     [orchestrator]           Loading python file patch/desert_valley.py as 'desert_valley'
    2025-12-05 16:51:32 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator::patch]    Processing patches from patch/valley_growth.jsonc
    2025-12-05 16:51:32 INFO     [orchestrator::patch]      Applying patch to Host 'forest'
    2025-12-05 16:51:32 INFO     [forest::patch]              Applying patch to Environment 'valley'
    2025-12-05 16:51:32 WARNING  [orchestrator::patch]      Host 'host-does-not-exist' does not exist, cannot patch
    2025-12-05 16:51:32 INFO     [sane_runner]            Changing all actions output to verbose
    2025-12-05 16:51:32 INFO     [orchestrator]           No previous save file to load
    2025-12-05 16:51:32 INFO     [orchestrator]           Running actions:
    2025-12-05 16:51:32 INFO     [orchestrator]             harvest_action  grow_action     
    2025-12-05 16:51:32 INFO     [orchestrator]           and any necessary dependencies
    2025-12-05 16:51:32 INFO     [orchestrator]           Full action set:
    2025-12-05 16:51:32 INFO     [orchestrator]             grow_action     harvest_action  
    2025-12-05 16:51:32 INFO     [orchestrator]           Checking host "desert"
    2025-12-05 16:51:32 INFO     [orchestrator]           Running as 'desert'
    2025-12-05 16:51:32 INFO     [orchestrator]           Checking ability to run all actions on 'desert'...
    2025-12-05 16:51:32 INFO     [orchestrator]             Checking environments...
    2025-12-05 16:51:32 INFO     [orchestrator]             Checking resource availability...
    2025-12-05 16:51:32 CRITICAL [desert]                       Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 50, used: 0 }}
    Traceback (most recent call last):

      File "/home/aislas/sane_workflows/bin/sane_runner.py", line 322, in <module>
        main()

      File "/home/aislas/sane_workflows/bin/sane_runner.py", line 305, in main
        success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )

      File "/home/aislas/sane_workflows/sane/orchestrator.py", line 529, in run_actions
        self.check_host( traversal_list )

      File "/home/aislas/sane_workflows/sane/orchestrator.py", line 465, in check_host
        can_run = host.resources_available( self.actions[node].resources( self.current_host ), requestor=self.actions[node] )

      File "/home/aislas/sane_workflows/sane/resources.py", line 637, in resources_available
        raise Exception( msg )

    Exception: Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 50, used: 0 }}

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/python_desert_patch/.sane/``

Our "patch" python file does in fact get loaded after ``.sane/mango/hosts/desert.py``!
We got a *little* bit further, but now we see the err of our ways in not adding
the appriopriate resources. How would we ever grow mangos on ``"cacti"``?!?


Python Modules
--------------
The final beginner section of the tutorial will cover how to reference python files
within other python files in your workflow.

For this example, we shall have some really useful helper functions in ``.sane/custom/funcs.py``:

.. literalinclude:: ../../examples/mango/python_imports/.sane/mango/custom/funcs.py
    :language: python
    :caption: .sane/mango/custom/funcs.py

And let's modify our ``"desert"`` host to use this function:

.. literalinclude:: ../../examples/mango/python_imports/.sane/mango/hosts/desert.py
    :language: python
    :caption: .sane/mango/hosts/desert.py
    :emphasize-lines: 3

Now if we run this:

.. code-block:: none
    :emphasize-lines: 14

    sane_runner -p .sane/ -n -r -sh sahara -v

    2025-12-05 17:24:58 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-05 17:24:58 INFO     [orchestrator]           Searching for workflow files...
    2025-12-05 17:24:58 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-05 17:24:58 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-05 17:24:58 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/hosts/desert.py
    2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/actions/harvest.py
    2025-12-05 17:24:58 INFO     [orchestrator]               Found .sane/mango/custom/funcs.py
    2025-12-05 17:24:58 INFO     [orchestrator]           Loading python file .sane/mango/hosts/desert.py as 'mango.hosts.desert'
    2025-12-05 17:24:58 INFO     [orchestrator]           Loading python file .sane/mango/actions/harvest.py as 'mango.actions.harvest'
    2025-12-05 17:24:58 INFO     [orchestrator]           Loading python file .sane/mango/custom/funcs.py as 'mango.custom.funcs'
    2025-12-05 17:24:58 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-05 17:24:58 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-05 17:24:58 INFO     [sane_runner]            Changing all actions output to verbose
    2025-12-05 17:24:58 INFO     [orchestrator]           No previous save file to load
    2025-12-05 17:24:58 INFO     [orchestrator]           Running actions:
    2025-12-05 17:24:58 INFO     [orchestrator]             harvest_action  grow_action     
    2025-12-05 17:24:58 INFO     [orchestrator]           and any necessary dependencies
    2025-12-05 17:24:58 INFO     [orchestrator]           Full action set:
    2025-12-05 17:24:58 INFO     [orchestrator]             grow_action     harvest_action  
    2025-12-05 17:24:58 INFO     [orchestrator]           Checking host "sonoran"
    2025-12-05 17:24:58 INFO     [orchestrator]           Checking host "sahara"
    2025-12-05 17:24:58 INFO     [orchestrator]           Running as 'sahara'
    2025-12-05 17:24:58 INFO     [orchestrator]           Checking ability to run all actions on 'sahara'...
    2025-12-05 17:24:58 INFO     [orchestrator]             Checking environments...
    2025-12-05 17:24:58 INFO     [orchestrator]             Checking resource availability...
    2025-12-05 17:24:58 CRITICAL [sahara]                       Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 0, used: 0 }}
    Traceback (most recent call last):

      File "/home/aislas/frameflow/bin/sane_runner.py", line 322, in <module>
        main()

      File "/home/aislas/frameflow/bin/sane_runner.py", line 305, in main
        success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )

      File "/home/aislas/frameflow/sane/orchestrator.py", line 529, in run_actions
        self.check_host( traversal_list )

      File "/home/aislas/frameflow/sane/orchestrator.py", line 465, in check_host
        can_run = host.resources_available( self.actions[node].resources( self.current_host ), requestor=self.actions[node] )

      File "/home/aislas/frameflow/sane/resources.py", line 637, in resources_available
        raise Exception( msg )

    Exception: Will never be able to acquire resource 'trees' : 4, host does not possess this resource. Resources: {'cacti': { total: 0, used: 0 }}

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/python_imports/.sane/``

We still have no trees, **but** our ``"cacti"`` amount corresponds to the ``.sane/mango/custom/funcs.py``
``num_cacti_in_region()`` function. Note that even though the ``.sane/mango/custom/funcs.py``
module is loaded after the ``mango.hosts.desert`` module, the import still happens correctly.

This is because anything provided as a ``-p``/``--path`` argument is added to the
`sys.path`_ for module searching. So ``.sane/mango/custom/funcs.py`` can be imported
in our ``desert.py`` file as ``mango.custom.funcs``.

.. toctree::
   :maxdepth: 2
