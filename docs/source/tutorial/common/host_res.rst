We see that it takes a :external:py:class:`dict` that uses :py:attr:`sane.resources.Resource`
syntax. The simple explanation is that the resource must be a non-negative integer
followed by optional binary scaling ( 'k' : 1024, 'm' : 1024 :sup:`2`, and so on), and
an optional unit designator.

The simple explanation is that the resource must be a non-negative integer
followed by optional binary scaling ( 'k' : 1024, 'm' : 1024 :sup:`2`, and so on), and
an optional unit designator.

So we have a ``forest`` :py:class:`Host` and want to add resources for our ``mango``
project workflow... Let's add ``"trees"`` (these could nominally be ``"cpus"``
or whatever resource your :py:class:`Action` would take to run):