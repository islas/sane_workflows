Before we create a new :py:class:`Action` for our workflow, we should first discuss
how it will tie in and depend on our ``"grow_action"``.

When running multiple :py:class:`Action` in a workflow, it may be beneficial to
have them run in a very particular order. This is where the directed acyclic
graph (`DAG`_) nature of SANE workflows comes into play.

Dependencies between :py:class:`Action` are mapped out based on :math:`child \rightarrow N parents`
relationships, where each :py:class:`Action` lists the parents it is dependent on.

:py:class:`Action` can have any number of :py:attr:`~Action.dependencies`, so long
as the dependencies never form a closed loop. In other words, an :py:class:`Action`
**CAN NEVER** be the ancestor (parent) to any of its own ancestors. If thought of
as a family tree, any single :py:class:`Action` **CAN NEVER** reappear earlier in
its lineage.

.. container:: twocol

    .. container:: leftside

      **BAD**: Dependency Graph with cycles

      .. graphviz::

        digraph foo {
            "bar" -> "baz";
            "baz" -> "boo";
            "baz" -> "foo";
            "foo" -> "bar";
        }

    .. container:: rightside

      **OKAY**: Dependency Graph with no cycles

      .. graphviz::

        digraph foo {
            "bar" -> "baz";
            "baz" -> "boo";
            "baz" -> "foo";
            "foo" -> "zoo";
        }

This is the first :py:class:`Action` in our workflow, so it will not have any
dependencies.
