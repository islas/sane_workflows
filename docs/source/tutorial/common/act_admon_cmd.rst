.. note:: The string provided to ``config["command"]`` must be an executable. Commands
          from your ``PATH`` will work, but if you use a script it must have the
          executable property. Try running:

          .. code-block:: none

              chmod +x <command script>

          if you are having issues getting your :py:class:`Action` to run your ``config["command"]``