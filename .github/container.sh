#!/bin/bash

set -ex

TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git

podman build -t quay.io/karmab/kcli:latest -f extras/debian .
podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman push quay.io/karmab/kcli:latest

# podman build --arch=amd64 -t quay.io/karmab/kcli:amd64 -f extras/debian .
# podman build --arch=arm64 -t quay.io/karmab/kcli:arm64 -f extras/debian .
# podman manifest create quay.io/karmab/kcli:latest
# podman manifest add quay.io/karmab/kcli:latest docker://quay.io/karmab/kcli:amd64
# podman manifest add quay.io/karmab/kcli:latest docker://quay.io/karmab/kcli:arm64
# podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
# podman manifest push --all quay.io/karmab/kcli:latest docker://quay.io/karmab/kcli:latest
