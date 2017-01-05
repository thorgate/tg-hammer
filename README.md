# tg-hammer

[![Build Status](https://travis-ci.org/thorgate/tg-hammer.svg?branch=master)](https://travis-ci.org/thorgate/tg-hammer)
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

Hammer includes functional tests that are executed inside Docker containers. The file
`run-tests.sh` executes three `docker-compose` commands that first brings up a slave server,
then a master server which executes the tests during building, and brings both of these down
after execution. The master acts as the developer machine and the slave as the server
where deployments are run on.

To run the tests manually, first comment out the line:

    py.test

and uncomment the line

    # tail -f /dev/null

inside `docker-entrypoint-master.sh`. This will keep both the master and slave running when
you execute

    docker-compose up --build

Now you can enter a `bash` shell inside the master by executing:

    docker exec -it tghammer_master_1 /bin/bash

At this point you can simply execute

    py.test

to run the tests.

Either method of running the tests will print tons of output and will (hopefully) result in all tests
passing. Sadly it is not possible to use `py.test` capturing to reduce the amount of spam because
this program is not compatible with `fabric`'s internal capturing logic.
