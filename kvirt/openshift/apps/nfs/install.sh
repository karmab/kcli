#!/usr/bin/env bash

SHARE={{ nfs_share or '/var/nfsshare-%s' % cluster }}

{% if nfs_ip == None %}
export IP={{ nfs_network|local_ip }}
# Latest nfs-utils 2.3.3-51 is broken
rpm -qi nfs-utils >/dev/null 2>&1 || dnf -y install nfs-utils
test ! -f /usr/lib/systemd/system/firewalld.service || systemctl disable --now firewalld
systemctl enable --now nfs-server
if [ ! -d $SHARE ] ; then
 mkdir $SHARE
 chcon -t svirt_sandbox_file_t $SHARE
 chmod 777 $SHARE
 echo "$SHARE *(rw,no_root_squash)"  >>  /etc/exports
exportfs -r
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
 echo sync k8s.gcr.io/sig-storage/nfs-subdir-external-provisioner:v4.0.2 to your registry
 REGISTRY_NAME={{ nfs_disconnected_registry }}
 sed -i "s@k8s.gcr.io@$REGISTRY_NAME:5000@" $BASEDIR/deploy/deployment.yaml
{% endif %}

sed -i -e "s@k8s-sigs.io/nfs-subdir-external-provisioner@storage.io/nfs@" -e "s@10.3.243.101@$IP@" -e "s@/ifs/kubernetes@$SHARE@" $BASEDIR/deploy/deployment.yaml
echo 'apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
   name: nfs
provisioner: storage.io/nfs
parameters:
  pathPattern: "${.PVC.namespace}/${.PVC.name}"
  onDelete: delete' > $BASEDIR/deploy/class.yaml
oc create -f $BASEDIR/deploy/deployment.yaml -f $BASEDIR/deploy/class.yaml
{% if nfs_default_storageclass %}
oc patch storageclass nfs -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
{% endif %}
