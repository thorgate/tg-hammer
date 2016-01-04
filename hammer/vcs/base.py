import re

from fabric.api import sudo, run, env, hide


class BaseVcs(object):
    """ Core VCS api
    """

    TAG = 'base'
    NAME = 'Base VCS'

    def __init__(self, project_root, use_sudo=None, code_dir=None, **kwargs):
        self.project_root = project_root
        self.code_dir = code_dir
        self.use_sudo = use_sudo

        if self.use_sudo is None:
            self.use_sudo = getattr(env, 'use_sudo', False)

        if self.code_dir is None:
            self.code_dir = getattr(env, 'code_dir', None)

            if self.code_dir is None:
                raise EnvironmentError('%s: Please provide code_dir (via `init_kwargs` or `env`)' % self.NAME)

    def repo_url(self):
        """ Retrieve Url of the remote repository (origin|default). If remote url can't be determined None is returned.

        :return: remote url
        :rtype: str|None
        """
        raise NotImplementedError  # pragma: no cover

    def clone(self, revision=None):
        """ Clones the project to a target machine. Will abort if something goes wrong.

        :param revision: Can be used to specify a branch or commit that should be activated after cloning.
        """
        raise NotImplementedError  # pragma: no cover

    def get_branch(self):
        """ Get current active branch in target machine.

        :return: current active branch
        :rtype: string
        """
        raise NotImplementedError  # pragma: no cover

    def pull(self):
        """ Update the cloned repository on the target machine without changing
            the working copy. Internally this is done via `git fetch` or `hg pull`.
        """
        raise NotImplementedError  # pragma: no cover

    def update(self, revision=''):
        """ Update the target to specified revision or tip of currently active branch if revision is omitted.

        :param revision: Specific revision to update to
        """
        raise NotImplementedError  # pragma: no cover

    def deployment_list(self, revision=''):
        """ List revisions to apply/un-apply when updating to given revision (if not specified defaults to tip of currently active branch).

            The returned dict can have the following keys:

            - forwards:     If there are revisions to apply, this value will contain a list with information about each commit
            - backwards:    If there are revisions to un-apply, this value will contain a list with information about each commit
            - revset:       If there are some revisions to apply/un-apply this will contain a string that can be passed on to changed_files
            - message:      If no revisions are to be applied or something else is wrong, this will contain this information

        :param revision: Specific revision to diff against
        :rtype: dict
        """
        raise NotImplementedError  # pragma: no cover

    def get_revset_log(self, revs):
        """ Returns lines returned by hg|git log as a list.

        :param revs: Revision set passed onto `hg|git log`
        :return: list of commits (lines are in the following format: `commit_hash branch author description`)
        :rtype: list
        """

        raise NotImplementedError  # pragma: no cover

    def version(self):
        """ Get the commit id, branch, message and author active on the target machine

        :return: (commit_id, branch, message, author)
        :rtype: tuple
        """

        raise NotImplementedError  # pragma: no cover

    def remote_cmd(self, *args, **kwargs):
        silent = kwargs.pop('silent', False)

        if silent:
            with hide('running', 'stderr', 'stdout'):
                return self._remote_cmd(*args, **kwargs)

        else:
            return self._remote_cmd(*args, **kwargs)

    def _remote_cmd(self, *args, **kwargs):
        if not self.use_sudo:  # pragma: no cover
            return run(*args, **kwargs)

        else:
            return sudo(*args, **kwargs)  # pragma: no cover

    def _changed_files(self, revision_set):
        raise NotImplementedError  # pragma: no cover

    def changed_files(self, revision_set, filter_re=None):
        """ Returns list of files that changed in the given revset, optionally filtered by the given regex or list of regex values.

            Each returned item is a combination of the action and the file name separated by space:
            > ['A test.tx', 'M foo.bar', 'R hello_world']

        :param revision_set: Revision set to use when building changed file list
        :param filter_re: optional regex filter (or list of regex values)
        :return: files changed
        :rtype: list
        """
        result = self._changed_files(revision_set)

        if filter_re:
            def finder(pattern):
                regex = re.compile(pattern)

                return filter(lambda filename: regex.search(filename), result)

            if isinstance(filter_re, (list, tuple)):
                full_result = []

                for reg in filter_re:
                    for res in finder(reg):
                        full_result.append(res)

                result = full_result

            else:
                result = finder(filter_re)

        return result

    @classmethod
    def get_revset(cls, x, y):
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def get_revisions(cls, x):
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def detect(cls, project_root, **init_kwargs):
        """ Detect if the current VCS implementation can be used for the
            active project.

            :param project_root: Root directory of the current project
            :rtype: bool
        """

        raise NotImplementedError  # pragma: no cover
