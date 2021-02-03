#!/usr/bin/env bash

echo "Waiting for /opt/openshift/.bootkube.done"
until ls /opt/openshift/.bootkube.done; do
  sleep 5
done
echo "Executing coreos-installer with ignition file /opt/openshift/master.ign and device /dev/{{ sno_disk | basename }}"
coreos-installer install --firstboot-args="console=tty0 rd.neednet=1" --ignition=/opt/openshift/master.ign /dev/{{ sno_disk |basename }} && shutdown -r now "Bootstrap completed, restarting node"
