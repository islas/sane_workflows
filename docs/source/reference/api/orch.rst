Orchestrator
============

.. py:module:: sane.orchestrator

  .. autodecorator:: sane.register

  .. autoclass:: sane.Orchestrator
      :show-inheritance:
      :special-members:

      .. _orch.ui:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. automethod:: add_action
      .. automethod:: add_host

      User Attributes & Properties
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      .. py:attribute:: actions
          :type: utdict.UniqueTypedDict[Action]

          The unique set of actions in this workflow.

          The actions are stored in a unique-key type-enforced dictionary. Only
          :py:class:`Action` instance objects may be stored (derived types valid)

      .. py:attribute:: hosts
          :type: utdict.UniqueTypedDict[Host]

          The unique set of hosts in this workflow.

          The hosts are stored in a unique-key type-enforced dictionary. Only
          :py:class:`Host` instance objects may be stored (derived types valid)

      .. autoproperty:: save_location
      .. autoproperty:: log_location
      .. autoproperty:: working_directory

      Internal API
      ------------
      While not to be invoked by the user, these functions may be useful reference.

      .. automethod:: __init__

      .. autoproperty:: current_host
      .. autoproperty:: save_file
      .. autoproperty:: results_file

      .. automethod:: run_actions
      .. automethod:: add_search_paths
      .. automethod:: add_search_patterns
      .. automethod:: load_paths
      .. automethod:: load_py_files
      .. automethod:: load_config_files
      .. automethod:: load_options
      .. automethod:: load_core_options
      .. automethod:: search_type

      .. automethod:: process_registered
      .. automethod:: process_patches
      .. automethod:: find_host
      .. automethod:: construct_dag
      .. automethod:: traversal_list

      .. py:attribute:: __wake__

          :py:class:`threading.Event`

          A synchronization primitive for coordinating workflow execution. All
          queued :py:class:`Actions <Action>` and the current :py:class:`Host`
          are provided a reference to this object before a workflow begins.

          During workflow execution (:py:meth:`run_actions()`), the :py:class:`Orchestrator`
          starts all :py:class:`Actions <Action>` able to run then calls :py:meth:`threading.Event.wait()`
          Further workflow execution evaluation will not continue until an object
          not in the main thread triggers this primitive.


.. toctree::
   :maxdepth: 6
