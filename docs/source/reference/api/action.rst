Action
======

.. py:module:: sane.action

  .. autoclass:: sane.DependencyType
      :members:
      :exclude-members: __new__
      :member-order: bysource

  .. autoclass:: sane.ActionState
      :members:
      :exclude-members: __new__
      :member-order: bysource

  .. autoclass:: sane.ActionStatus
      :members:
      :exclude-members: __new__
      :member-order: bysource


  .. autoclass:: sane.Action
      :show-inheritance:
      :special-members:

      .. _action.ui:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. automethod:: __init__
      .. automethod:: add_dependencies
      .. automethod:: add_resource_requirements
      .. automethod:: load_options

      User Attributes & Properties
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

      .. py:attribute:: config
          :type: dict

          A user-defined ``dict`` that can hold anything `picklable`_

          Automatic config :py:meth:`loading <load_core_options>` and 
          :py:meth:`dereferencing <dereference>` is supported for this attribute.
          This is meant as a general information container without the
          need for defining a custom :py:class:`Action` with custom attributes.

          Reserved keywords in this dict are:

          ===============  =================================================
          keyword          usage
          ===============  =================================================
          ``"command"``    command to execute when :py:class:`Action` is run
          ``"arguments"``  arguments to use in command execution
          ===============  =================================================

          If a custom :py:class:`Action` overrides :py:meth:`run()`, then there are no reserved keywords
          as the above keywords are specific to the default base class :py:meth:`run()` implementation.

      .. py:attribute:: outputs
          :type: dict

          A user-provided ``dict`` of `picklable`_ output values that should be valid upon :py:class:`Action` completion

          These outputs will be provided to direct dependencies of this :py:class:`Action` within their
          :py:attr:`dependencies` property during execution. Any further use of this attribute is
          left to user implementation.


      .. py:attribute:: environment
          :type: str

          The :py:attr:`Environment.name` of the :py:class:`Environment` to use
          that the :py:attr:`current host <sane.Orchestrator.current_host>` should provide.

      .. autoproperty:: host_info
      .. autoproperty:: info
      .. autoproperty:: id
      .. autoproperty:: dependencies
      .. automethod:: resources

      .. autoattribute:: local

      Customizable Functions
      ----------------------
      :py:class:`Action` and :py:class:`Host` classes are designed to be modified by users.
      
      While any function could generally be overwritten with some care,
      certain functions within each class are designed specifically for user
      modification without the need to worry about internal logic.
      
      Defining these functions does not require calling :py:class:`super` or other intrinsic
      Python knowledge beyond the interface of the function and any user logic.

      .. automethod:: extra_requirements_met
      .. automethod:: load_extra_options

      .. automethod:: pre_launch
      .. automethod:: pre_run
      .. automethod:: run
      .. automethod:: post_run
      .. automethod:: post_launch


      Helper Functions
      ----------------
      .. automethod:: resolve_path
      .. automethod:: resolve_path_exists
      .. automethod:: file_exists_in_path
      .. automethod:: dereference_str
      .. automethod:: dereference
      .. automethod:: execute_subprocess
      .. automethod:: push_exec_raw
      .. automethod:: pop_exec_raw

      .. _action.internal:

      Internal API
      ------------
      The following documentation is provided for advanced use beyond the creation of
      :ref:`custom Actions <advanced.custom_actions>`.

      .. autoattribute:: __timestamp__
      .. autoattribute:: __time__
      .. autoattribute:: dry_run

      .. autoproperty:: logfile
      .. autoproperty:: runlog
      .. autoproperty:: origins
      .. autoproperty:: status
      .. autoproperty:: state
      .. autoproperty:: results

      .. automethod:: load_core_options
      .. automethod:: launch

      .. automethod:: save_outputs
      .. automethod:: load_outputs

      .. automethod:: set_status_success
      .. automethod:: set_status_failure
      .. automethod:: set_state_pending
      .. automethod:: set_state_skipped
      .. automethod:: set_state_error

      .. autoattribute:: __orch_wake__
      .. autoattribute:: _run_lock






.. toctree::
   :maxdepth: 6
