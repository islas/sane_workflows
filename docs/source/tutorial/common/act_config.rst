Arguably the most versatile field in the default :py:class:`Action`, this generic
``dict`` is meant to hold anything `picklable`_ that your action may need in running.
Later (during :ref:`advanced.dereferencing`) we will learn to more effectively use
this general data container.

For now, the main use is in the ``config["command"]`` and ``config["arguments"]``
keys which are used by the default :py:meth:`Action.run`. As their names imply,
during :py:class:`Action` execution, the ``config["command"]`` and ``config["arguments"]``
will be used as the command and arguments to execute for that action, respectively.

We are going to use the helper script located at ``.sane/mango/scripts.grow.sh`` to
perform our main logic. This thereby allows us to have an :py:class:`Action` with
customizable execution without needing to write :ref:`advanced.custom_actions`. The
path we use to the script should be a relative path from the working directory, in
this case ``./``. Only use absolute paths for scripts that will always be in the
same place (e.g. host scripts)!