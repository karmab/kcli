#!/bin/bash

set -ex

TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git
docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD docker.io
docker build -t quay.io/karmab/kcli -f extras/alpine .
docker tag quay.io/karmab/kcli:latest quay.io/karmab/kcli:$TAG

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli:latest
docker push quay.io/karmab/kcli:$TAG
