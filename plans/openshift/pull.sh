#!/usr/bin/env bash
echo openshift3/ose-haproxy-router openshift3/ose-deployer openshift3/ose-sti-builder openshift3/ose-pod openshift3/ose-docker-registry openshift3/ose-docker-builder openshift3/registry-console openshift3/ruby-20-rhel7 openshift3/mysql-55-rhel7 openshift3/php-55-rhel7 jboss-eap-6/eap64-openshift openshift3/nodejs-010-rhel7 | xargs -P10 -n1 docker pull
