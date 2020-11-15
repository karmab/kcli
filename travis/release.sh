#!/bin/bash

set -ex

if [ "$TRAVIS_BRANCH" == "master" ] && [ "$TRAVIS_PULL_REQUEST" == 'false' ] ; then
    docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
    docker push quay.io/karmab/kcli:latest
    
    if [ "$TRAVIS_TAG" != "" ]; then 
        docker login -u $QUAY_USERNAME -p $QUAY_PASSWORD quay.io
        docker push quay.io:karmab/kcli:$TRAVIS_TAG
    fi

    "./pypi.sh"
    "./packagecloud.sh"
    "./packagecloud_clean.py"
fi
