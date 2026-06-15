Logger
======

.. py:module:: sane.logger

    .. rubric:: Reserved Log Levels
        :heading-level: 1

    These reserved log levels help filter and control which log messages get output
    to the console/main log and which go to only the :py:attr:`Action.logfile`. By
    using the :ref:`running.debug` settings when running a workflow, you can lower
    the required log level to appear in the main log.


  .. autodata:: sane.logger.STDOUT

  .. autodata:: sane.logger.ACT_INFO

  .. autodata:: sane.logger.MAIN_LOG

  .. autoclass:: sane.logger.Logger
      :special-members:

      .. _logger.ui:

      User Interface
      --------------

      User Methods
      ^^^^^^^^^^^^
      .. .. automethod:: __init__
      .. automethod:: log
      .. automethod:: log_push
      .. automethod:: log_pop
      .. automethod:: push_logscope
      .. automethod:: pop_logscope

      Internal API
      ------------
      The following documentation is provided for advanced use in the creation of
      :ref:`custom classes <advanced.custom_actions>`.

      .. autoattribute:: default_log_level
      .. autoattribute:: label_length
      .. autoproperty:: logname
      .. autoproperty:: current_logname
      .. autoattribute:: logger
      .. automethod:: log_flush


.. toctree::
   :maxdepth: 6
