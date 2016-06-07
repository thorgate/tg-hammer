# tg-hammer

[![PyPI version](https://badge.fury.io/py/tg-hammer.svg)](https://badge.fury.io/py/tg-hammer)

Helpers for fabric based deployments.

## Quickstart

Install tg-hammer::

    pip install tg-hammer


## Features

See the documentation for detailed information.
https://tg-hammer.readthedocs.org

### VCS

Hammer provides unified helper api for both git and Mercurial
based projects. It can automatically detect which version control
system to use based on the current project (by inspecting project_root).

### Services

Hammer contains management helpers for the following unix service daemon utilities:

 - upstart
 - systemd
 - supervisor

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

After establishing an ssh connection use the following commands to execute the functional test suite::

    cd /vagrant
    workon hammer
    py.test

This will print tons of output and will (hopefully) result in all tests passing. Sadly it's
not possible to use py.test capturing to reduce the amount of spam since it is not compatible
with fabrics internal capturing logic.
