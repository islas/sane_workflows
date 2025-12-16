Any :py:class:`Action` that makes use of quantifiable resources tracked by
:py:attr:`Host.resources` should ideally note them by calling this function.

These resource requests are how the :py:class:`Orchestrator` coordinates tasking
with a given :py:class:`Host`. This is to ensure the resources that the host *does*
provide are not oversubscribed (keeping usage at or below limit), and that any
:py:class:`Action` that requires resources that are not provided are caught.

.. danger:: If an :py:class:`Action` does not request resources, **regardless**
            of the internal logic and **actual** resources usage, it will **ALWAYS**
            be run. If you use untracked or more resources than requested, you may
            inadvertently use more resources than the :py:class:`Host` provides.

            It is generally a good idea to track critical resources needed in both
            the :py:class:`Action` and :py:class:`Host`

