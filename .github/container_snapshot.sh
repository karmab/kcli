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

if [ "$TAG" == "arm64" ] ; then
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
sed -i 's/bookworm/bookworm-arm64/' extras/debian
# sed -i 's/\[all\]//' extras/debian
else
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
fi

podman login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
podman build -t quay.io/karmab/kcli:$TAG -f extras/debian .
podman push quay.io/karmab/kcli:$TAG
