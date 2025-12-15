Each :py:class:`Action` must run within an :py:class:`Environment`, however the
actual object instance is owned by the :py:class:`Host`, as each host is left to
implement that specific environment.

The communication from :py:class:`Action` to :py:class:`Host` about which
environment to use is facilitated by a ``str`` match between :py:attr:`Action.environment`
and :py:attr:`Environment.name` (or :py:attr:`Environment.aliases`) within the
:py:attr:`Host.environments`.
