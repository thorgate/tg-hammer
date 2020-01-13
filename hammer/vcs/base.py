import re

import ftfy

from hammer.util import is_fabric1


class SudoCWDContext(object):
    def __init__(self, vcs_instance, path):
        self.vcs = vcs_instance

        self.path = path

    def __enter__(self):
        self.vcs.cmd_cwd_stack.append(self.path)

        return None

    def __exit__(self, type, value, traceback):
        self.vcs.cmd_cwd_stack.pop(-1)


class BaseVcs(object):
    """ Core VCS api
    """

    TAG = 'base'
    NAME = 'Base VCS'

    def __init__(self, project_root, use_sudo=None, code_dir=None, **kwargs):
        self.project_root = project_root
        self.use_sudo = use_sudo

        self._context = None
        self._code_dir = None

        self.cmd_cwd_stack = []

        if self.use_sudo is None:
            if is_fabric1:
                from fabric.api import env
                self.use_sudo = getattr(env, 'use_sudo', False)

            else:
                raise EnvironmentError('%s: Please provide use_sudo (via init kwargs)' % self.NAME)

        if code_dir is None and is_fabric1:
            from fabric.api import env

            self.set_code_dir(getattr(env, 'code_dir', None))

        else:
            self.set_code_dir(code_dir)

    @property
    def cmd_cwd(self):
        if self.cmd_cwd_stack:
            return self.cmd_cwd_stack[-1]

        return None

    @property
    def context(self):
        if self._context is None:
            raise EnvironmentError('%s: Please attach fabric context with self.attach_context')

        return self._context

    def attach_context(self, context):
        """Bind fabric context to vcs

        This should be called from server fabric task (like test or live), for example:

        >>> vcs = Vcs.init(project_root=os.path.dirname(os.path.dirname(__file__)), use_sudo=True)
        >>>
        >>> @task(alias='test', hosts=['foo.bar.baz'])
        >>> def staging(c):
        >>>     defaults(c)
        >>>
        >>>     vcs.attach_context(c)
        >>>     ...

        :param context: Fabric Connection - http://docs.fabfile.org/en/2.5/api/connection.html#fabric.connection.Connection
        :return:
        """
        self._context = context

    @property
    def code_dir(self):
        if self._code_dir is None:
            raise EnvironmentError('%s: Please provide code_dir (via init kwargs / set_code_dir%s)' % (self.NAME,
                                                                                                       ' / `env`' if is_fabric1 else ''))

        return self._code_dir

    def set_code_dir(self, code_dir):
        """
        This should be called from server fabric task (like test or live), for example:

        >>> vcs = Vcs.init(project_root=os.path.dirname(os.path.dirname(__file__)), use_sudo=True)
        >>>
        >>> @task(alias='test', hosts=['foo.bar.baz'])
        >>> def staging(c):
        >>>     defaults(c)
        >>>
        >>>     vcs.attach_context(c)
        >>>     vcs.set_code_dir('/srv/myproject')
        >>>     ...

        :param code_dir: Repository directory on the remote machine
        :type code_dir: str
        """
        self._code_dir = code_dir

    def run(self, command, **kwargs):
        if self.cmd_cwd:
            with self.real_cd(self.cmd_cwd):
                return self._run(command, **kwargs)

        return self._run(command, **kwargs)

    def _run(self, command, **kwargs):
        if is_fabric1:
            from fabric.api import run
            return run(command, **kwargs)

        else:
            def wrapped(w_command, **w_kwargs):
                res = self.context.run(w_command, **w_kwargs)

                return res.stdout.rstrip('\n')

            return wrapped(command, **kwargs)

    def sudo(self, command, **kwargs):
        if is_fabric1:
            from fabric.api import sudo

            if self.cmd_cwd:
                with self.real_cd(self.cmd_cwd):
                    return sudo(command, **kwargs)

            return sudo(command, **kwargs)

        else:
            def wrapped(w_command, **w_kwargs):
                # Workaround for https://github.com/pyinvoke/invoke/issues/459
                # Once the issue is resolved in upstream we can make self.cd use builtin c.cd again and remove self.cmd_cwd
                #  and SudoCWDContext class
                if self.cmd_cwd:
                    w_command = ['bash -c "cd ' + self.cmd_cwd + ' && ' + w_command + '"']

                res = self.context.sudo(w_command, **w_kwargs)

                return res.stdout.rstrip('\n')

            return wrapped(command, **kwargs)

    def cd(self, path):
        if is_fabric1:
            from fabric.api import cd
            return cd(path)

        else:
            # Workaround for https://github.com/pyinvoke/invoke/issues/459
            return SudoCWDContext(self, path)

    @property
    def real_cd(self):
        if is_fabric1:
            from fabric.api import cd
            return cd

        else:
            return self.context.cd

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

    def remote_cmd(self, command, **kwargs):
        silent = kwargs.pop('silent', False)

        if silent:
            if is_fabric1:
                kwargs['quiet'] = True

                from fabric.api import hide

                # Note: The core concept of "output levels" is gone on fabric2 - see: https://www.fabfile.org/upgrading.html#upgrading
                with hide('running', 'stderr', 'stdout'):
                    return self._remote_cmd(command, **kwargs)

            kwargs['hide'] = True
            kwargs['echo'] = False

            return self._remote_cmd(command, **kwargs)

        else:
            return self._remote_cmd(command, **kwargs)

    @classmethod
    def cleanup_command_result(cls, result):
        str_result = ftfy.guess_bytes(result)[0] if is_fabric1 else result

        return ftfy.fix_text(str_result)

    def _remote_cmd(self, command, **kwargs):
        if self.use_sudo:
            return self.cleanup_command_result(self.sudo(command, **kwargs))

        else:  # pragma: no cover
            return self.cleanup_command_result(self.run(command, **kwargs))

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

                return list(filter(lambda filename: regex.search(filename), result))

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
