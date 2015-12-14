import pytest

from fabric.api import env

from hammer.vcs import BaseVcs


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
