import os
import shutil
import subprocess

import pytest

from hammer.util import is_fabric1, as_str
from hammer.vcs import Vcs


def make_repo_dir(base_dir, name):
    return os.path.join(base_dir, name)


class VcsTestUtil(object):
    def __init__(self, vcs_type):
        self.vcs_type = vcs_type
        self.handler_name = 'Git' if vcs_type == 'git' else 'Mercurial'

        self.base_dir = os.path.join(os.getcwd(), '.repos')
        self.repo_dir = make_repo_dir(self.base_dir, self.vcs_type)

        self.user_name = 'Testing user'
        self.user_email = 'test@test.sdf'
        self.commit_hash = {}

        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)

        self.reset()

    def reset(self):
        if os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)

        os.mkdir(self.repo_dir)

        self.init_empty_repo()

    def __str__(self):
        return 'VcsTestUtil: %s' % self.vcs_type

    @property
    def expected_remote(self):
        if self.vcs_type == 'git':
            return 'root@hammer.repo.host:/repos/git/test.git'

        else:
            return 'ssh://root@hammer.repo.host//repos/hg/test'

    @property
    def default_branch(self):
        return 'master' if self.vcs_type == 'git' else 'default'

    @property
    def user_full(self):
        return '%s <%s>' % (self.user_name, self.user_email)

    def get_vcs(self, code_dir=None, context=None):
        vcs = Vcs.init(project_root=self.repo_dir, code_dir=code_dir if code_dir else '/srv/%s_project' % self.vcs_type, use_sudo=False)
        vcs.attach_context(context)

        return vcs

    def init_empty_repo(self):
        if self.vcs_type == 'git':
            subprocess.check_output(['git', 'init', self.repo_dir])

            subprocess.check_output(['git', 'config', 'user.email', self.user_email], cwd=self.repo_dir)
            subprocess.check_output(['git', 'config', 'user.name', self.user_name], cwd=self.repo_dir)

        else:
            subprocess.check_output(['hg', 'init', self.repo_dir])

            with open(os.path.join(self.repo_dir, '.hg', 'hgrc'), 'w+') as handle:
                handle.write('[ui]\n')
                handle.write('username = %s <%s>\n\n' % (self.user_name, self.user_email))

    def check_status(self):
        if self.vcs_type == 'git':
            subprocess.check_output('git status'.split(), cwd=self.repo_dir)

            # Test that we don't accidentally create a false positive here, when hammer is using git as a vcs
            return as_str(subprocess.check_output('git rev-parse --show-toplevel'.split(), cwd=self.repo_dir)).strip() == self.repo_dir

        else:
            subprocess.check_output('hg status'.split(), cwd=self.repo_dir)

            # Test that we don't accidentally create a false positive here, when hammer is using hg as a vcs
            return as_str(subprocess.check_output('hg root'.split(), cwd=self.repo_dir).strip()) == self.repo_dir

    def get_commit_messages(self):
        if self.vcs_type == 'git':
            logs = as_str(subprocess.check_output("git log --oneline --format=%s".split(), cwd=self.repo_dir)).strip().split('\n')
            logs = [x.strip(' "\'') for x in logs]

            return logs

        else:
            logs = as_str(subprocess.check_output("hg log --template '{desc|firstline}\\n'".split(), cwd=self.repo_dir)).strip().split('\n')
            logs = [y for y in [x.strip(' "\'\n') for x in logs] if y]

            return logs

    def add_remote(self):
        if self.vcs_type == 'git':
            subprocess.check_output(("git remote add origin %s" % self.expected_remote).split(), cwd=self.repo_dir)

            if os.path.exists('/repos/git/test.git'):
                subprocess.check_output("rm -rf /repos/git/test.git".split())

            subprocess.check_output("mkdir -p /repos/git/test.git".split())
            subprocess.check_output("git --bare init /repos/git/test.git".split())

        else:
            # add remote path
            with open(os.path.join(self.repo_dir, '.hg', 'hgrc'), 'a+') as handle:
                handle.write('[paths]\n')
                handle.write('default = %s\n' % self.expected_remote)

            # if os.path.exists('/repos/hg/test.hg')
            if os.path.exists('/repos/hg/test'):
                subprocess.check_output("rm -rf /repos/hg/test".split())

            subprocess.check_output("mkdir -p /repos/hg/test".split())
            subprocess.check_output("hg init /repos/hg/test".split())

    def push(self, branch=False):
        if self.vcs_type == 'git':
            if branch:
                branch = 'origin %s' % branch

            else:
                branch = 'origin master'

            subprocess.check_output(("git push %s" % branch).split(), cwd=self.repo_dir)

        else:
            subprocess.check_output(("hg push%s" % (' --new-branch' if branch else '')).split(), cwd=self.repo_dir)

    def store_commit_hash(self, key, branch=None, extra_files=None, message=None):
        if branch:
            if self.vcs_type == 'git':
                branch = (('-b %s' % branch) if not isinstance(branch, list) else branch[0])
                subprocess.check_output(('git checkout %s' % branch).split(), cwd=self.repo_dir)
            else:
                if isinstance(branch, list):
                    subprocess.check_output(['hg', 'checkout', branch[0]], cwd=self.repo_dir)

                else:
                    subprocess.check_output(['hg', 'branch', branch], cwd=self.repo_dir)

        self.put_file(key)
        subprocess.check_output([self.vcs_type, 'add', key], cwd=self.repo_dir)

        if extra_files:
            for ex in extra_files:
                contents = None

                if isinstance(ex, list):
                    contents = ex[1]
                    ex = ex[0]

                self.put_file(ex, contents=contents)
                subprocess.check_output([self.vcs_type, 'add', ex], cwd=self.repo_dir)

        subprocess.check_output([self.vcs_type, 'commit', '-m%s' % (message if message is not None else key)], cwd=self.repo_dir)

        self.get_and_store_latest_hash(key)

    def get_and_store_latest_hash(self, key):
        if self.vcs_type == 'git':
            output = as_str(subprocess.check_output("git --no-pager log -n 1 --oneline --format='%h'".split(), cwd=self.repo_dir))

            self.commit_hash[key] = output.strip().strip('"\'').strip()

        else:
            out = as_str(subprocess.check_output('hg id -in'.split(), cwd=self.repo_dir)).strip()
            out = out.split()
            out.reverse()
            self.commit_hash[key] = ':'.join([x for x in out if x])

    def merge_to_stable(self, key):
        if self.vcs_type == 'git':
            subprocess.check_output('git checkout stable'.split(), cwd=self.repo_dir)
            subprocess.check_output('git merge master'.split(), cwd=self.repo_dir)

        else:
            subprocess.check_output('hg checkout stable'.split(), cwd=self.repo_dir)
            subprocess.check_output('hg merge default'.split(), cwd=self.repo_dir)
            subprocess.check_output(('hg commit -m%s' % key).split(), cwd=self.repo_dir)

        self.get_and_store_latest_hash(key)

    def create_commits_master_1(self):
        """ Creates the first 3 commits into the master|default branch
        """

        # Create the commits
        self.store_commit_hash('1.txt')
        self.store_commit_hash('2.txt')
        self.store_commit_hash('3.txt')

        return True

    def put_file(self, name, contents=None):
        with open(os.path.join(self.repo_dir, name), 'w+') as handle:
            handle.write(contents if contents is not None else name)
            handle.close()


def pytest_addoption(parser):
    parser.addoption('--hg', action='store_true', help='Test hg integration only')
    parser.addoption('--git', action='store_true', help='Test git integration only')


def pytest_generate_tests(metafunc):
    if 'repo' in metafunc.fixturenames:
        if getattr(metafunc.config.option, 'git', False):
            metafunc.parametrize('repo_type', ['git'], scope="module")

        elif getattr(metafunc.config.option, 'hg', False):
            metafunc.parametrize('repo_type', ['hg'], scope="module")

        else:
            metafunc.parametrize('repo_type', ['git', 'hg'], scope="module")


@pytest.fixture(scope='module')
def repo(repo_type):
    obj = VcsTestUtil(repo_type)

    setattr(obj, '_repo', repo_type)
    setattr(obj, '_real_dir', '.git' if repo_type == 'git' else '.hg')

    return obj


@pytest.fixture(scope='function')
def get_context(monkeypatch):
    def _get_context(hostname):
        if is_fabric1:
            monkeypatch.setattr('fabric.state.env.host_string', hostname)
            monkeypatch.setattr('fabric.state.env.use_ssh_config', True)

            return None

        else:
            from fabric import Connection

            return Connection(host=hostname)

    return _get_context
