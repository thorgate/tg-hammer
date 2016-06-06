API
===

Vcs
---

.. py:module:: hammer.vcs
.. autoclass:: BaseVcs
   :members: repo_url, clone, version, get_branch, pull, update, deployment_list, get_revset_log, changed_files


service_helpers
---------------

.. py:module:: hammer.service_helpers

.. py:attribute:: DAEMON_TYPES

   Hammer supports the following daemon types out of the box

   - upstart
   - systemd
   - supervisor

.. autofunction:: install_services_cp
.. autofunction:: install_services
.. autofunction:: manage_service
