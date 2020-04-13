#!/bin/bash

set -ex

if [ "$TRAVIS_BRANCH" == "master" ] && [ "$TRAVIS_PULL_REQUEST" == 'false' ] ; then
    docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
    docker push karmab/kcli:latest
    
    if [ "$TRAVIS_TAG" != "" ]; then 
        docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
        docker push karmab/kcli:$TRAVIS_TAG
    fi

    "./pypi.sh"
    "./packagecloud.sh"
    "./packagecloud_clean.py"
fi
