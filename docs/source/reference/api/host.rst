Host
====

.. py:module:: sane.host

  .. autoclass:: sane.Host
      :show-inheritance:
      :special-members:

      .. _host.ui:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. automethod:: __init__
      .. automethod:: add_environment
      .. automethod:: add_resources

      User Attributes & Properties
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      .. autoproperty:: name
      .. autoproperty:: aliases

      .. py:attribute:: environments
          :type: utdict.UniqueTypedDict[Environment]

          The unique set of environments within this host.

          The environments are stored in a unique-key type-enforced dictionary. Only
          :py:class:`Environment` instance objects may be stored (derived types valid)

      .. py:attribute:: config
          :type: dict

          A user-defined ``dict`` that can hold anything `picklable`_

          This is meant as a general information container without the
          need for defining a custom :py:class:`Host` with custom attributes.

      .. autoproperty:: default_env
      .. autoproperty:: base_env
      .. autoproperty:: resources

      Customizable Functions
      ----------------------
      :py:class:`Action` and :py:class:`Host` classes are designed to be modified by users.
      
      While any function could generally be overwritten with some care,
      certain functions within each class are designed specifically for user
      modification without the need to worry about internal logic.
      
      Defining these functions does not require calling :py:class:`super` or other intrinsic
      Python knowledge beyond the interface of the function and any user logic.

      .. automethod:: load_extra_config

      .. automethod:: pre_run_actions
      .. automethod:: pre_launch
      .. automethod:: launch_wrapper
      .. automethod:: post_launch
      .. automethod:: post_run_actions

      .. autoproperty:: watchdog_func

      Internal API
      ------------
      The following documentation is provided for advanced use in the creation of
      :ref:`custom Hosts <adv_use_hosts>`.

      .. autoproperty:: info

      .. automethod:: load_config
      .. automethod:: load_core_config
      .. automethod:: search_type

      .. automethod:: resources_available
      .. automethod:: acquire_resources
      .. automethod:: release_resources

      .. automethod:: __orch_wake__
      .. autoattribute:: kill_watchdog

.. toctree::
   :maxdepth: 6
