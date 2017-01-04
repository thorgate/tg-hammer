#!/usr/bin/env bash

docker-compose up --build -d slave
docker-compose up --build master
docker-compose down
