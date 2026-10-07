***
CLI
***

``sane`` runs workflows and inspects saved results::

   sane workflow [options]
   sane view <command> [workflow_save] [options]

Use ``--help`` at any level to see the available commands or their options::

   sane --help
   sane workflow --help
   sane view --help
   sane view logs --help

Running Workflows
=================

Use ``workflow`` to invoke the runner::

   sane workflow -p ./workflow -a simulate --run

See :doc:`/user_guide/running` for action selection, execution, graph output,
logging, and virtual relaunches. See :ref:`running.paths` for
workflow discovery and :ref:`running.saves` for saved-state behavior.

Additional options:

``-s PATTERN``, ``--search_pattern PATTERN``
   Select files to load. Repeat for multiple patterns. Defaults to ``*.json``,
   ``*.jsonc``, and ``*.py``. Quote patterns to prevent shell expansion.

``-w PATH``, ``--working_dir PATH``
   Set the working directory for actions. Defaults to ``./``; an action-specific
   working directory takes precedence.

``-ll PATH``, ``--log_location PATH``
   Set the log directory. Defaults to ``./log``.

``-m MODE``, ``--mode MODE``
   Control reuse of saved state: ``0`` uses workflow state (the default),
   ``1`` always runs requested actions, and ``2`` also invalidates downstream
   actions. For example, rerun a selected action with ``--run --mode 1``.

Inspecting Results
==================

``view`` reads ``orchestrator.json`` from ``./tmp`` by default. Supply a directory
as the optional ``workflow_save`` argument to inspect another run, or use
``--filename NAME`` to read a different saved-state filename::

   sane view summary ./results/trial

.. list-table:: View commands
   :header-rows: 1
   :widths: 20 80

   * - Command
     - Result
   * - ``status``
     - Report each action's execution status. Use ``-l N`` to set the maximum line length.
   * - ``state``
     - Report each action's saved state. Use ``-l N`` to set the maximum line length.
   * - ``logs``
     - List action log paths. Use ``--errors`` to include only failed actions.
   * - ``summary``
     - Report success or failure, action and error counts, and runtimes.
       Exits with a nonzero status when any saved action has failed.
   * - ``usage``
     - Plot recorded resource usage. Prompts for a run index; pressing Enter selects index 0.
       Requires Matplotlib.

After a run, check its summary and locate logs for failed actions::

   sane view summary
   sane view logs --errors --relative_path

``logs`` lists paths rather than displaying file contents. Use ``--runlog`` to
select logs from inside the action launch. Both ``logs`` and ``summary`` accept
``--markdown`` for reports::

   sane view logs --errors --runlog --markdown
   sane view summary --markdown

To inspect resource events, add arrows or stems to the usage plot::

   sane view usage --arrows --stems

Legacy Commands
===============

``sane_runner`` and ``sane_view`` are deprecated aliases for
``sane workflow`` and ``sane view``. Their existing arguments remain valid;
only the command prefix changes when migrating. The legacy commands print a
deprecation notice to standard error.
