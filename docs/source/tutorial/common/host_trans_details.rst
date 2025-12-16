As far as creating a host we are basically done... Well, not really. It is a valid
host, but it does not provided much. Additionally, when running a workflow, the
expectation is that any :py:class:`Action` will always run in an :py:class:`Environment`,
even if one is not needed. Thus, hosts must provide at least one :py:class:`Environment`
to even be somewhat useful.

Let's continue to flesh out this :py:class:`Host`.