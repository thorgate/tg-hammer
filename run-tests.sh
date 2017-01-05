#!/usr/bin/env bash

docker-compose up --build -d slave
docker-compose up --build master

# Bring both containers down
docker-compose down

# Exit with the correct exitcode
exit $RES
