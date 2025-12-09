********
Tutorial
********
.. py:module:: sane
    :no-index:

In this tutorial we will work through creating a workflow for a
project called ``mango``. The files will be added gradually as we
build up our understanding of SANE workflows.


Structure
=========
To begin, we will discuss how we will layout our plan for file structure.
This is not strictly necessary, but a best practice design.

When writing a workflow, it will be a good idea to place it in a
separate location from the project source code, unless the project
itself is just workflow files.

For the purposes of this tutorial, we will be placing files under ``.sane``.

Alternate :py:class:`Host` definitions or specialized patches
(see :py:meth:`~Orchestrator.process_patches`) that are specific
to a user or particular machine not directly supported by your project
can be placed completely outside your project or repository and
pulled into the workflow at runtime using the :ref:`--path <running.paths>`
flag.

Finally, especially when using the python interface, it may be
beneficial to place files under another folder inside the workflow
root folder. This acts as the root `namespace package`_ for python imports.

Let's work through an example layout for our ``mango`` workflow
before we start looking at adding files and content said files.

Take this directory structure:

.. code-block:: none

    .sane/
    ├── common.jsonc
    ├── mango
    │   ├── actions
    │   │   ├── grow.jsonc
    │   │   └── harvest.py
    │   ├── custom
    │   │   ├── actions.py
    │   │   ├── envs.py
    │   │   └── hosts.py
    │   │   └── funcs.py
    │   └── hosts
    │       ├── desert.py
    │       └── forest.jsonc
    └── scripts
        └── grow.sh
        └── harvest.sh

In the above directory structure, our python and JSON files will
not be specifically isolated. The :py:class:`Orchestrator` will find
them for us.

Instead, we will made sure to place all custom python modules that
we want to ``import`` later within our workflow under at least
one extra folder; in this case under ``.sane/mango/custom``.

From there, any extra folders or organization is left for us to
decide. For this example, we will organized actions and hosts into
separate folders as well.

We also will have helper scripts under ``.sane/scripts/`` that the will
not be read in with the rest of the workflow files as its extension
is neither ``.py`` nor ``.json[c]``.

Go to the next section to begin the tutorial and adding these files.

.. toctree::
    :maxdepth: 2
    :caption: Tutorial Contents

    python.rst
    json.rst
    advanced.rst
