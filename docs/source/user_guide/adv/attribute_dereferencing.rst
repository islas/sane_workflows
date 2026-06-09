
.. _advanced.dereferencing:

Attribute Dereferencing
=======================
.. py:module:: sane
    :no-index:

Summary
-------

SANE supports GitHub-Actions-style attribute dereferencing of strings within any
instance of :py:class:`Action` (including derived), usable within the JSON and
Python interface.

Attribute dereferencing lets you reference values defined within an :py:class:`Action`
object dynamically at runtime. While the actual dereference operation (:py:meth:`Action.dereference_str`)
only acts on :py:class:`str`, the main function :py:meth:`Action.dereference`
can fully operate on strings, lists, and nested dictionaries.

Dereferencing uses the syntax:

.. code-block:: python

  "${{ <attribute> }}""


A more detailed explanation can be viewed from this :ref:`api_ref` excerpt:

.. collapse:: Quick Reference (click to open/close):

    .. automethod:: Action.dereference_str
      :no-index:

    .. automethod:: Action.dereference
      :no-index:

|


The :py:attr:`Action.config` is resolved at an action's default :py:meth:`~Action.run()`:sup:`1`,
so the values must be present and valid at dereference time.

.. important:: :sup:`1` Not all :py:class:`Action` attributes are dereferenced by
               default. The base class will always have fully dereferenced :py:attr:`~Action.config`
               and the :py:attr:`~Action.info` of :py:attr:`~Action.dependencies` (that
               parent ``Action's`` :py:attr:`~Action.outputs` and :py:attr:`~Action.config`
               by default) at the start of :py:meth:`~Action.run()`.

               Dependency :py:attr:`~Action.info` is always dereferenced.

               Users are free to call :py:meth:`~Action.dereference` at any time
               within any method of a derived :py:class:`Action` class. If users
               override the :py:meth:`Action.info` or :py:meth:`Action.run` method
               they should take care to :py:meth:`~Action.dereference` any attributes
               needed.


Basic JSON Example
------------------
The JSON interface commonly uses attribute dereferencing inside the
``"config"`` dictionary for an :py:class:`Action`. For example:

.. code-block:: json

  {
    "actions" :
    {
      "hello" :
      {
        "config" :
        {
          "command" : "echo",
          "arguments" : [ "Running action ${{ id }}" ]
        }
      }
    }
  }


When :py:class:`Action` ``"hello"`` is run the string ``${{ id }}`` will be replaced
with the :py:attr:`Action.id` (``hello`` in this example).

Basic Python Example
--------------------
You can also use dereferencing from within the Python interface when you
setup ``config`` dictionaries within :py:class:`sane.Action` objects. For example:

.. code-block:: python

    import sane

    @sane.register
    def create_actions( orch ):
      a = sane.Action( "a" )
      b = sane.Action( "b" )

      b.add_dependencies( a.id )
      # Setup so Action 'b' can reference values from itself and dependencies
      a.config["greeting"] = "Hello from ${{ id }}"
      b.config["message"] = "Depends on '${{ dependencies.a.config.greeting }}'"
      orch.add_action( a )
      orch.add_action( b )

      a.config["command"] = "echo"
      a.config["arguments"] = [ "${{ config.greeting }}" ]

      b.config["command"] = "echo"
      b.config["arguments"] = [ "${{ config.message }}" ]

When :py:class:`Action` ``"b"`` is run it will recursively replace the reference
strings in ``"arguments"`` until the final output is ``"Depends on 'Hello from a'"``.

.. hint:: Note that the dependency :py:attr:`~Action.info` passed to ``"b"`` from ``"a"``
          is :py:meth:`dereferenced <Action.dereference>` beforehand *within the context of* ``"a"``

Callables
---------

If an attribute resolves to a `callable`_, it will be called **WITH NO ARGUMENTS**
first before continuing dereferencing. An *extra* special case of this is the
:py:meth:`sane.Action.resources` method, where it will be invoked with the 
current host name (via :py:attr:`Action.host_info`) if available to ensure the
resource :py:class:`dict` returned matches the context of the current :py:class:`Host`.

How SANE Implements Dereferencing
---------------------------------
.. role:: green
  :class: green-text

The bulk of implementation is within the :py:meth:`Action.dereference_str` method.
Feel free to click on the :green:`[source]` hyperlink to follow along with the code
walkthrough.

The method operates by building up a history of the string to dereference. On each
pass:

#. Check if the output string is not in the history
#. The previous output string is appended to the history
#. Matches are generated using the internal regular expression for dereference syntax
#. For every match this iteration

   * Step through attributes in reference string until complete
   * Take final value and perform in-place substitution on output string

#. Continue until output string is present in history, meaning there are no more substitutions

This method of dereferencing allows us to break down complex references or even
detect cycles to prevent accidental infinite loops:

.. code-block::

    Dereferenced [0] '${{ config.two[ ${{ config.arr[ ${{ config.three.${{ config.foobar }} }} ] }} ] }}'
                 [1] '${{ config.two[ ${{ config.arr[ ${{ config.three.foo }} ] }} ] }}'
                 [2] '${{ config.two[ ${{ config.arr[ 3 ] }} ] }}'
                 [3] '${{ config.two[ 0 ] }}'
         into => [4] '2'

Direct API Usage in Python
--------------------------

When you implement custom actions or need explicit control of dereferencing,
call the :py:class:`Action` helpers directly. Remember that dereferencing operates
at the scope of the current :py:class:`Action` *and* will throw an error on bad
values unless the ``noexcept=True`` argument is provided.

.. code-block:: python

    import sane

    class MyAction( sane.Action ):
      def load_data( self, file ):
        ...do work...

      def run( self ):
        # Our action will need a file from some previous action run
        datafile = self.dereference( "${{ dependencies.${{ config.data_from }}.output.data }}" )
        self.load_data( datafile )

This is a very simplified example where you could easily replace the ``datafile``
variable creation with ``datafile = self.dependencies[config["data_from"]]["output"]["data"]``.
However, it allows us to define this operation in a manner that goes beyond single
resolution. Consider:

.. code-block:: python

    import sane

    class MyAction( sane.Action ):
      def __init__( self, id ):
        # Data normally comes from this location
        self.datafile = "${{ dependencies.${{ config.data_from }}.output.data }}"

      def load_extra_options( self, options, origin ):
        # Allow instances of this action type to change where the data comes from
        self.datafile = options.pop( "datafile", self.datafile )
        super().load_extra_options( self, options, origin )

      def load_data( self, file ):
        ...do work...

      def run( self ):
        # Our action will need a file from some previous action run
        datafile = self.dereference( "${{ datafile }}" )
        self.load_data( datafile )

We've now set the datafile to something that cannot be used upon creation as it
depends on runtime information. Likewise, we've given any user of this custom :py:class:`Action`
the option to change the file that gets loaded. At ``run()`` the logic for default
setup stays exactly the same, but it is now more flexible to configurability. Replicating
this with logic contained to just ``run()`` may look something like:

.. code-block:: python

    import sane

    class MyAction( sane.Action ):
      def __init__( self, id ):
        # Data normally comes from this location
        self.datafile = None

      def load_extra_options( self, options, origin ):
        # Allow instances of this action type to change where the data comes from
        self.datafile = options.pop( "datafile", self.datafile )
        super().load_extra_options( self, options, origin )

      def load_data( self, file ):
        ...do work...

      def run( self ):
        if datafile is None:
          datafile = self.dependencies[config["data_from"]]["output"]["data"]
        # Our action will need a file from some previous action run
        self.load_data( datafile )

While subtle, notice that this "equivalent logic" still loses some configurability:
if we override the ``datafile`` value at option load we cannot access any non-default
runtime information. For example, we would not be able to set it to use output data
from a build dependency instead (e.g. ``${{ dependencies.build.output.data }}``).

Fundamentally, while much of the logic for dereferencing could in theory be replaced
with conditional or use-specific code the main use is allowing flexible runtime
variable referencing for simpler configuration logic.

Runtime Notes and Safety
------------------------
Dereferencing is a substitution-only mechanism and does not evaluate arbitrary code.
It only accesses attributes and items available within the referenced objects, starting
at the :py:class:`Action` that called it.

Because resolution happens only at function execution, the referenced attributes
must be present at least by then otherwise an exception is raised unless ``noexcept=True``
is passed to the API. Keep this in mind when making use of deferred evaluation.

Indexing into non-list or out-of-range indices raises an exception.

More Examples
-------------
The test suite contains focused examples of dereferencing behavior. See
``tests/test_action.py`` (the ``test_action_dereference*`` tests) for concrete
cases demonstrating nested, indexed, and multi-stage dereferencing.

Summary
-------
Attribute dereferencing is a compact, expressive mechanism to inject dynamic
workflow values into configuration. In the default :py:meth:`Action.run` the
:py:attr:`~Action.config` attribute is dereferenced, but users are free to use
this capability in any custom :py:class:`Action` classes they write!

.. toctree::
   :maxdepth: 6