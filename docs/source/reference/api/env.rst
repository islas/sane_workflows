Environment
===========

.. py:module:: sane.environment

  .. autoclass:: sane.Environment
      :show-inheritance:
      :special-members:

      .. _env.ui:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. automethod:: __init__
      .. automethod:: setup_env_vars
      .. automethod:: setup_lmod_cmds
      .. automethod:: setup_scripts

      User Attributes & Properties
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      .. autoproperty:: name
      .. autoproperty:: aliases
      .. autoattribute:: lmod_path

      Customizable Functions
      ----------------------
      The :py:class:`Environment` is also designed to be modified by users.
      
      While any function could generally be overwritten with some care,
      certain functions within each class are designed specifically for user
      modification without the need to worry about internal logic.
      
      Defining these functions does not require calling :py:class:`super` or other intrinsic
      Python knowledge beyond the interface of the function and any user logic.

      .. automethod:: load_extra_options

      .. automethod:: pre_setup
      .. automethod:: post_setup

      Internal API
      ------------
      The following documentation is provided for advanced use in the creation of
      a custom :py:class:`Environment`.

      .. automethod:: setup

      .. automethod:: load_options
      .. automethod:: load_core_options

      .. automethod:: env_var_prepend
      .. automethod:: env_var_append
      .. automethod:: env_var_set
      .. automethod:: env_var_unset

      .. automethod:: module
      .. automethod:: env_script

.. toctree::
   :maxdepth: 6
