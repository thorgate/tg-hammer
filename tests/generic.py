import os
import pytest

from hammer.vcs import BaseVcs, Vcs
from hammer.util import is_fabric1


@pytest.mark.skipif(not is_fabric1, reason='env is only available on fabric 1')
def test_use_sudo_loaded_from_env():
    from fabric.api import env

    setattr(env, 'use_sudo', 'dummy')

    vcs = BaseVcs('', code_dir='hello')

    assert vcs.use_sudo == 'dummy'


def test_use_sudo_loaded_from_arg():
    vcs = BaseVcs('', code_dir='hello', use_sudo='dummy')

    assert vcs.use_sudo == 'dummy'


def test_code_dir_not_provided_raises():
    with pytest.raises(EnvironmentError):
        BaseVcs('')


@pytest.mark.skipif(not is_fabric1, reason='env is only available on fabric 1')
def test_code_dir_from_env():
    from fabric.api import env

    setattr(env, 'code_dir', 'dummy')

    vcs = BaseVcs('')

    assert vcs.code_dir == 'dummy'


def test_code_dir_loaded_from_arg():
    vcs = BaseVcs('', code_dir='hello', use_sudo=False)

    assert vcs.code_dir == 'hello'


def test_invalid_vcs_raises_env_error():
    v = Vcs.init(os.path.join('tests', 'ssh'), code_dir='hello', use_sudo=False)

    with pytest.raises(EnvironmentError):
        print(v.NAME)
