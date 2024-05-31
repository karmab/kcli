#!/bin/bash

set -ex

[ -n "$COMMIT" ] && git checkout $COMMIT
TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git

podman build -t quay.io/karmab/kcli:$TAG -f extras/debian .
podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman push quay.io/karmab/kcli:$TAG
