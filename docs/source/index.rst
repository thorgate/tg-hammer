tg-hammer documentation
=======================

Introduction
============

Hammer provides unified helpers fabric based deployments.

Features
--------

vcs
***

Unified helper api for both git and Mercurial based projects. It can automatically detect which version control
system to use based on the current project (by inspecting project_root env variable).

service_helpers
***************

Management helpers for the following unix service daemon utilities:

 - upstart
 - systemd
 - supervisor


.. toctree::
   :maxdepth: 3

   install
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

