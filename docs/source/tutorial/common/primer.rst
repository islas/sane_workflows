.. py:module:: sane
    :no-index:

.. role:: bolditalic
    :class: bolditalic

In this tutorial we will work through creating a workflow for a
project called ``mango``. The files will be added gradually as we
build up our understanding of SANE workflows.

Run commands from the directory containing ``.sane/``. Each captured run below
uses a separate copy of its example stage under ``/home/aislas/mango/`` (for
example, ``python_grow_action``); your working directory can have another name.
The example directory for each stage is listed below its output. Copy that
stage's ``.sane/`` directory into an empty working directory to reproduce it.
Timestamps, absolute paths, and randomly generated mango counts will differ.

We will be recreating the workflow created in the |alt_doc| tutorial,
however you **do not** need to go through that tutorial first.

.. hint::

    SANE workflows tries to keep the python usage and JSON representation as
    as similar as possible. What you learn in one tutorial will translate
    smoothly to the other.

    Additionally, the JSON and python interfaces can be used in tandem within
    workflows.
