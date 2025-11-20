Orchestrator
============

.. py:module:: sane.orchestrator

  .. autodecorator:: sane.register

  .. autoclass:: sane.Orchestrator
      :show-inheritance:
      :special-members:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. automethod:: __init__
      .. automethod:: add_action
      .. automethod:: add_host

      User Properties
      ^^^^^^^^^^^^^^^
      .. autoproperty:: save_location
      .. autoproperty:: log_location
      .. autoproperty:: save_file
      .. autoproperty:: results_file
      .. autoproperty:: current_host
      .. autoproperty:: working_directory

      User Attributes
      ^^^^^^^^^^^^^^^
      .. py:attribute:: actions
          :type: utdict.UniqueTypedDict[Action]

          The unique set of actions in this workflow.

          The actions are stored in a unique-key type-enforced dictionary. Only
          :py:class:`Action` instance objects may be stored (derived types valid)

      .. py:attribute:: hosts
          :type: utdict.UniqueTypedDict[Action]

          The unique set of hosts in this workflow.

          The hosts are stored in a unique-key type-enforced dictionary. Only
          :py:class:`Host` instance objects may be stored (derived types valid)

      Internal API
      ------------
      While not to be invoked by the user, these functions may be useful reference.

      .. automethod:: run_actions
      .. automethod:: load_paths
      .. automethod:: load_py_files
      .. automethod:: load_config_files
      .. automethod:: load_config
      .. automethod:: load_core_config
      .. automethod:: process_registered
      .. automethod:: process_patches
      .. automethod:: find_host
      .. automethod:: construct_dag
      .. automethod:: traversal_list


.. toctree::
   :maxdepth: 6
