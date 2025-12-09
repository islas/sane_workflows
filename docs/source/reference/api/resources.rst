Resources
=========

.. py:module:: sane.resources

  .. autoclass:: sane.resources.Resource
      :members:
      :exclude-members: __new__
      :member-order: bysource

  .. autoclass:: sane.resources.AcquirableResource
      :members:
      :exclude-members: __new__
      :member-order: bysource

  .. autoclass:: sane.resources.ResourceRequestor
      :show-inheritance:
      :special-members:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. automethod:: add_resource_requirements

      User Attributes & Properties
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

      .. automethod:: resources
      .. autoattribute:: local

      Internal API
      ------------
      .. automethod:: load_core_config


  .. autoclass:: sane.resources.ResourceProvider
      :show-inheritance:
      :special-members:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. automethod:: add_resources

      User Attributes & Properties
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      .. autoproperty:: resources

      Internal API
      ------------
      .. automethod:: load_core_config
      .. automethod:: resources_available
      .. automethod:: acquire_resources
      .. automethod:: release_resources


  .. autoclass:: sane.resources.NonLocalProvider
    :show-inheritance:
    :special-members:

    User Interface
    --------------

    User Attributes & Properties
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    .. autoattribute:: local_resources
    .. autoattribute:: default_local
    .. autoattribute:: force_local

    Internal API
    ------------
    .. automethod:: load_core_config

    Customizable Functions
    ----------------------
    The :py:class:`NonLocalProvider` class is by design an abstract base class
    to force a specialized implementation to be defined. This class has no inherent
    knowledge abount how nonlocal resources would be requested or managed.

    .. automethod:: nonlocal_resources_available
    .. automethod:: nonlocal_acquire_resources
    .. automethod:: nonlocal_release_resources

  .. autoclass:: sane.resources.ResourceMapper
      :exclude-members: __new__
      :special-members:
      
      .. automethod:: add_mapping

.. toctree::
   :maxdepth: 6
