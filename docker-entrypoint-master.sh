#!/usr/bin/env bash

service ssh restart

py.test
# Uncomment the line below and comment the line above to leave the master running.
# tail -f /dev/null
