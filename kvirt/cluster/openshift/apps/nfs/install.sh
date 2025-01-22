#!/usr/bin/env bash

SHARE={{ nfs_share or '/var/nfsshare-%s' % cluster }}

{% if nfs_ip == None %}
export IP={{ nfs_network|local_ip }}
if [ "$(which apt-get)" != "" ] ; then
 SERVICE=nfs-kernel-server
 sudo apt-get -y install nfs-kernel-server
else
 # Latest nfs-utils 2.3.3-51 is broken
 rpm -qi nfs-utils >/dev/null 2>&1 || sudo dnf -y install nfs-utils
 test ! -f /usr/lib/systemd/system/firewalld.service || sudo systemctl disable --now firewalld
 SERVICE=nfs-server
fi
sudo systemctl enable --now $SERVICE
if [ ! -d $SHARE ] ; then
 sudo mkdir $SHARE
 sudo chcon -t svirt_sandbox_file_t $SHARE
 sudo chmod 777 $SHARE
 echo "$SHARE *(rw,no_root_squash)"  | sudo tee -a /etc/exports
 sudo exportfs -r
fi
{% else %}
IP={{ nfs_ip }}
{% endif %}

NAMESPACE="{{ nfs_namespace }}"
BASEDIR="nfs-subdir"
oc create namespace $NAMESPACE
git clone https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner.git $BASEDIR
oc project $NAMESPACE
sed -i "s/namespace:.*/namespace: $NAMESPACE/g" $BASEDIR/deploy/rbac.yaml $BASEDIR/deploy/deployment.yaml
oc create -f $BASEDIR/deploy/rbac.yaml
oc adm policy add-scc-to-user hostmount-anyuid system:serviceaccount:$NAMESPACE:nfs-client-provisioner

{% if nfs_disconnected_registry != None %}
 echo sync registry.k8s.io/sig-storage/nfs-subdir-external-provisioner:v4.0.2 to your registry
 REGISTRY={{ nfs_disconnected_registry }}
 sed -i "s@registry.k8s.io@$REGISTRY:5000@" $BASEDIR/deploy/deployment.yaml
{% endif %}

sed -i -e "s@registry.k8s.io/nfs-subdir-external-provisioner@storage.io/nfs@" -e "s@10.3.243.101@$IP@" -e "s@/ifs/kubernetes@$SHARE@" $BASEDIR/deploy/deployment.yaml
echo 'apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs
{% if nfs_default_storageclass %}
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
{% endif %}
provisioner: k8s-sigs.io/nfs-subdir-external-provisioner
parameters:
  pathPattern: "${.PVC.namespace}/${.PVC.name}"
  onDelete: delete' > $BASEDIR/deploy/class.yaml
oc create -f $BASEDIR/deploy/deployment.yaml -f $BASEDIR/deploy/class.yaml
{% if not nfs_default_storageclass %}
echo Run the following command to make odf-storagecluster-ceph-rbd the default storage class
echo oc patch storageclass nfs -p \'{\"metadata\": {\"annotations\":{\"storageclass.kubernetes.io/is-default-class\":\"true\"}}}\'
{% endif %}
