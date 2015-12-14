tg-hammer documentation
=======================

Contents:

.. toctree::
   :maxdepth: 2

Introduction
============

Hammer provides unified helper api for both git and Mercurial
based projects. It can automatically detect which version control
system to use based on the current project (by inspecting project_root).

VCS API
=======

.. py:module:: hammer.vcs
.. autoclass:: BaseVcs
   :members: repo_url, clone, version, get_branch, pull, update, deployment_list, get_revset_log, changed_files

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

