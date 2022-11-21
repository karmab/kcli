#!/bin/bash

set -ex

cd extras/controller
docker build -t quay.io/karmab/kcli-controller:latest .

docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
docker push quay.io/karmab/kcli-controller:latest
