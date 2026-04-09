#!/bin/bash

[  -n "$COMMIT"  ] && git checkout $COMMIT
SHORT_TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$SHORT_TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git

TAG="${TAG:-$SHORT_TAG}"
if [  -n "${EGG}"  ] ; then
  sed -i "s/\[all\]/\[${EGG}\]/" extras/Dockerfile
  TAG="${EGG}-${TAG}"
fi

if [ "$TAG" == "arm64" ] ; then
  sed -i 's/bookworm/bookworm-arm64/' extras/Dockerfile
fi

podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman build -t quay.io/karmab/kcli:$TAG -f extras/Dockerfile .
podman push quay.io/karmab/kcli:$TAG
