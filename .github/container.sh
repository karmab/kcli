#!/bin/bash

set -ex

TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git
docker build -t quay.io/karmab/kcli:latest -f extras/debian .

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli:latest
