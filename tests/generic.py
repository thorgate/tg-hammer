import os
import pytest

from fabric.api import env

from hammer.vcs import BaseVcs, Vcs


def test_use_sudo_loaded_from_env():
    setattr(env, 'use_sudo', 'dummy')

    vcs = BaseVcs('', code_dir='hello')

    assert vcs.use_sudo == 'dummy'


def test_code_dir_not_provided_raises():
    with pytest.raises(EnvironmentError):
        BaseVcs('')


def test_code_dir_from_env():
    setattr(env, 'code_dir', 'dummy')

    vcs = BaseVcs('')

    assert vcs.code_dir == 'dummy'


def test_invalid_vcs_raises_env_error():
    setattr(env, 'code_dir', 'dummy')

    v = Vcs.init(os.path.join('tests', 'ssh'))

    with pytest.raises(EnvironmentError):
        print(v.NAME)
