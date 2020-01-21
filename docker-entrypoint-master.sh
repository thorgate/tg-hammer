#!/usr/bin/env bash

service ssh restart

coverage run -m py.test -v
# Uncomment the line below and comment the line above to leave the master running.
# tail -f /dev/null

RES=$?

# Report coverage
coverage report && coverage html

# Exit with correct exitcode
exit $RES
