#!/usr/bin/env bash

if [ -d /root/manifests ] ; then
 mkdir -p /var/lib/microshift/manifests
 cp /root/manifests/*y*ml /var/lib/microshift/manifests
fi
{% if podman %}
dnf -y install podman
mkdir -p /var/lib/microshift/resources/kubeadmin/$hostname
curl -o /etc/systemd/system/microshift.service https://raw.githubusercontent.com/redhat-et/microshift/main/packaging/systemd/microshift-containerized.service
{% else %}
dnf copr enable -y @redhat-et/microshift{{ '-nightly' if nightly else ''}}
dnf -y install microshift
{% endif %}
systemctl enable microshift --now
