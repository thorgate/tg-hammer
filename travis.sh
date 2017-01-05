#!/usr/bin/env bash

# Build images
docker-compose build

# Bring containers up in detached mode
docker-compose up -d

# Wait for tests to complete
echo "Running tests, please wait..."
RES=`docker wait tghammer_master_1`

# Show logs
docker logs tghammer_master_1

# Bring both containers down
docker-compose down

# Exit with the correct exitcode
exit $RES
