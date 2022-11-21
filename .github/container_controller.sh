#!/bin/bash

set -ex

docker build -t quay.io/karmab/kcli-controller:latest -f extras/controller/Dockerfile .

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli-controller:latest
