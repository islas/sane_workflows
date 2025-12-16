JSON Interface
==============
.. |alt_doc| replace:: :doc:`python`
.. include:: common/primer.rst

Preface
-------
The JSON interface of SANE workflows is minimal, but provides rich control
over the default classes provided, and allows using custom classes that
add support for the JSON interface.

.. collapse:: Confused about *how* are JSON files loaded? Better yet, what is a JSON file?

    .. tip:: JSON loading of files relies on the :external:py:mod:`json` python
            module. Reading in JSON files, the **files are read one-to-one as
            simple python objects** ( ``{}`` as ``dict``, ``[]`` as ``list``,
            ``""`` as ``str``, and ``#`` as ``int``)

            A JSON file itself is nothing more than a *"file format ... to store
            and transmit data objects"*, the contents of which are decided by us.
            See https://en.wikipedia.org/wiki/JSON for more detail.

|

.. attention:: Much like the python interface, it will be important to understand
               at a very high level our entry point.

               *ALL* files (JSON or python) are only ever loaded by the 
               :py:class:`Orchestrator`. JSON files specifically are read in via
               the :py:meth:`Orchestrator.load_config_files` function. All subsequent
               loading functions (``load_core_options``) operates only on the specific
               subsections of the file they are provided.

As we go through this section of the tutorial, we will go over various ``load_core_options``
functions that digest information from our config files. To prepare us, we will
briefly look at an example JSON file. **For now, do not worry about understanding the content**,
and instead :bolditalic:`focus on layout`:

.. code-block:: json
    :caption: Example config file
    :name: Example config file

    // Section A: Everything between these {} will be loaded as options
    // by Orchestrator.load_core_options()
    {
      "hosts" :
      {
        // Section B: Everything between {} for each <key> : { <value> } will be loaded by <type>.load_core_options()
     // <key>            : { <value> }
     // vvvvvvvvv            vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        "my_host"        : { "type" : "sane.Host", "resources" : { "cpus" : 12 } },
        "my_larger_host" : { "type" : "sane.Host", "resources" : { "cpus" : 24 } }
      },
      "actions" :
      {
        // Section B again
        "my_action" :
        {
          "type" : "sane.Action",
          "resources" : { "cpus" : 8 },
          "config" : { "command" : "script.sh", "arguments" : [ 1, 2, 3 ] }
        }
      }
      "patches" :
      {
        "priority" : 0,
        "hosts"   :
        {
          // Section C: Everything between {} for each value will be loaded by respective load_core_options()
          "my_larger_host" : { "resources" : { "gpus" : 1 } }
        }
        "actions" :
        {
          // Section C again
          "my_action"  : { "config" : { "arguments" : [ 3, 2, 1 ] } }
        }
      }
    }

Reviewing the example above:

* ``Section A`` is the entire config file top-level ``{}`` that is further digested
  into smaller subsections of options
* ``Section B`` breaks out the ``{ <value> }`` in ``"<key>" : { <value> }`` pairs
  that will be loaded as a subsection by ``<type>.load_core_options()``
* ``Section C*`` is similar to ``Section B`` but ``type`` is not used

If this doesn't make sense, **don't worry**. This is just an overview to gain context
before the walkthrough.

.. _config disambiguation:

.. admonition:: ``config`` disambiguation
    :class: tip

    We will often refer to a ``config`` being used within the :py:class:`Action`.
    Do not confuse this with the *config file* itself.

    The :py:attr:`Action.config` is a generalized container to hold data in the
    object instance, whereas the *config file* is just the set of options read in.

    The :py:attr:`Action.config` will always be referred to with ``code`` or
    :py:attr:`reference link <Action.config>` styling.

Orchestrator
------------
The primary loading function is :py:meth:`Orchestrator.load_core_options`. You
**do not need to call this function**, however it is noted here as the values
this method loads are the primary way we interact with the JSON interface.

This function will take the entire *options* ``dict`` of the JSON file and attempt
to load valid keys. Thus, this is effectively the functions that determines the
top-level structure of these JSON config files.

Below is a quick look at the function:

.. collapse:: Quick Reference (click to open/close)

  .. automethod:: Orchestrator.load_core_options
      :no-index:

|

Using the above *Quick Reference* or `Example config file`_ as guidance:

JSON files for SANE workflows are always composed of three optional
keys within the root dictionary:

* ``"hosts"``
* ``"actions"``
* ``"patches"``

The ``"patches"`` dictionary mirrors the layout of the parent JSON
dictionary, except that ``"type"`` is no longer valid in any referenced
host or action (and you can't have more nested ``"patches"``).

Within the ``"hosts"`` and ``"actions"`` dictionaries, the unique keys are used
as the ``name`` or ``id`` for the underlying objects they will create. The valid
fields inside the corresponding *options* ``{ <value> }`` of the  unique key name/id
are left without much specification because the ``"type"`` key may change how that
*options* subsection is loaded, as we will see later in the :ref:`advanced.custom_classes`
section.

For now, we will assume we are using the default classes. We then can simply use
their respective ``load_core_options``. Let's start making some file content.

.. _separate config files:

.. admonition:: Separate config files?
    :class: hint

    Since all *options* at the top-level are optional, we can categorically
    organize our config files to contain different subsections. The separate files
    will each be processed into the :py:class:`Orchestrator` cummulatively, building
    up the workflow definition piecemeal.

Hosts
-----
To begin our workflow, let's create the ``.sane/mango/hosts/forest.jsonc``
file and create a host in this file.

.. code-block:: none
    :emphasize-lines: 4

    .sane/
    └── mango
        └── hosts
            └── forest.jsonc

We will start by creating a :py:class:`Host` *options* under the ``"hosts"`` key.
Recall that the unique key under ``"hosts"`` acts as the :py:attr:`Host.name`.

.. code-block:: json
    :caption: ``.sane/mango/hosts/forest.jsonc``

    {
      "hosts" :
      {
        "forest" :
        {
          //...what to put here...
        }
      }
    }

.. include:: common/host_trans_details.rst

To find what fields/keys
to put in our ``"forest"`` *options* ``{ <value> }`` area,
let's take a quick look at the :py:meth:`Host.load_core_options`:

.. collapse:: Quick Reference (click to open/close):

  .. automethod:: Host.load_core_options
      :no-index:

|

Some interesting things to note about the keys available to us:

* All keys are optional (this is the case for all default classes)
* Support for different keys is provided via subclass calls implementing their own ``load_core_options``:

  * Keys supported by other subclasses are aggregates (not replacements) to the supported key list

.. hint:: All keys across all default classes are always optional.

Thus, taking into account all suported key aggregated from the different classes
we can see that we have quite a few *options* options:

  From :py:meth:`Host.load_core_options`:

  * ``"aliases"``
  * ``"default_env"``
  * ``"config"`` (see :py:attr:`Host.config` or `config disambiguation`_ for disambiguation)
  * ``"base_env"``
  * ``"environments"``

  From :py:meth:`ResourceProvider.load_core_options <resources.ResourceProvider.load_core_options>`:

  * ``"resources"``
  * ``"mapping"``

That is a lot of options, so make this introduction simple we will focus on
the key options that will make this host useful: ``"environments"`` and ``"resources"``.

Resources & Environment
^^^^^^^^^^^^^^^^^^^^^^^
Maps:

* ``"resources"`` to :py:meth:`Host.add_resources` / :py:attr:`Host.resources`
* ``"environments"`` to :py:meth:`Host.add_environment` / :py:attr:`Host.environments`

Let's take a second to look at the *options* documentation for ``"resources"``.

.. include:: common/host_res.rst

.. code-block:: json
    :caption: ``.sane/mango/hosts/forest.jsonc``

    {
      "hosts" :
      {
        "forest" :
        {
          "resources" :
          {
            // this coud be cpus but we'll use trees because
            // that is where mangos grow
            "trees" : 12
          }
        }
      }
    }

Next, we need an :py:class:`Environment` *options*.

.. include:: common/env_admon_req.rst

We see once again that the details of the environment *options* are sparse due to
a ``"type"`` specification, similar to the one used under ``"hosts"`` and ``"actions"``
*configs*. Likewise, if no ``"type"`` is specified, the internal default class is
used. 

Therefore, let's assume we are using the default :py:class:`Environment.load_core_options`:

.. collapse:: Quick Reference (click to open/close):

  .. automethod:: Environment.load_core_options
      :no-index:

|

A lot of *options* option again:

* ``"aliases"``
* ``"lmod_path"``
* ``"env_vars"``
* ``"lmod_cmds"``
* ``"env_scripts"``

.. include:: common/env_var_demo.rst

To do this and maintain the simple approach for now, we will only use ``"env_vars"``
under our unique keys that create our :py:class:`Environment`.

Our ``.sane/mango/hosts/forest.jsonc`` should now look like:

.. literalinclude:: ../../examples/mango/json_basic_host/.sane/mango/hosts/forest.jsonc
    :caption: .sane/mango/hosts/forest.jsonc
    :language: json
    :name: forest.jsonc

.. include:: common/host_uneventful.rst

.. code-block:: none
    :emphasize-lines: 7

    sane_runner -p .sane/ -n -sh forest -v --run

    2025-12-12 17:33:31 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-12 17:33:31 INFO     [orchestrator]           Searching for workflow files...
    2025-12-12 17:33:31 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-12 17:33:31 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-12 17:33:31 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-12 17:33:31 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-12 17:33:31 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-12 17:33:31 INFO     [sane_runner]            No actions selected
    ...help info...

.. tip:: This output can be reproduced by using the source repo example found at
         ``/home/aislas/frameflow/docs/examples/mango/json_basic_host/.sane``

The default search patterns found our file and loaded it, but nothing was done since
no actions were found.

.. _json.actions:

Actions
-------
Let's now try to create our first JSON-based :py:class:`Action`!

We will create the ``.sane/mango/actions/grow.jsonc`` file, as well as create a helper
script at ``.sane/scripts/grow.sh``:

.. code-block:: none
    :emphasize-lines: 4, 8

    .sane/
    ├── mango
    │   ├── actions
    │   │   └── grow.jsonc
    │   └── hosts
    │       └── forest.jsonc
    └── scripts
        └── grow.sh

Confused as to how we are able to use separate files? See the `separate config files`_
tip for clarification.

We will start by creating our ``.sane/mango/actions/grow.jsonc`` file:

.. code-block:: python
    :caption: ``.sane/mango/actions/grow.jsonc``

    {
      "actions" :
      {
        "grow_action" :
        {
          //...
        }
      }
    }

Similar to what we've done previously, let us look at the :py:meth:`Action.load_core_options`:

.. collapse:: Quick Reference (click to open/close):

  .. automethod:: Action.load_core_options
      :no-index:

|

To quickly summarize, the :py:meth:`Action.load_core_options` supports:

  From :py:meth:`Action.load_core_options`:

  * ``"environment"``
  * ``"working_directory"``
  * ``"config"``
  * ``"dependencies"``

  From :py:meth:`ResourceRequestor.load_core_options <resources.ResourceRequestor.load_core_options>`:

  * ``"resources"``
  * ``"local"``

Most important to us will be:

* ``"config"``
* ``"environment"``
* ``"resources"``
* ``"dependencies"`` (covered later)

We shall go over relevance of each of these.

``"config"``
^^^^^^^^^^^^
Maps to :py:attr:`Action.config` (see `config disambiguation`_)

.. include:: common/act_config.rst

Let's quickly modify our ``.sane/mango/actions/grow.jsonc``:

.. code-block:: json
    :caption: ``.sane/mango/actions/grow.jsonc``

    {
      "actions" :
      {
        "grow_action" :
        {
          "config" :
          {
            "command" : ".sane/scripts/grow.sh",
            // this must be a list
            "arguments" : [ 4 ]
          }
        }
      }
    }

As for the contents of ``.sane/mango/scripts/grow.sh`` let's use:

.. literalinclude:: ../../examples/mango/json_grow_action/.sane/mango/scripts/grow.sh
    :caption: ``.sane/mango/scripts/grow.sh``
    :language: bash

.. include:: common/act_admon_cmd.rst

``"environment"``
^^^^^^^^^^^^^^^^^
Maps to :py:attr:`Action.environment`

.. include:: common/act_env.rst

Let's update our ``.sane/mango/actions/grow.jsonc`` again, saying we need a ``"valley"``
environment (recall `forest.jsonc`_):

.. code-block:: json
    :caption: ``.sane/mango/actions/grow.jsonc``

    {
      "actions" :
      {
        "grow_action" :
        {
          "config" :
          {
            "command" : ".sane/scripts/grow.sh",
            // this must be a list
            "arguments" : [ 4 ]
          },
          "environment": "valley"
        }
      }
    }

``"resources"``
^^^^^^^^^^^^^^^
Maps to :py:meth:`Action.add_resource_requirements` / :py:attr:`Action.resources`

.. include:: common/act_res.rst

To grow our *mangos* we will need ``"trees"`` (recall `forest.jsonc`_):

.. literalinclude:: ../../examples/mango/json_grow_action/.sane/mango/actions/grow.jsonc
    :caption: .sane/actions/grow.jsonc
    :language: json

``"dependencies"``
^^^^^^^^^^^^^^^^^^
Maps to :py:meth:`Action.add_dependencies` / :py:attr:`Action.dependencies`

This is the first :py:class:`Action` in our workflow, so it will not have any
dependencies. See the :ref:`json.adding_deps` for details on adding dependencies.


Final :py:class:`Action` Result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Our final ``.sane/mango/actions/grow.jsonc`` should now look like:

.. literalinclude:: ../../examples/mango/json_grow_action/.sane/mango/actions/grow.jsonc
    :language: json
    :caption: ``.sane/actions/grow.jsonc``
    :name: grow.jsonc



Running
-------

Now that we have everything set up, we should be able to run. We will be using the
following *optional* flags:

* ``-sh`` :ref:`running.specific_host` option to ensure our host is selected
* ``-n`` :ref:`New Run <running.saves>` option to always rerun our workflow entirely
* ``-v``  :ref:`running.verbose` option to get full output in one location rather than split amongst multiple files

.. code-block:: none
    :emphasize-lines: 7-8, 10-11, 32, 42-44, 48, 50-54, 61-63

    sane_runner -p .sane/ -sh forest -n -v -r

    2025-12-12 19:58:08 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-12 19:58:08 INFO     [orchestrator]           Searching for workflow files...
    2025-12-12 19:58:08 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-12 19:58:08 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-12 19:58:08 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-12 19:58:08 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-12 19:58:08 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-12 19:58:08 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-12 19:58:08 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-12 19:58:08 INFO     [orchestrator]           No previous save file to load
    2025-12-12 19:58:08 INFO     [orchestrator]           Requested actions:
    2025-12-12 19:58:08 INFO     [orchestrator]             grow_action  
    2025-12-12 19:58:08 INFO     [orchestrator]           and any necessary dependencies
    2025-12-12 19:58:08 INFO     [orchestrator]           Full action set:
    2025-12-12 19:58:08 INFO     [orchestrator]           Full action set:
    2025-12-12 19:58:08 INFO     [orchestrator]             grow_action  
    2025-12-12 19:58:08 INFO     [orchestrator]           Checking host "forest"
    2025-12-12 19:58:08 INFO     [orchestrator]           Running as 'forest'
    2025-12-12 19:58:08 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2025-12-12 19:58:08 INFO     [orchestrator]             Checking environments...
    2025-12-12 19:58:08 INFO     [orchestrator]             Checking resource availability...
    2025-12-12 19:58:08 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-12 19:58:08 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * * 
    2025-12-12 19:58:08 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-12 19:58:08 INFO     [orchestrator]           Saving host information...
    2025-12-12 19:58:08 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2025-12-12 19:58:08 INFO     [orchestrator]           No previous save file to load
    2025-12-12 19:58:08 INFO     [orchestrator]           Using working directory : '/home/aislas/mango'
    2025-12-12 19:58:08 INFO     [orchestrator]           Running actions...
    2025-12-12 19:58:08 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2025-12-12 19:58:08 INFO     [thread_0]  [grow_action::launch]      Action logfile captured at /home/aislas/mango/log/grow_action.log
    2025-12-12 19:58:08 INFO     [thread_0]  [grow_action::launch]      Saving action information for launch...
    2025-12-12 19:58:08 INFO     [thread_0]  [grow_action::launch]      Using working directory : '/home/aislas/mango'
    2025-12-12 19:58:08 INFO     [thread_0]  [grow_action::launch]      Running command:
    2025-12-12 19:58:08 INFO     [thread_0]  [grow_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_grow_action.json
    2025-12-12 19:58:08 INFO     [thread_0]  [grow_action::launch]      Command output will be captured to logfile /home/aislas/mango/log/grow_action.runlog
    2025-12-12 19:58:08 INFO     [thread_0]  [grow_action::launch]      Command output will be printed to this terminal
    2025-12-12 19:58:08 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
    2025-12-12 19:58:08 INFO     [grow_action::launch]    Current directory: /home/aislas/mango
    2025-12-12 19:58:08 INFO     [grow_action::launch]    Loaded Action "grow_action"
    2025-12-12 19:58:08 INFO     [grow_action::launch]    Loaded Host "forest"
    2025-12-12 19:58:08 INFO     [grow_action::launch]    Using Environment "valley"
    2025-12-12 19:58:08 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2025-12-12 19:58:08 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2025-12-12 19:58:08 INFO     [grow_action::run]       Running command:
    2025-12-12 19:58:08 INFO     [grow_action::run]         .sane/mango/scripts/grow.sh 4
    2025-12-12 19:58:08 INFO     [grow_action::run]       Command output will be printed to this terminal
    2025-12-12 19:58:08 STDOUT   [grow_action::run]       Growing with 4 trees with 85% growth rate...
    2025-12-12 19:58:08 STDOUT   [grow_action::run]         Tree 1 grew 7 mangos!
    2025-12-12 19:58:08 STDOUT   [grow_action::run]         Tree 2 grew 5 mangos!
    2025-12-12 19:58:08 STDOUT   [grow_action::run]         Tree 3 grew 6 mangos!
    2025-12-12 19:58:08 STDOUT   [grow_action::run]         Tree 4 grew 2 mangos!
    2025-12-12 19:58:08 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
    2025-12-12 19:58:08 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2025-12-12 19:58:08 INFO     [orchestrator]           Finished running queued actions
    2025-12-12 19:58:08 INFO     [orchestrator]             grow_action: success  
    2025-12-12 19:58:08 INFO     [orchestrator]           All actions finished with success
    2025-12-12 19:58:08 INFO     [orchestrator]           Finished in 0:00:00.199341
    2025-12-12 19:58:08 INFO     [orchestrator]           Logfiles at /home/aislas/mango/log
    2025-12-12 19:58:08 INFO     [orchestrator]           Save file at /home/aislas/mango/tmp/orchestrator.json
    2025-12-12 19:58:08 INFO     [orchestrator]           JUnit file at /home/aislas/mango/log/results.xml
    2025-12-12 19:58:08 INFO     [sane_runner]            Finished


.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/json_grow_action/.sane/``

.. include:: common/run_review.rst

Extending the workflow
----------------------
Now that we have a basis for creating our workflow, let's harvest our *mangos*.
We will be adding a ``.sane/mango/actions/harvest.jsonc`` file and supporting 
``.sane/mango/scripts/harvest.sh`` script:

.. code-block:: none
    :emphasize-lines: 5, 10

    .sane/
    └── mango
        ├── actions
        │   ├── grow.jsonc
        │   └── harvest.jsonc
        ├── hosts
        │   └── forest.jsonc
        └── scripts
            ├── grow.sh
            └── harvest.sh

.. _json.adding_deps:

Adding ``"dependencies"``
^^^^^^^^^^^^^^^^^^^^^^^^^
.. include:: common/act_dep.rst

If we were to add depedencies to an :py:class:`Action`, we would list the :py:attr:`Action.id`
and :py:class:`DependencyType` string value for each dependency:

.. collapse:: Quick Reference (click to open/close)

  .. autoclass:: DependencyType
      :no-index:
      :members:
      :exclude-members: __new__
      :member-order: bysource

|

.. code-block:: json
    :caption: Example JSON dependency

    // ...JSON file excerpt...
    "actions" :
    {
      "a" : {},
      "b" : { "dependencies" : { "a" : "afterok" },
      "c" : {},
      "d" : { "dependencies" : { "b" : "afterok", "c" : "afternotok" },
    }

New files
^^^^^^^^^
We can model the new ``"harvest_action"`` after the `grow.jsonc`_ example, but change a few things
such as the script we will run and adding a dependency to our initial ``"grow_action"``:

.. literalinclude:: ../../examples/mango/json_harvest_action/.sane/mango/actions/harvest.jsonc
    :language: json
    :caption: ``.sane/mango/actions/harvest.jsonc``
    :name: harvest.jsonc
    :emphasize-lines: 8, 13

And our helper script as:

.. literalinclude:: ../../examples/mango/json_harvest_action/.sane/mango/scripts/harvest.sh
    :language: bash
    :caption: ``.sane/mango/scripts/harvest.sh``

Note that we listed the dependencies using the :py:attr:`Action.id` string value.

.. include:: common/harvest_dep_caveat.rst

Let's run with new action:

.. code-block:: none
    :emphasize-lines: 59, 75, 77-78

    sane_runner -p .sane/ -sh forest -n -v -r

    2025-12-12 20:14:31 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
    2025-12-12 20:14:31 INFO     [orchestrator]           Searching for workflow files...
    2025-12-12 20:14:31 INFO     [orchestrator]             Searching .sane/ for *.json
    2025-12-12 20:14:31 INFO     [orchestrator]             Searching .sane/ for *.jsonc
    2025-12-12 20:14:31 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
    2025-12-12 20:14:31 INFO     [orchestrator]               Found .sane/mango/actions/harvest.jsonc
    2025-12-12 20:14:31 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
    2025-12-12 20:14:31 INFO     [orchestrator]             Searching .sane/ for *.py
    2025-12-12 20:14:31 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
    2025-12-12 20:14:31 INFO     [orchestrator]           Loading config file .sane/mango/actions/harvest.jsonc
    2025-12-12 20:14:31 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
    2025-12-12 20:14:31 INFO     [orchestrator]           No previous save file to load
    2025-12-12 20:14:31 INFO     [orchestrator]           Requested actions:
    2025-12-12 20:14:31 INFO     [orchestrator]             grow_action     harvest_action  
    2025-12-12 20:14:31 INFO     [orchestrator]           and any necessary dependencies
    2025-12-12 20:14:31 INFO     [orchestrator]           Full action set:
    2025-12-12 20:14:31 INFO     [orchestrator]           Full action set:
    2025-12-12 20:14:31 INFO     [orchestrator]             grow_action     harvest_action  
    2025-12-12 20:14:31 INFO     [orchestrator]           Checking host "forest"
    2025-12-12 20:14:31 INFO     [orchestrator]           Running as 'forest'
    2025-12-12 20:14:31 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
    2025-12-12 20:14:31 INFO     [orchestrator]             Checking environments...
    2025-12-12 20:14:31 INFO     [orchestrator]             Checking resource availability...
    2025-12-12 20:14:31 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-12 20:14:31 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * * 
    2025-12-12 20:14:31 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
    2025-12-12 20:14:31 INFO     [orchestrator]           Saving host information...
    2025-12-12 20:14:31 INFO     [orchestrator]           Setting state of all inactive actions to pending
    2025-12-12 20:14:31 INFO     [orchestrator]           No previous save file to load
    2025-12-12 20:14:31 INFO     [orchestrator]           Using working directory : '/home/aislas/mango'
    2025-12-12 20:14:31 INFO     [orchestrator]           Running actions...
    2025-12-12 20:14:31 INFO     [orchestrator]           Running 'grow_action' on 'forest'
    2025-12-12 20:14:31 INFO     [thread_0]  [grow_action::launch]         Action logfile captured at /home/aislas/mango/log/grow_action.log
    2025-12-12 20:14:31 INFO     [thread_0]  [grow_action::launch]         Saving action information for launch...
    2025-12-12 20:14:31 INFO     [thread_0]  [grow_action::launch]         Using working directory : '/home/aislas/mango'
    2025-12-12 20:14:31 INFO     [thread_0]  [grow_action::launch]         Running command:
    2025-12-12 20:14:31 INFO     [thread_0]  [grow_action::launch]           /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_grow_action.json
    2025-12-12 20:14:31 INFO     [thread_0]  [grow_action::launch]         Command output will be captured to logfile /home/aislas/mango/log/grow_action.runlog
    2025-12-12 20:14:31 INFO     [thread_0]  [grow_action::launch]         Command output will be printed to this terminal
    2025-12-12 20:14:31 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
    2025-12-12 20:14:31 INFO     [grow_action::launch]    Current directory: /home/aislas/mango
    2025-12-12 20:14:31 INFO     [grow_action::launch]    Loaded Action "grow_action"
    2025-12-12 20:14:31 INFO     [grow_action::launch]    Loaded Host "forest"
    2025-12-12 20:14:31 INFO     [grow_action::launch]    Using Environment "valley"
    2025-12-12 20:14:31 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2025-12-12 20:14:31 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2025-12-12 20:14:31 INFO     [grow_action::run]       Running command:
    2025-12-12 20:14:31 INFO     [grow_action::run]         .sane/mango/scripts/grow.sh 4
    2025-12-12 20:14:31 INFO     [grow_action::run]       Command output will be printed to this terminal
    2025-12-12 20:14:31 STDOUT   [grow_action::run]       Growing with 4 trees with 85% growth rate...
    2025-12-12 20:14:31 STDOUT   [grow_action::run]         Tree 1 grew 7 mangos!
    2025-12-12 20:14:31 STDOUT   [grow_action::run]         Tree 2 grew 4 mangos!
    2025-12-12 20:14:31 STDOUT   [grow_action::run]         Tree 3 grew 6 mangos!
    2025-12-12 20:14:31 STDOUT   [grow_action::run]         Tree 4 grew 3 mangos!
    2025-12-12 20:14:31 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
    2025-12-12 20:14:31 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
    2025-12-12 20:14:31 INFO     [orchestrator]           Running 'harvest_action' on 'forest'
    2025-12-12 20:14:31 INFO     [thread_0]  [harvest_action::launch]      Action logfile captured at /home/aislas/mango/log/harvest_action.log
    2025-12-12 20:14:31 INFO     [thread_0]  [harvest_action::launch]      Saving action information for launch...
    2025-12-12 20:14:31 INFO     [thread_0]  [harvest_action::launch]      Using working directory : '/home/aislas/mango'
    2025-12-12 20:14:31 INFO     [thread_0]  [harvest_action::launch]      Running command:
    2025-12-12 20:14:31 INFO     [thread_0]  [harvest_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_harvest_action.json
    2025-12-12 20:14:31 INFO     [thread_0]  [harvest_action::launch]      Command output will be captured to logfile /home/aislas/mango/log/harvest_action.runlog
    2025-12-12 20:14:31 INFO     [thread_0]  [harvest_action::launch]      Command output will be printed to this terminal
    2025-12-12 20:14:31 INFO     [harvest_action::launch] ***************Inside action_launcher.py***************
    2025-12-12 20:14:31 INFO     [harvest_action::launch] Current directory: /home/aislas/mango
    2025-12-12 20:14:31 INFO     [harvest_action::launch] Loaded Action "harvest_action"
    2025-12-12 20:14:31 INFO     [harvest_action::launch] Loaded Host "forest"
    2025-12-12 20:14:31 INFO     [harvest_action::launch] Using Environment "valley"
    2025-12-12 20:14:31 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
    2025-12-12 20:14:31 INFO     [valley]                   Environment variable GROWTH_RATE=85
    2025-12-12 20:14:31 INFO     [harvest_action::run]    Running command:
    2025-12-12 20:14:31 INFO     [harvest_action::run]      .sane/mango/scripts/harvest.sh
    2025-12-12 20:14:31 INFO     [harvest_action::run]    Command output will be printed to this terminal
    2025-12-12 20:14:31 STDOUT   [harvest_action::run]    Harvesting mangos...
    2025-12-12 20:14:31 STDOUT   [harvest_action::run]    Collected : 20
    2025-12-12 20:14:31 INFO     [harvest_action::launch] ***************Finished action_launcher.py***************
    2025-12-12 20:14:31 INFO     [orchestrator]           [FINISHED] ** Action 'harvest_action'         completed with 'success'
    2025-12-12 20:14:31 INFO     [orchestrator]           Finished running queued actions
    2025-12-12 20:14:31 INFO     [orchestrator]             grow_action   : success  harvest_action: success  
    2025-12-12 20:14:31 INFO     [orchestrator]           All actions finished with success
    2025-12-12 20:14:31 INFO     [orchestrator]           Finished in 0:00:00.360383
    2025-12-12 20:14:31 INFO     [orchestrator]           Logfiles at /home/aislas/mango/log
    2025-12-12 20:14:31 INFO     [orchestrator]           Save file at /home/aislas/mango/tmp/orchestrator.json
    2025-12-12 20:14:31 INFO     [orchestrator]           JUnit file at /home/aislas/mango/log/results.xml
    2025-12-12 20:14:31 INFO     [sane_runner]            Finished


.. tip:: This output can be reproduced by using the source repo example found at
          ``docs/examples/mango/json_harvest_action/.sane/``

Again, reviewing the highlighted regions:

* Our ``"harvest_action"`` is only executed *after* the ``"grow_action"`` has completed
* The ``config["command"]`` is executed (this time with no ``config["arguments"]``)
* The ``STDOUT`` shows that we harvested ``20`` *mangos*. Quite the haul!


.. admonition:: ✨ Congratulations! ✨

    You've gone through the basic JSON interface tutorial and are ready to make
    some workflows!

    If you're looking to add more control to your workflows or for an extra challenge,
    check out the :doc:`advanced`.

.. TODO move this to advanced section
.. Patching
.. --------
.. To get an idea of how we might incorporate patches, let's pretend we want to modify
.. our ``GROWTH_RATE`` in our ``"valley"`` environment temporarily without touching the
.. original host file. Also, we can include a host key that doesn't exist to see what happens:

.. .. literalinclude:: ../../examples/mango/json_grow_action/patch/valley_growth.jsonc
..     :caption: patch/valley_growth.jsonc
..     :language: bash

.. Running with this patch path added we would get:

.. .. code-block:: none
..     :emphasize-lines: 17-20, 55-56, 60

..     sane_runner -p .sane/ --specific_host forest --run -p patch/ -v -n

..     2025-12-05 14:25:25 INFO     [sane_runner]            Logging output to /home/aislas/mango/log/runner.log
..     2025-12-05 14:25:25 INFO     [orchestrator]           Searching for workflow files...
..     2025-12-05 14:25:25 INFO     [orchestrator]             Searching .sane/ for *.json
..     2025-12-05 14:25:25 INFO     [orchestrator]             Searching .sane/ for *.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator]               Found .sane/mango/hosts/forest.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator]               Found .sane/mango/actions/grow.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator]             Searching .sane/ for *.py
..     2025-12-05 14:25:25 INFO     [orchestrator]             Searching patch/ for *.json
..     2025-12-05 14:25:25 INFO     [orchestrator]             Searching patch/ for *.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator]               Found patch/valley_growth.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator]             Searching patch/ for *.py
..     2025-12-05 14:25:25 INFO     [orchestrator]           Loading config file .sane/mango/hosts/forest.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator]           Loading config file .sane/mango/actions/grow.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator]           Loading config file patch/valley_growth.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator::patch]    Processing patches from patch/valley_growth.jsonc
..     2025-12-05 14:25:25 INFO     [orchestrator::patch]      Applying patch to Host 'forest'
..     2025-12-05 14:25:25 INFO     [forest::patch]              Applying patch to Environment 'valley'
..     2025-12-05 14:25:25 WARNING  [orchestrator::patch]      Host 'host-does-not-exist' does not exist, cannot patch
..     2025-12-05 14:25:25 INFO     [sane_runner]            Changing all actions output to verbose
..     2025-12-05 14:25:25 INFO     [orchestrator]           No previous save file to load
..     2025-12-05 14:25:25 INFO     [orchestrator]           Running actions:
..     2025-12-05 14:25:25 INFO     [orchestrator]             grow_action  
..     2025-12-05 14:25:25 INFO     [orchestrator]           and any necessary dependencies
..     2025-12-05 14:25:25 INFO     [orchestrator]           Full action set:
..     2025-12-05 14:25:25 INFO     [orchestrator]             grow_action  
..     2025-12-05 14:25:25 INFO     [orchestrator]           Checking host "forest"
..     2025-12-05 14:25:25 INFO     [orchestrator]           Running as 'forest'
..     2025-12-05 14:25:25 INFO     [orchestrator]           Checking ability to run all actions on 'forest'...
..     2025-12-05 14:25:25 INFO     [orchestrator]             Checking environments...
..     2025-12-05 14:25:25 INFO     [orchestrator]             Checking resource availability...
..     2025-12-05 14:25:25 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
..     2025-12-05 14:25:25 INFO     [orchestrator]           * * * * * * * * * *            All prerun checks for 'forest' passed            * * * * * * * * * * 
..     2025-12-05 14:25:25 INFO     [orchestrator]           * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * 
..     2025-12-05 14:25:25 INFO     [orchestrator]           Saving host information...
..     2025-12-05 14:25:25 INFO     [orchestrator]           Setting state of all inactive actions to pending
..     2025-12-05 14:25:25 INFO     [orchestrator]           No previous save file to load
..     2025-12-05 14:25:25 INFO     [orchestrator]           Using working directory : '/home/aislas/mango'
..     2025-12-05 14:25:25 INFO     [orchestrator]           Running actions...
..     2025-12-05 14:25:25 INFO     [orchestrator]           Running 'grow_action' on 'forest'
..     2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Saving action information for launch...
..     2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Using working directory : '/home/aislas/mango'
..     2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Running command:
..     2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]        /home/aislas/frameflow/sane/action_launcher.py /home/aislas/mango /home/aislas/mango/tmp/action_grow_action.json
..     2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Command output will be printed to this terminal
..     2025-12-05 14:25:25 INFO     [thread_0]  [grow_action::launch]      Command output will be captured to logfile /home/aislas/mango/log/grow_action.log
..     2025-12-05 14:25:26 INFO     [grow_action::launch]    ***************Inside action_launcher.py***************
..     2025-12-05 14:25:26 INFO     [grow_action::launch]    Current directory: /home/aislas/mango
..     2025-12-05 14:25:26 INFO     [grow_action::launch]    Loaded Action "grow_action"
..     2025-12-05 14:25:26 INFO     [grow_action::launch]    Loaded Host "forest"
..     2025-12-05 14:25:26 INFO     [grow_action::launch]    Using Environment "valley"
..     2025-12-05 14:25:26 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '85'
..     2025-12-05 14:25:26 INFO     [valley]                   Environment variable GROWTH_RATE=85
..     2025-12-05 14:25:26 INFO     [valley]                 Running env cmd: 'set' with var: 'GROWTH_RATE' and val: '400'
..     2025-12-05 14:25:26 INFO     [valley]                   Environment variable GROWTH_RATE=400
..     2025-12-05 14:25:26 INFO     [grow_action::run]       Running command:
..     2025-12-05 14:25:26 INFO     [grow_action::run]         .sane/scripts/grow.sh 4
..     2025-12-05 14:25:26 INFO     [grow_action::run]       Command output will be printed to this terminal
..     2025-12-05 14:25:26 STDOUT   [grow_action::run]       Growing with 4 trees with 400% growth rate...
..     2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 1 grew 37 mangos!
..     2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 2 grew 1 mangos!
..     2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 3 grew 9 mangos!
..     2025-12-05 14:25:26 STDOUT   [grow_action::run]         Tree 4 grew 37 mangos!
..     2025-12-05 14:25:26 INFO     [grow_action::launch]    ***************Finished action_launcher.py***************
..     2025-12-05 14:25:26 INFO     [orchestrator]           [FINISHED] ** Action 'grow_action'            completed with 'success'
..     2025-12-05 14:25:26 INFO     [orchestrator]           Finished running queued actions
..     2025-12-05 14:25:26 INFO     [orchestrator]             grow_action: success  
..     2025-12-05 14:25:26 INFO     [orchestrator]           All actions finished with success
..     2025-12-05 14:25:26 INFO     [orchestrator]           Finished in 0:00:00.194862
..     2025-12-05 14:25:26 INFO     [orchestrator]           Save file at /home/aislas/mango/tmp/orchestrator.json
..     2025-12-05 14:25:26 INFO     [orchestrator]           JUnit file at /home/aislas/mango/log/results.xml
..     2025-12-05 14:25:26 INFO     [sane_runner]            Finished

.. .. tip:: This output can be reproduced by using the source repo example found at
..           ``docs/examples/mango/json_grow_action/.sane/``

.. .. hint:: The ``-v``/``--verbose`` flag copies the :py:meth:`Action.run()` output to
..           the main output. The ``-n``/``--new`` flag forces a new workflow run evaluation.
..           See :doc:`../user_guide/running` for more info.

.. Looking at the three highlighted regions, we can see some new effects:

.. * A new ``[<context>::patch]`` section appears in loading & processing

..   * Our patch is applied under ``"forest"`` :py:class:`Host` to the ``"valley"`` :py:class:`Environment`
..   * The nonexistent host patch produces a ``WARNING``
.. * The ``"env_vars"`` patch is applied *after* the previous setting, it does not replace it (see :py:meth:`Environment.setup_env_vars` for more info)
.. * We grew our mangos with ``400%``!

.. toctree::
   :maxdepth: 2
