.. _advanced.custom_classes:

Custom Classes
==============
.. py:module:: sane
    :no-index:

Writing custom classes using SANE workflows will mostly depend on which type of
workflow object you wish to customize. However, each class is always based off
of the :py:class:`sane.options.OptionLoader` base class. If you plan on modifying
the class to expose configurable options with the idea of allowing both Python
and JSON interfacing then you should update the :py:meth:`~sane.options.OptionLoader.load_extra_options`
function for that class.

As the principle is the same for any derivable workflow option, the main concepts
are presented here before the specifics of any individual class.

Custom Option Loading
---------------------
The key idea behind :py:class:`sane.options.OptionLoader` is that it provides a
consistent and auditable contract for loading configuration dictionaries into
an object. This is the same pattern used by :py:class:`sane.Action`,
:py:class:`sane.Host`, :py:class:`sane.Environment`, and other workflow objects.

The primary benefits to using the provided functions:

* It standardizes option loading across workflow objects.
* It encourages safe handling of configuration dictionaries by consuming
  supported keys and warning about unused keys.
* It preserves the ability to trace where options were loaded from with
  :py:attr:`~sane.options.OptionLoader.origins`.


Primary User Interface Function
-------------------------------

A custom :py:class:`sane.options.OptionLoader` class (beyond the workflow objects
in SANE) is expected to implement or extend :py:meth:`~sane.options.OptionLoader.load_extra_options`

.. collapse:: Quick Reference (click to open/close)

  .. automethod:: sane.options.OptionLoader.load_extra_options
      :no-index:

|

This function is always called after :py:meth:`~sane.options.OptionLoader.load_core_options`
during the processing of :py:meth:`~sane.options.OptionLoader.load_options()`:


.. collapse:: Quick Reference (click to open/close)

  .. automethod:: sane.options.OptionLoader.load_options
      :no-index:

|


.. warning:: When using **ANY** ``load_*_options()`` method, the most important rule that
             any key that your implementation handles should be removed from the ``options`` dict.

             This is because at the end of the call, any remaining keys will be recognized
             as unused and will be logged.


Python Example
--------------

The following simple example defines a custom :py:class:`Action` object, and demonstrates
some common use patterns for option loading. Use in Python is purely for convenience
if configuring from a :external:py:class:`dict` works best for your workflow.

.. code-block:: python

    import sane

    class MyAction( sane.Action ):
      def __init__( self, id ):
        super().__init__( id )
        self.max_items = 20
        self.prefix    = "memo"

      def load_extra_options( self, options, origin ):
        # Pop from the dictionary using a default value if not found allows this
        # key to remain optional
        self.max_items = options.pop( "max_items", self.max_items )
        self.prefix    = options.pop( "prefix", self.prefix )
        # Continue to load any extra options - good practice for inheritance
        super().load_extra_options(options, origin)

    @sane.register
    def workflow( orch ):
      action = MyAction( "foo" )
      action.load_options( { "max_items" : 10 } )
      orch.add_action( action )


.. note::
    When the workflow is loaded, ``action.load_options(...)`` is the only call
    to be called as it will under the hood call the derived methods.

JSON Interfacing
----------------
When a JSON file declares an object with a ``"type"`` field, the
:py:class:`sane.Orchestrator` will resolve that type using
:py:meth:`sane.options.OptionLoader.search_type`.

.. collapse:: Quick Reference (click to open/close)

  .. automethod:: sane.options.OptionLoader.search_type
      :no-index:

|

This means that your custom Python module must be available to the workflow
before the JSON file is interpreted. When using the ``sane_runner`` entry point,
this is done for you by default - loading your Python files first before any
JSON files. The exact order of operations is outlined in :py:meth:`Orchestrator.load_paths`:

.. collapse:: Quick Reference (click to open/close)

  .. automethod:: Orchestrator.load_paths
      :no-index:

|


The JSON type can be the Python fully `qualified name`_ or a shortened type name
that uniquely identifies the type from the loaded Python modules.

.. code-block:: json

    {
      "actions":
      {
        "bar":
        {
          "type": "where_MyAction_is.MyAction",
          "max_items": 50,
        }
      }
    }

.. hint::
    Recall from the Tutorial :ref:`tutorial.structure` that the path we provide
    to the runner functions as the root `namespace package`_ so our type will be
    named based off of that. If ``MyAction`` is found in ``.sane/proj/custom_actions/acts.py``
    and run with ``sane_runner -p .sane/ ...`` then ``"type" : "proj.custom_actions.acts.MyAction"``
    is the full type name.


Summary
-------
Setting up the :py:meth:`~sane.options.OptionLoader.load_extra_options` is a good
idea for custom workflow classes that plan to use :py:meth:`~sane.options.load_options()`
either directly from Python or via JSON configs. When adding your own options keep in mind
to:

* **Only** override :py:meth:`load_extra_options` (core options are reserved for internal classes)
* **Always** remove each processed key from the ``options`` dictionary
* **Always** call ``super.load_extra_options()`` at some point in your derived method to ensure proper inheritance setup

Specific Classes
================
.. toctree::
    :maxdepth: 2

    custom_actions.rst
    custom_hosts.rst

