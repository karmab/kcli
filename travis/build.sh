#!/bin/bash

set -ex

git rev-parse --short HEAD > kvirt/version/git
docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD docker.io
docker build -t quay.io/karmab/kcli -f extras/alpine .
