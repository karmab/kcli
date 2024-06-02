#!/bin/bash

[  -n "$COMMIT"  ] && git checkout $COMMIT
SHORT_TAG="$(git rev-parse --short HEAD)"
GIT_VERSION="$SHORT_TAG $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git

TAG="${TAG:-$SHORT_TAG}"
if [  -n "${EGG}"  ] ; then
  sed -i "s/\[all\]/\[${EGG}\]/" extras/debian
  TAG="${EGG}-${TAG}"
fi

podman build -t quay.io/karmab/kcli:$TAG -f extras/debian .
podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman push quay.io/karmab/kcli:$TAG
