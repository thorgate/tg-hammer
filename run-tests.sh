#!/usr/bin/env bash

# Build images
docker-compose build

# Bring slave up in detached mode
docker-compose up -d slave

# Run tests
docker-compose run master /hammer/docker-entrypoint-master.sh
RES=$?

# Bring both containers down
docker-compose down

# Exit with the correct exitcode
exit $RES
