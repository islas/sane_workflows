A quick walkthrough of the above output, focusing on the highlighted regions:

1. The :py:class:`Orchestrator` finds and loads our files
2. The :py:class:`Orchestrator`, after verifying the selected :py:class:`Host`, runs our :py:class:`Action` on the host
3. During execution inside our :py:class:`Action` (``action_launcher.py``):
    a. The :py:class:`Action` loading itself and the :py:class:`Host`
    b. Sets up the :py:class:`Environment`
    c. Calls our ``config["command"]`` with ``config["arguments"]``
    d. Outputs the command output with log tag ``STDOUT`` (stderr also goes here)
4. Final logs and results information is left at the bottom for our convenience

Special notes:

* Everything betwwen ``***...Inside action_launcher.py...***`` and ``***...Finished action_launcher.py...***`` for
  a respective :py:class:`Action` is actually the direct output of the :py:meth:`Action.run`
* (3.a) occurs because the ``action_launcher.py`` (:py:meth:`Action.run`) occurs in a totally separate
  subprocess
* (3.d) captures all command output (stdout and stderr)