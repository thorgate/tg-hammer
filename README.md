# tg-hammer

.. image:: https://badge.fury.io/py/tg-hammer.png
    :target: https://badge.fury.io/py/tg-hammer

Helpers for fabric based deployments.

## Quickstart

Install tg-hammer::

    pip install tg-hammer

Then use it in your fabfile::

    from hammer.vcs import VcsProxy


    # Provide configuration to the VCS logic
    # Note: You can omit both of these keys when you
    #       want them to be retrieved from fabrics `env`
    vcs_config = {
        'use_sudo': False,              # Set to True if your target machine requires elevated privileges when running vcs commands
        'code_dir': '/srv/project',     # Directory on the target machine that will be operated on
    }
    vcs = VcsProxy.init(project_root='path to root dir of project', **vcs_config)

    # Now you can use the vcs api
    vcs.repo_url()
    > git@github.com:thorgate/tg-hammer.git


## Features

Hammer provides unified helper api for both git and Mercurial
based projects. It can automatically detect which version control
system to use based on the current project (by inspecting project_root).

See the documentation for detailed information.

https://tg-hammer.readthedocs.org


## Testing

Hammer includes functional tests that are executed inside Vagrant. Included Vagrantfile will
boot up two machines (master and slave) which will be used to execute the full test suite.
Master acts as the developer machine and slave as the server deployments are run on.

To run the tests, just execute `vagrant up` in the project root directory. After the initial 
setup completes, you can ssh into the master machine by using with the following data::

    Host: 127.0.0.1
    Port: 2222
    User: vagrant
    Pass: vagrant

After establishing an ssh connection use the following commands to execute the functional
test suite.

> cd /vagrant
> workon hammer
> py.test

This will print tons of output and will (hopefully) result in all tests passing. Sadly it's
not possible to use py.test capturing to reduce the amount of spam since it is not compatible
with fabrics internal capturing logic.
