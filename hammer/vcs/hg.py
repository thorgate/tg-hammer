import os
from subprocess import CalledProcessError, check_output

from hammer.util import abort, as_str

from .base import BaseVcs


class Mercurial(BaseVcs):
    TAG = 'hg'
    NAME = 'Mercurial'

    def version(self):
        with self.cd(self.code_dir):
            commit_id, branch = self.remote_cmd('hg id -nb', silent=True).split()

            separator = ':|:|:'
            c_hash, author, message = self.remote_cmd(("hg --config ui.color=never --config ui.paginate=never log --template "
                                                       "'{node|short}%(sep)s{author}%(sep)s{desc|firstline}\\n' -r %(id)s") % dict(
                sep=separator,
                id=commit_id,
            ), silent=True).split(separator)

            commit_id = '%s:%s' % (commit_id, c_hash)

        return commit_id, branch, message, author

    def repo_url(self):
        try:
            result = as_str(check_output(['sh', '-c', 'hg paths default'], cwd=self.project_root)).rstrip('\n')

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

        self.remote_cmd('hg clone %s %s' % (repo_url, self.code_dir))

        if revision:
            self.update(revision)

    def get_branch(self):
        with self.cd(self.code_dir):
            return self.remote_cmd('hg id -b', silent=True).strip()

    def pull(self):
        with self.cd(self.code_dir):
            self.remote_cmd('hg pull', silent=True)

    def update(self, revision=''):
        # Default revision to empty string if it is None
        revision = revision or ''

        self.pull()

        with self.cd(self.code_dir):
            self.remote_cmd('hg update %s' % revision)

    def get_revset_log(self, revs):
        with self.cd(self.code_dir):
            result = self.remote_cmd("hg --config ui.color=never --config ui.paginate=never log --template '{rev}:{node|short} {branch} "
                                     "{author} {desc|firstline}\\n' -r '%s'" % revs, silent=True)

            if not result:
                return []

            return list(filter(lambda y: y, [x.strip() for x in (result.split('\n') or [])]))

    def deployment_list(self, revision=''):
        with self.cd(self.code_dir):
            # First lets pull
            self.pull()

            revision_set = self.get_revset('.', revision)
            revisions = self.get_revset_log(revision_set)

            if len(revisions) > 1:
                # Target is forward of the current rev
                return {'forwards': self.get_revisions(revisions), 'revset': revision_set}

            elif len(revisions) == 1:
                # Current rev is the same as target
                return {'message': "Already at target revision"}

            # Check if target is backwards of the current rev
            revision_set = self.get_revset(revision, '.')
            revisions = self.get_revset_log(revision_set)

            if revisions:
                return {'backwards': list(reversed(self.get_revisions(revisions))), 'revset': revision_set}

            else:
                return {'message': "Target revision is not related to the current revision"}  # pragma: no cover

    def _changed_files(self, revision_set):
        with self.cd(self.code_dir):
            result = self.remote_cmd("hg --config ui.color=never --config ui.paginate=never status --rev '%s'" % revision_set,
                                     silent=True).splitlines()

            return result

    @classmethod
    def get_revset(cls, x, y):
        assert x or y

        if x and y:
            # All revisions that are descendants of the current revision and ancestors of the target revision
            #  (inclusive), but not the current revision itself
            return '%s::%s' % (x, y)
        else:
            # All revisions that are in the current branch, are descendants of the current revision and are not the
            #  current revision itself.
            return 'branch(p1()) and %s::%s' % (x or '', y or '')

    @classmethod
    def get_revisions(cls, x):
        return x[1:]

    @classmethod
    def detect(cls, project_root, **init_kwargs):
        return os.path.exists(os.path.join(project_root, '.hg'))
