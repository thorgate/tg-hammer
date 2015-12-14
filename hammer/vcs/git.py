import os

from fabric import colors
from fabric.api import cd, hide, abort, local, lcd

from .base import BaseVcs


class Git(BaseVcs):
    TAG = 'git'
    NAME = 'Git'

    def repo_url(self):
        with lcd(self.project_root):
            try:
                result = local('git config --get remote.origin.url', capture=True)

            except SystemExit as e:
                if e.code == 1:
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
        with cd(self.code_dir), hide('running'):
            sep = ':|:|:'

            commit_id, message, author = self.remote_cmd(("git --no-pager log -n 1 --oneline "
                                                         "--format='%%h%(sep)s%%s%(sep)s%%an <%%ae>'") % dict(sep=sep)).split(sep)

            branch = self.get_branch('HEAD')

        return commit_id, branch, message, author

    def get_branch(self, commit_id='HEAD', ambiguous=False):
        with cd(self.code_dir), hide('running'):
            try:
                branch = self.remote_cmd('git symbolic-ref --short -q %s' % commit_id)

            except SystemExit as e:
                if e.code == 1:
                    # Previous command will exit with exit code 1 if in detached
                    # head state.
                    branch = None
                else:
                    raise  # pragma: no cover

            if not branch:
                # Lets attempt to figure out the branch
                res = self.remote_cmd("git --no-pager log -n 1 --oneline --pretty=%%d %s" % commit_id).strip(' ()').split(',')
                res = [y for y in [x.strip() for x in res] if y]

                # Figure out the matching branch name
                valid_branches = []
                for candidate in res:
                    if 'HEAD' in candidate:
                        continue

                    if candidate.startswith('origin/'):
                        candidate = candidate[7:]
                        valid_branches.append(candidate)

                # in some cases even the second command won't be
                #  able to figure out the branch
                if not valid_branches:
                    valid_branches = self.git_what_branch(commit_id)

                if not valid_branches:
                    # No compatible branch found. Oh well lets just abort...
                    abort('Could not figure out remote branch (for %s)' % commit_id)  # pragma: no cover

                elif len(valid_branches) > 1:  # pragma: no cover
                    if ambiguous:
                        return '|'.join(valid_branches)

                    # Ask the user which one is valid
                    print(colors.yellow('Could not automatically determine remote git branch '
                                        '(for %s), please pick the correct value' % commit_id))
                    print('Candidates are (use 0 to abort): %s' % (
                        ', '.join(['%d: %s' % (i + 1, x) for i, x in enumerate(valid_branches)])
                    ))

                    value = None
                    while value not in range(len(valid_branches) + 1):
                        value = raw_input('Select value: ')

                        try:
                            value = int(value)

                        except (TypeError, ValueError):
                            value = None

                    if value == 0:
                        abort('Cancel by user')

                    else:
                        return valid_branches[value - 1]

                else:
                    return valid_branches[0]

        return branch

    def pull(self):
        with cd(self.code_dir):
            self.remote_cmd('git fetch origin')

    def update(self, revision=''):
        if not revision:
            revision = 'origin/%s' % self.get_branch()

        with cd(self.code_dir):
            self.remote_cmd('git checkout %s' % revision)

    def get_all_branches(self, remote=True):
        with cd(self.code_dir):
            all_branches = self.remote_cmd('git --no-pager branch%s --color=never' % ' -r' if remote else ' -a')
            all_branches = [x.strip() for x in all_branches.splitlines(False)]

            return set(list(map(self.normalize_branch, filter(lambda y: y, all_branches))))

    def get_commit_id(self):
        with cd(self.code_dir):
            return self.remote_cmd('git --no-pager log -n 1 --oneline --pretty=%h').strip()

    def git_what_branch(self, commit_id):
        if commit_id.lower() == 'head':
            commit_id = self.get_commit_id()

        with cd(self.code_dir):
            all_branches = self.get_all_branches()
            valid_branches = []

            for branch in all_branches:
                try:
                    commit_log = self.remote_cmd(('git --no-pager log --oneline '
                                                  '%(branch)s origin/%(branch)s --pretty=%%h | grep %(commit)s') % dict(
                        branch=branch,
                        commit=commit_id,
                    ))

                    if commit_log and commit_id in commit_log:  # pragma: no branch
                        valid_branches.append(branch)

                except SystemExit as e:
                    if e.code == 1:
                        continue

                    else:
                        raise  # pragma: no cover

        return valid_branches

    def deployment_list(self, revision=''):
        if not revision:
            revision = 'origin/%s' % self.get_branch()

        with cd(self.code_dir), hide('running', 'stdout'):
            # First lets pull
            self.pull()

            revision_set = self.get_revset(' ', revision)
            revisions = self.get_revset_log(revision_set)

            if len(revisions) > 0:
                # Target is forward of the current rev
                return {'forwards': self.get_revisions(revisions), 'revset': revision_set}

            # Check if target is backwards of the current rev
            revision_set = self.get_revset(revision, ' ')
            revisions = self.get_revset_log(revision_set)

            if revisions:
                return {'backwards': list(reversed(self.get_revisions(revisions))), 'revset': revision_set}

            else:
                return {'message': "Already at target revision"}

    def _changed_files(self, revision_set):
        with cd(self.code_dir):
            result = self.remote_cmd("git --no-pager diff --name-status %s" % revision_set, quiet=True).splitlines()

            return map(lambda x: x.replace('\t', ' '), result)

    def get_revset_log(self, revs):
        with cd(self.code_dir):
            result = self.remote_cmd("git --no-pager log %s --oneline --format='%%h %%(branch)s %%an <%%ae> %%s'" % revs).strip()

            if result:
                result = result.split('\n')

                return map(self.log_add_branch, filter(lambda y: y, [x.strip() for x in result]))

            return []

    def log_add_branch(self, line, needle='branch'):
        if not line:
            return line  # pragma: no cover

        commit_hash = line.split()[0]

        if not commit_hash:
            return line  # pragma: no cover

        return line % {needle: self.get_branch(commit_hash, ambiguous=True)}

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
    def normalize_branch(branch):
        return branch.replace('origin/', '').replace('HEAD', '').replace('->', '').strip('/').strip()
