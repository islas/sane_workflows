JSON Interface
==============
.. py:module:: sane
    :no-index:

The JSON interface of SANE workflows is the simplest to use
for default class declarations.

It provides rich control over the default classes provided,
and allows using custom classes that add support for the
JSON interface.

Firstly, it is **important** to note that *ALL* files (JSON or python)
are only ever loaded by the :py:class:`Orchestrator`. JSON files
specifically are loaded via the :py:meth:`Orchestrator.load_core_config`
function. Let's take a look at that here for reference:

.. automethod:: sane.Orchestrator.load_core_config
    :no-index:

JSON files for SANE workflows are always composed of three optional
keys within the root dictionary:

* ``"hosts"``
* ``"actions"``
* ``"patches"``

The ``"patches"`` dictionary mirrors the layout of the parent JSON
dictionary, except that ``"type"`` is no longer valid in any referenced
host or action.

Within the ``"hosts"`` and ``"actions"`` dictionaries, unique keys
are used as the names or ids for the underlying objects they will
create. The valid dictionary values of the  unique key name/id are
left without much specification because the ``"type"`` key may change
what is even allowed, as we will see later in the :ref:`advanced.custom_classes`
section.

For now, we will assume we are using the default classes, we can
use their respective ``load_core_config``. Let's start making some
file content.

Hosts
-----
To begin our workflow, let's create the ``.sane/mango/hosts/forest.jsonc``
file and create a host in this file. We will start by writing the body
of the :py:meth:`Orchestrator.load_core_config` layout:

.. literalinclude:: ../../examples/mango/json_bare_host/.sane/mango/hosts/forest.jsonc
    :caption: .sane/mango/hosts/forest.jsonc
    :language: json


Well, now we have an host! All keys in the default :py:meth:`Host.load_core_config`
are optional, so this is a valid host, but not very useful...

.. hint:: Actually, all keys across all default classes are always optional.

We could run our workflow now and get:

.. code-block:: none

    sane_runner -p .sane

    2025-12-05 11:49:48 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-05 11:49:48 INFO     [orchestrator]           Searching for workflow files...
    2025-12-05 11:49:48 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-05 11:49:48 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-05 11:49:48 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-05 11:49:48 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-05 11:49:48 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-05 11:49:48 INFO     [sane_runner]            No actions selected
    ...help message because we have no actions..

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/json_bare_host/.sane/``

Let's take a look at the :py:meth:`Host.load_core_config` to get an
idea of what values we can use in the host config section:

.. automethod:: Host.load_core_config
    :no-index:

We can see that we have quite a few config options, aggregated from different sources:

From :py:meth:`Host.load_core_config`:

* ``"aliases"``
* ``"default_env"``
* ``"config"`` (see :py:attr:`Host.config` for disambiguation)
* ``"base_env"``
* ``"environments"``

From :py:meth:`ResourceProvider.load_core_config`:

* ``"resources"``
* ``"mapping"``

That is a lot of options, so make this introduction simple we will focus on
the key options that will make this host useful: ``"environments"`` and ``"resources"``.

Resources & Environment
^^^^^^^^^^^^^^^^^^^^^^^
For ``"resources"`` we see that it is a ``dict`` that uses :py:attr:`sane.resources.Resource`
syntax. The simple explanation is that the resource must be a non-negative integer
followed by optional binary scaling ( 'k' : 1024, 'm' : 1024 :sup:`2`, and so on), and
an optional unit designator.

We will add ``"resources" : {  "trees" : 12 }`` to our host.

Next, we need an environment. We see once again that the details of the
environment config are sparse due to a ``"type"`` specification. Let's
assume we are using the default :py:class:`Environment.load_core_config`:

.. automethod:: Environment.load_core_config
    :no-index:

.. important:: Currently, actions *ALWAYS* need to run with an :py:class:`Environment` set up.
               Therefore, hosts **must** have at least one :py:class:`Environment` declared
               that isn't the :py:attr:`~Host.base_env`

A lot of config option again:

* ``"aliases"``
* ``"lmod_path"``
* ``"env_vars"``
* ``"lmod_cmds"``
* ``"env_scripts"``

To maintain the simple approach for now, we will only use ``"env_vars"``.
Our ``.sane/mango/hosts/forest.jsonc`` should now look like:

.. literalinclude:: ../../examples/mango/json_grow_action/.sane/mango/hosts/forest.jsonc
    :language: json
    :caption: .sane/mango/hosts/forest.jsonc

We now have a functional host. Again, it can't do a whole lot without an :py:class:`Action`
to exercise the host and its environments.

.. _json.actions:

Actions
-------
We will now create our first action in the ``.sane/mango/actions/grow.jsonc`` file.
Similar to what we've done previously, let us look at the :py:meth:`Action.load_core_config`:

.. automethod:: Action.load_core_config
    :no-index:

Our options are...
From :py:meth:`Action.load_core_config`:

* ``"environment"``
* ``"working_directory"``
* ``"config"``
* ``"dependencies"``

From :py:meth:`ResourceRequestor.load_core_config`:

* ``"resources"``
* ``"local"``

Since we are using the default :py:meth:`Action.run()` we should use ``"config"``
to pass in a ``"command"`` and ``"arguments"`` to execute. Additionally, since
we did not provide a :py:attr:`~Host.default_env` to the host declaration, we will
need to make sure this action specifies an environment name. Finally, while we do
not necessarily need to list resources, it may be a good idea if this action does
in fact use some.

We will ignore all other options for now.

Our ``.sane/mango/actions/grow.jsonc`` will look like:

.. literalinclude:: ../../examples/mango/json_grow_action/.sane/mango/actions/grow.jsonc
    :caption: .sane/actions/grow.jsonc
    :language: json

We are going to use the helper script located at ``.sane/scripts.grow.sh`` to
perform our main logic. This thereby allows us to have an :py:class:`Action` with
customizable execution without needing to write :ref:`advanced.custom_actions`. The
path we use to the script should be a relative path from the working directory, in
this case ``./``. Only use absolute paths for scripts that will always be in the
same place (e.g. host scripts)!

While we could have complex logic for ``.sane/scripts/grow.sh``, for now
we will use the following content:

.. literalinclude:: ../../examples/mango/json_grow_action/.sane/scripts/grow.sh
    :caption: .sane/scripts/grow.sh
    :language: bash

.. note:: The ``config["command"]`` must be an executable file. Make sure to run
          ``chmod +x .sane/scripts/grow.sh``!

Now we can run this action on the host we created. We will use the :ref:`running.specific_host`
option to avoid the default FQDN match behavior so that this runs on any machine
(see :py:attr:`valid_host` for more info).

Our output would look like:

.. code-block:: none

    sane_runner -p .sane --specific_host forest --run

    2025-12-05 12:26:17 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-05 12:26:17 INFO     [orchestrator]           Searching for workflow files...
    2025-12-05 12:26:17 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-05 12:26:17 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-05 12:26:17 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-05 12:26:17 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-05 12:26:17 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-05 12:26:17 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-05 12:26:17 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-05 12:26:17 INFO     [orchestrator]           No previous save file to load
    2025-12-05 12:26:17 INFO     [orchestrator]           Running actions:
    2025-12-05 12:26:17 INFO     [orchestrator]             grow_action  
    2025-12-05 12:26:17 INFO     [orchestrator]           and any necessary dependencies
    2025-12-05 12:26:17 INFO     [orchestrator]           Full action set:
    2025-12-05 12:26:17 INFO     [orchestrator]             grow_action  
    2025-12-05 12:26:17 INFO     [orchestrator]           Checking host "forest"
    2025-12-05 12:26:17 INFO     [orchestrator]           Running as 'forest'
    2025-12-05 12:26:17 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2025-12-05 12:26:17 INFO     [orchestrator]             Checking environments...
    2025-12-05 12:26:17 INFO     [orchestrator]             Checking resource availability...
    2025-12-05 12:26:17 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-05 12:26:17 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * * 
    2025-12-05 12:26:17 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-05 12:26:17 INFO     [orchestrator]           Saving host information...
    2025-12-05 12:26:17 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2025-12-05 12:26:17 INFO     [orchestrator]           No previous save file to load
    2025-12-05 12:26:17 INFO     [orchestrator]           Using working directory : '/home/aislas/mango'
    2025-12-05 12:26:17 INFO     [orchestrator]           Running actions...
    2025-12-05 12:26:17 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2025-12-05 12:26:17 INFO     [thread_0]  [grow_action::launch]      Saving action information for launch...
    2025-12-05 12:26:17 INFO     [thread_0]  [grow_action::launch]      Using working directory : '/home/aislas/mango'
    2025-12-05 12:26:17 INFO     [thread_0]  [grow_action::launch]      Running command:
    2025-12-05 12:26:17 INFO     [thread_0]  [grow_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_grow_action.json
    2025-12-05 12:26:17 INFO     [thread_0]  [grow_action::launch]      Command output will be captured to logfile /home/aislas/mango/log/grow_action.log
    2025-12-05 12:26:17 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2025-12-05 12:26:17 INFO     [orchestrator]           Finished running queued actions
    2025-12-05 12:26:17 INFO     [orchestrator]             grow_action: success  
    2025-12-05 12:26:17 INFO     [orchestrator]           All actions finished with success
    2025-12-05 12:26:17 INFO     [orchestrator]           Finished in 0:00:00.262162
    2025-12-05 12:26:17 INFO     [orchestrator]           Save file at /home/aislas/mango/tmp/orchestrator.json
    2025-12-05 12:26:17 INFO     [orchestrator]           JUnit file at /home/aislas/mango/log/results.xml
    2025-12-05 12:26:17 INFO     [sane_runner]            Finished

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/json_grow_action/.sane/``

The output of our :py:class:`Action.run()` is stored in the logfile, where the stdout
of our shell script is wrapped in ``<timestamp> STDOUT [context]``:

.. code-block:: none

  2025-12-05 12:26:17 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
  2025-12-05 12:26:17 INFO     [grow_action::launch]    Current directory: /home/aislas/mango
  2025-12-05 12:26:17 INFO     [grow_action::launch]    Loaded Action "grow_action"
  2025-12-05 12:26:17 INFO     [grow_action::launch]    Loaded Host "forest"
  2025-12-05 12:26:17 INFO     [grow_action::launch]    Using Environment "valley"
  2025-12-05 12:26:17 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
  2025-12-05 12:26:17 INFO     [valley]                   Environment variable GROWTH_RATE=85
  2025-12-05 12:26:17 INFO     [grow_action::run]       Running command:
  2025-12-05 12:26:17 INFO     [grow_action::run]         .sane/scripts/grow.sh 4
  2025-12-05 12:26:17 INFO     [grow_action::run]       Command output will be printed to this terminal
  2025-12-05 12:26:17 STDOUT   [grow_action::run]       Growing with 4 trees with 85% growth rate...
  2025-12-05 12:26:17 STDOUT   [grow_action::run]         Tree 1 grew 6 mangos!
  2025-12-05 12:26:17 STDOUT   [grow_action::run]         Tree 2 grew 5 mangos!
  2025-12-05 12:26:17 STDOUT   [grow_action::run]         Tree 3 grew 8 mangos!
  2025-12-05 12:26:17 STDOUT   [grow_action::run]         Tree 4 grew 6 mangos!
  2025-12-05 12:26:17 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************

Patching
--------
To get an idea of how we might incorporate patches, let's pretend we want to modify
our ``GROWTH_RATE`` in our ``"valley"`` environment temporarily without touching the
original host file. Also, we can include a host key that doesn't exist to see what happens:

.. literalinclude:: ../../examples/mango/json_grow_action/patch/valley_growth.jsonc
    :caption: patch/valley_growth.jsonc
    :language: bash

Running with this patch path added we would get:

.. code-block:: none
    :emphasize-lines: 17-20, 55-56, 60

    sane_runner -p .sane/ --specific_host forest --run -p patch/ -v -n

    2025-12-05 14:25:25 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-05 14:25:25 INFO     [orchestrator]           Searching for workflow files...
    2025-12-05 14:25:25 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-05 14:25:25 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-05 14:25:25 INFO     [orchestrator]             Searching patch/ for *.json
    2025-12-05 14:25:25 INFO     [orchestrator]             Searching patch/ for *.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator]               Found patch/valley_growth.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator]             Searching patch/ for *.py
    2025-12-05 14:25:25 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator::patch]    Processing patches from patch/valley_growth.jsonc
    2025-12-05 14:25:25 INFO     [orchestrator::patch]      Applying patch to Host 'forest'
    2025-12-05 14:25:25 INFO     [forest::patch]              Applying patch to Environment 'valley'
    2025-12-05 14:25:25 WARNING  [orchestrator::patch]      Host 'host-does-not-exist' does not exist, cannot patch
    2025-12-05 14:25:25 INFO     [sane_runner]            Changing all actions output to verbose
    2025-12-05 14:25:25 INFO     [orchestrator]           No previous save file to load
    2025-12-05 14:25:25 INFO     [orchestrator]           Running actions:
    2025-12-05 14:25:25 INFO     [orchestrator]             grow_action  
    2025-12-05 14:25:25 INFO     [orchestrator]           and any necessary dependencies
    2025-12-05 14:25:25 INFO     [orchestrator]           Full action set:
    2025-12-05 14:25:25 INFO     [orchestrator]             grow_action  
    2025-12-05 14:25:25 INFO     [orchestrator]           Checking host "forest"
    2025-12-05 14:25:25 INFO     [orchestrator]           Running as 'forest'
    2025-12-05 14:25:25 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2025-12-05 14:25:25 INFO     [orchestrator]             Checking environments...
    2025-12-05 14:25:25 INFO     [orchestrator]             Checking resource availability...
    2025-12-05 14:25:25 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-05 14:25:25 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * * 
    2025-12-05 14:25:25 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-05 14:25:25 INFO     [orchestrator]           Saving host information...
    2025-12-05 14:25:25 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2025-12-05 14:25:25 INFO     [orchestrator]           No previous save file to load
    2025-12-05 14:25:25 INFO     [orchestrator]           Using working directory : '/home/aislas/mango'
    2025-12-05 14:25:25 INFO     [orchestrator]           Running actions...
    2025-12-05 14:25:25 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Saving action information for launch...
    2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Using working directory : '/home/aislas/mango'
    2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Running command:
    2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_grow_action.json
    2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Command output will be printed to this terminal
    2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Command output will be captured to logfile /home/aislas/mango/log/grow_action.log
    2025-12-05 14:25:26 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
    2025-12-05 14:25:26 INFO     [grow_action::launch]    Current directory: /home/aislas/mango
    2025-12-05 14:25:26 INFO     [grow_action::launch]    Loaded Action "grow_action"
    2025-12-05 14:25:26 INFO     [grow_action::launch]    Loaded Host "forest"
    2025-12-05 14:25:26 INFO     [grow_action::launch]    Using Environment "valley"
    2025-12-05 14:25:26 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2025-12-05 14:25:26 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2025-12-05 14:25:26 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '400'
    2025-12-05 14:25:26 INFO     [valley]                   Environment variable GROWTH_RATE=400
    2025-12-05 14:25:26 INFO     [grow_action::run]       Running command:
    2025-12-05 14:25:26 INFO     [grow_action::run]         .sane/scripts/grow.sh 4
    2025-12-05 14:25:26 INFO     [grow_action::run]       Command output will be printed to this terminal
    2025-12-05 14:25:26 STDOUT   [grow_action::run]       Growing with 4 trees with 400% growth rate...
    2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 1 grew 37 mangos!
    2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 2 grew 1 mangos!
    2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 3 grew 9 mangos!
    2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 4 grew 37 mangos!
    2025-12-05 14:25:26 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
    2025-12-05 14:25:26 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2025-12-05 14:25:26 INFO     [orchestrator]           Finished running queued actions
    2025-12-05 14:25:26 INFO     [orchestrator]             grow_action: success  
    2025-12-05 14:25:26 INFO     [orchestrator]           All actions finished with success
    2025-12-05 14:25:26 INFO     [orchestrator]           Finished in 0:00:00.194862
    2025-12-05 14:25:26 INFO     [orchestrator]           Save file at /home/aislas/mango/tmp/orchestrator.json
    2025-12-05 14:25:26 INFO     [orchestrator]           JUnit file at /home/aislas/mango/log/results.xml
    2025-12-05 14:25:26 INFO     [sane_runner]            Finished

.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/json_grow_action/.sane/``

.. hint:: The ``-v``/``--verbose`` flag copies the :py:meth:`Action.run()` output to
          the main output. The ``-n``/``--new`` flag forces a new workflow run evaluation.
          See :doc:`../user_guide/running` for more info.

Looking at the three highlighted regions, we can see some new effects:

* A new ``[<context>::patch]`` section appears in loading & processing

  * Our patch is applied under ``"forest"`` :py:class:`Host` to the ``"valley"`` :py:class:`Environment`
  * The nonexistent host patch produces a ``WARNING``
* The ``"env_vars"`` patch is applied *after* the previous setting, it does not replace it (see :py:meth:`Environment.setup_env_vars` for more info)
* We grew our mangos with ``400%``!

.. toctree::
   :maxdepth: 2
