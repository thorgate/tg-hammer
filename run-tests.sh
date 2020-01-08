#!/usr/bin/env bash

set -e

PYTHON_VERSION="${PYTHON_VERSION:-2.7.13}"

DEPENDENCY_FILE='development'

if [[ ${PYTHON_VERSION} == 3* ]]; then
    DEPENDENCY_FILE='development3'
fi

echo '' > tests.log
echo "Using python:$PYTHON_VERSION" | tee tests.log

# Pull images
docker pull python:${PYTHON_VERSION}

# Generate Docker files
sed "s/\[PYTHON_VERSION\]/$PYTHON_VERSION/g" Dockerfile-master > Dockerfile-master-rendered
sed "s/\[PYTHON_VERSION\]/$PYTHON_VERSION/g" Dockerfile-slave > Dockerfile-slave-rendered

sed -i "s/\[DEPENDENCY_FILE\]/$DEPENDENCY_FILE/g" Dockerfile-master-rendered

# Build images
docker-compose build

# Bring containers up in detached mode
docker-compose up -d

# Wait for tests to complete
echo "Running tests, please wait..."
RES=`docker wait tghammer_master`

# Show logs
docker logs tghammer_master | tee tests.log

# Bring both containers down
docker-compose down

# Exit with the correct exitcode
exit $RES
