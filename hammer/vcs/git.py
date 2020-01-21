import os
import sys
from subprocess import check_output, CalledProcessError

from hammer.colors import green, red, yellow
from hammer.util import abort, prompt, as_str, UnexpectedExit

from .base import BaseVcs


def ask_input(*args):
    if sys.version_info > (3, 0):
        return input(*args)

    else:
        return raw_input(*args)  # NOQA


class Git(BaseVcs):
    TAG = 'git'
    NAME = 'Git'

    def __init__(self, project_root, use_sudo=None, code_dir=None, **kwargs):
        self._branch_cache = {}

        super(Git, self).__init__(project_root, use_sudo, code_dir, **kwargs)

    def repo_url(self):
        """Get remote url of the current repository"""

        # Get all remotes
        remotes = as_str(check_output(['sh', '-c', "git remote -v | awk '{split($0, a); print a[1]}' | awk '!seen[$0]++'"],
                                      cwd=self.project_root)).rstrip('\n').splitlines()

        if not remotes:
            return None

        if len(remotes) > 1:
            remotes = dict([(remote_name, self._get_remote_url(remote_name)) for remote_name in remotes])

            valid_choices = ['abort', ] + list(remotes.keys())

            message = "%(question)s [%(remotes)s, Use `%(abort)s` to cancel]:" % {
                'abort': yellow('abort'),
                'question': red("Which remote to use?", bold=True),
                'remotes': ', '.join([green(x) for x in remotes.keys()]),
            }

            def validate_choice(val):
                if val in valid_choices:
                    return val

                else:
                    raise Exception('Please select a valid value')

            selected = prompt(message, validate=validate_choice)

            if selected == 'abort':
                abort('Aborted by user')

            return as_str(remotes[selected])

        else:
            return as_str(self._get_remote_url(remotes[0])) or None

    def _get_remote_url(self, remote_name):
        try:
            result = as_str(check_output(['sh', '-c', 'git config --get remote.%s.url' % remote_name], cwd=self.project_root)).rstrip('\n')

        except CalledProcessError as e:
            if e.returncode == 1:
                result = None

            else:
                raise  # pragma: no cover

        return result or None

    def clone(self, revision=None):
        repo_url = self.repo_url()

        if not repo_url:
            abort('Repo url was not found')  # pragma: no cover

        self.remote_cmd('git clone %(repo)s %(dir)s' % dict(
            repo=repo_url,
            dir=self.code_dir,
        ))

        # update to a specific version
        if revision:
            self.update(revision)

    def version(self):
        with self.cd(self.code_dir):
            sep = ':|:|:'

            commit_id, message, author = \
                self.remote_cmd(("git --no-pager log -n 1 --oneline "
                                 "--format='%%h%(sep)s%%s%(sep)s%%an <%%ae>'") % dict(sep=sep), silent=True).split(sep)

            branch = self.get_branch('HEAD')

        return commit_id, branch, message, author

    def _get_commit_branch(self, commit_id):
        candidates = []

        # Attempt to figure out the branch/branches via git branch --contains
        try:
            candidates = self.remote_cmd(
                'git for-each-ref --contains %s --format \'%%(refname)\' refs/remotes/' % commit_id,
                silent=True,
            ).strip().splitlines(False)
        except UnexpectedExit:
            # Fall back to older way of determining the branch
            try:
                candidates = self.remote_cmd(
                    'git branch --color=never -a --contains %s' % commit_id,
                    silent=True,
                ).strip().splitlines(False)
            except UnexpectedExit as e:
                # Previous command will exit with code 129 if the commit_id is invalid.
                # All other exit codes MUST trigger a fatal error
                if e.code != 129:
                    raise  # pragma: no cover

        # cleanup candidates
        def cleanup_branch_name(_branch_name):
            _branch_name = _branch_name.strip()

            if _branch_name.startswith('['):
                return None

            if _branch_name.startswith('* '):
                _branch_name = _branch_name[2:]

            if not Git._can_normalize_branch(_branch_name):
                return None

            if 'HEAD' in _branch_name:
                return None

            for prefix in ['refs/remotes/origin/', 'refs/remotes/', 'remotes/origin/', 'origin/']:
                if _branch_name.startswith(prefix):
                    _branch_name = _branch_name[len(prefix):]

            return _branch_name

        candidates = list(filter(lambda _b: _b, set(map(cleanup_branch_name, candidates))))

        # If there are still some candidates after cleanup return them
        if candidates:
            if commit_id.lower() == 'head':
                commit_id = self.get_commit_id()
            return candidates, commit_id

        # Attempt to figure out the branch via git symbolic-ref
        try:
            branch = self.remote_cmd('git symbolic-ref --short -q %s' % commit_id, silent=True)

            # Let's return the branch if we found one
            if branch:
                return [branch, ], None

        except UnexpectedExit as e:
            # Previous command will exit with code 1 if in detached head state.
            # All other exit codes MUST trigger a fatal error
            if e.code != 1:
                raise  # pragma: no cover

        # Attempt to figure out the branch using git log
        res = self.remote_cmd("git --no-pager log -n 1 --oneline --pretty=%%d %s" % commit_id, silent=True).strip(' ()').split(',')
        res = [y for y in [x.strip() for x in res] if y]
        valid_branches = []
        real_commit = None

        for candidate in res:
            if 'HEAD' in candidate:
                continue

            if candidate.startswith('origin/'):
                candidate = candidate[7:]
                valid_branches.append(candidate)

        # We got some valid branches, lets return them
        if valid_branches:
            return valid_branches, real_commit

        # in some cases the previous commands won't be able to figure out the branch.
        # Then we fall back onto using I{git_what_branch}
        # First lets check local branches
        valid_branches, real_commit = self.git_what_branch(commit_id, remote=False)

        # We got some valid branches, lets return them
        if valid_branches:
            return valid_branches, real_commit

        # Finally, lets also try remote branches via I{git_what_branch}
        # since this commit hash did not exist in local branches
        valid_branches, real_commit = self.git_what_branch(commit_id, remote=True)
        return valid_branches, real_commit

    def get_branch(self, commit_id='HEAD', ambiguous=False):
        with self.cd(self.code_dir):

            # Resolve 'HEAD' into a real commit_id so that the cache functions properly.
            if commit_id.lower() == 'head':
                commit_id = self.get_commit_id()

            # Use the branch cache, if possible.
            if commit_id and commit_id in self._branch_cache:
                return self._branch_cache[commit_id]

            valid_branches, real_commit = self._get_commit_branch(commit_id)

            if not valid_branches:
                # No compatible branch found. Oh well lets just abort...
                abort('Could not figure out remote branch (for %s)' % real_commit or commit_id)  # pragma: no cover

            elif len(valid_branches) > 1:  # pragma: no cover
                valid_branches = sorted(valid_branches)
                if ambiguous:
                    return '|'.join(valid_branches)

                # Ask the user which one is valid
                print(yellow('Could not automatically determine remote deployed git branch '
                             '(for %s), please pick the correct value' % real_commit or commit_id))
                print('Candidates are (use 0 to abort): %s' % (
                    ', '.join(['%d: %s' % (i + 1, x) for i, x in enumerate(valid_branches)])
                ))

                value = None
                while value not in range(len(valid_branches) + 1):
                    value = ask_input('Select value: ')

                    try:
                        value = int(value)

                    except (TypeError, ValueError):
                        value = None

                if value == 0:
                    abort('Cancel by user')

                else:
                    if real_commit:
                        self._branch_cache[real_commit] = valid_branches[value - 1]

                    return valid_branches[value - 1]

            else:
                if real_commit:
                    self._branch_cache[real_commit] = valid_branches[0]

                return valid_branches[0]

    def pull(self):
        with self.cd(self.code_dir):
            self.remote_cmd('git fetch origin')

    def has_revision(self, revision, locally=False):
        if revision.startswith('origin/'):
            revision_without_origin = revision[len('origin/'):]
        else:
            revision_without_origin = revision

        if locally:
            repo_url = '.'
        else:
            repo_url = self.repo_url()

        # Returns 1 if this revision (branch) exists on the remote repo or 0 if it does not.
        cmd = u'git ls-remote --heads {repo_url} {revision} | wc -l'.format(
            repo_url=repo_url, revision=revision_without_origin,
        )

        has_branch = self.remote_cmd(cmd)

        if not int(has_branch):
            try:
                self.remote_cmd(u'git show --no-pager {}'.format(revision))
                has_branch = True
            except SystemExit:
                return False
            except UnexpectedExit:
                return False

        return has_branch

    @staticmethod
    def _no_revision_error(revision):
        return u'This revision or commit_id does not exist in the repo: {}'.format(revision)

    @staticmethod
    def _no_remote_revision_allowed_error(revision):
        return u'One cannot deploy a branch that starts with "origin/". Branch given: {}'.format(revision)

    @staticmethod
    def _no_revisions_in_remote_branch_error(revision):
        return u'No revisions were found in the remote repository for the branch given: {}'.format(revision)

    @staticmethod
    def _commit_id_is_too_short(revision):
        return u'The commit id given is too short: {}'.format(revision)

    def _get_revision_and_base_branch(self, revision):
        base_branch = None
        on_new_branch = False
        revision_is_branch = False

        if len(revision) > 0:

            # Check if this is a commit_id or a branch name.
            # A valid branch name raises a ValueError.
            try:
                int(revision, 16)
                assert len(revision) > 6

            except AssertionError:
                abort(red(self._commit_id_is_too_short(revision)))

            except ValueError:
                revision_is_branch = True

                # Make sure that this branch exists in the remote repo.
                if not self.has_revision(revision):
                    abort(red(self._no_revision_error(revision)))

                # If this branch does not exist locally, we need to
                # create it so that the branch searching alg. works.
                if not self.has_revision(revision, locally=True):
                    on_new_branch = True
                    cmd = u'git fetch origin {0}:{0}'.format(revision)
                    msg_tmpl = u'Not a commit ID and the branch exists remotely. ' \
                               u'Now creating this branch locally: {} with this command: {}'
                    print(yellow(msg_tmpl.format(revision, cmd)))
                    self.remote_cmd(cmd, silent=True)
                    revision = u'origin/{}'.format(revision)

        # If no revision was given we should use the local branch.
        else:
            base_branch = self.get_branch()
            revision = u'origin/{}'.format(base_branch)

        # If revision supplied is a branch and we didn't create that
        #  branch in the previous block, lets diff against origin/revision
        #  instead of using the local version of the branch
        if revision_is_branch and not on_new_branch:
            if not revision.startswith('origin/'):
                revision = u'origin/{}'.format(revision)

        return revision, base_branch

    def update(self, revision=''):
        if revision is None:
            revision = ''

        with self.cd(self.code_dir):
            self.pull()

            revision, base_branch = self._get_revision_and_base_branch(revision)

            self.remote_cmd(u'git checkout {}'.format(revision))

    def get_all_branches(self, remote):
        with self.cd(self.code_dir):
            all_branches = self.remote_cmd('git --no-pager branch%s --color=never' % (' -r' if remote else ' -l'), silent=True)
            all_branches = [x.strip() for x in all_branches.splitlines(False)]

            return set(list(filter(lambda y: y, map(self.normalize_branch, all_branches))))

    def get_commit_id(self):
        with self.cd(self.code_dir):
            return self.remote_cmd('git --no-pager log -n 1 --oneline --pretty=%h', silent=True).strip()

    def git_what_branch(self, commit_id, remote=False):
        if commit_id.lower() == 'head':
            commit_id = self.get_commit_id()

        if self._branch_cache.get(commit_id, None) is not None:
            return [self._branch_cache[commit_id], ], commit_id

        with self.cd(self.code_dir):
            all_branches = self.get_all_branches(remote=remote)
            valid_branches = []

            for branch in all_branches:
                try:
                    commit_log = self.remote_cmd(('git --no-pager log --oneline '
                                                  '%(branch)s origin/%(branch)s --pretty=%%h | grep %(commit)s') % dict(
                        branch=branch,
                        commit=commit_id,
                    ), silent=True)

                    if commit_log and commit_id in commit_log:  # pragma: no branch
                        valid_branches.append(branch)

                except UnexpectedExit as e:
                    if e.code == 1:
                        continue

                    else:
                        raise  # pragma: no cover

        return valid_branches, commit_id

    def deployment_list(self, revision=''):
        if revision is None:
            revision = ''

        if revision.startswith('origin/'):
            abort(red(self._no_remote_revision_allowed_error(revision)))

        with self.cd(self.code_dir):
            # First lets pull
            self.pull()

            revision, base_branch = self._get_revision_and_base_branch(revision)

            revision_set = self.get_revset(' ', revision)
            revisions = self.get_revset_log(revision_set, base_branch=base_branch)
            print(' ')

            if len(revisions) > 0:
                # Target is forward of the current revision.
                return {'forwards': self.get_revisions(revisions), 'revset': revision_set}

            # Check if target is backwards from the current revision:
            revision_set = self.get_revset(revision, ' ')
            revisions = self.get_revset_log(revision_set, base_branch=base_branch)
            print(' ')

            if revisions:
                return {'backwards': list(reversed(self.get_revisions(revisions))), 'revset': revision_set}
            else:
                return {'message': "Already at target revision"}

    def _changed_files(self, revision_set):
        with self.cd(self.code_dir):
            result = self.remote_cmd("git --no-pager diff --name-status %s" % revision_set, silent=True).splitlines()

            return list(map(lambda x: x.replace('\t', ' '), result))

    def get_revset_log(self, revs, base_branch=None):
        with self.cd(self.code_dir):
            result = self.remote_cmd("git --no-pager log --oneline --format='%%h {} %%an <%%ae> %%s' %s" % revs, silent=True).strip()

            if result:
                result = result.split('\n')

                return list(map(lambda z: self.log_add_branch(z, base_branch=base_branch),
                                filter(lambda y: y, [x.strip() for x in result])))

            return []

    def log_add_branch(self, line, base_branch=None):
        if not line:
            return line  # pragma: no cover

        commit_hash = line.split()[0]

        if not commit_hash:
            return line  # pragma: no cover

        def get_branch():
            print(yellow(u'Figuring out branch for commit: {}'.format(line.replace('{}', '-'))))
            return self.get_branch(commit_hash, ambiguous=True)

        # The line begins with commit hash and then "{}", thus we can be certain that the first occurrence of "{}" is
        #  the one we're interested in.
        return line.replace('{}', base_branch if base_branch is not None else get_branch(), 1)

    @classmethod
    def get_revset(cls, x, y):
        assert x and y, NotImplementedError('With git, get_revset should always have x and y')

        return '%s..%s' % (x, y)

    @classmethod
    def get_revisions(cls, x):
        return list(reversed(x))

    @classmethod
    def detect(cls, project_root, **init_kwargs):
        return os.path.exists(os.path.join(project_root, '.git'))

    @staticmethod
    def _can_normalize_branch(branch):
        return branch and 'detached from' not in branch and 'detached at' not in branch

    @staticmethod
    def normalize_branch(branch):
        if not Git._can_normalize_branch(branch):
            return None

        return branch.replace('origin/', '').replace('HEAD', '').replace('->', '').strip('/').strip()
