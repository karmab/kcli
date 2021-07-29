#!/bin/bash

set -ex

git rev-parse --short HEAD > kvirt/version/git
docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD docker.io
docker build -t quay.io/karmab/kcli -f extras/alpine .

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli:latest
