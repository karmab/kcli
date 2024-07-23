apt-get -y install nfs-kernel-server || dnf -y install nfs-utils
systemctl enable --now nfs-server

IP=$(hostname -I | cut -d" " -f1)

{% if nfs_dynamic %}

mkdir /var/nfsshare
chcon -t svirt_sandbox_file_t /var/nfsshare
chmod 777 /var/nfsshare
echo "/var/nfsshare *(rw,no_root_squash)" >> /etc/exports
exportfs -r

NAMESPACE="nfs"
BASEDIR="/root/nfs-subdir"
kubectl create namespace $NAMESPACE
git clone https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner.git $BASEDIR
kubectl project $NAMESPACE
sed -i "s/namespace:.*/namespace: $NAMESPACE/g" $BASEDIR/deploy/rbac.yaml $BASEDIR/deploy/deployment.yaml
kubectl create -f $BASEDIR/deploy/rbac.yaml
sed -i -e "s@registry.k8s.io/nfs-subdir-external-provisioner@storage.io/nfs@" -e "s@10.3.243.101@$IP@" -e "s@/ifs/kubernetes@/var/nfsshare@" $BASEDIR/deploy/deployment.yaml
echo 'apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
  name: nfs
provisioner: k8s-sigs.io/nfs-subdir-external-provisioner
parameters:
  pathPattern: "${.PVC.namespace}/${.PVC.name}"
  onDelete: delete' > $BASEDIR/deploy/class.yaml
kubectl create -f $BASEDIR/deploy/deployment.yaml -f $BASEDIR/deploy/class.yaml
{% else %}

for i in `seq -f "%03g" 1 30` ; do
mkdir /pv${i}
echo "/pv$i *(rw,no_root_squash)" >> /etc/exports
chcon -t svirt_sandbox_file_t /pv${i}
chmod 777 /pv${i}
done
exportfs -r

sed -i "s/IP/$IP/" /root/nfs.yml
for i in `seq 1 20` ; do j=`printf "%03d" ${i}` ; sed "s/001/$j/" /root/nfs.yml | kubectl create -f - ; done
for i in `seq 21 30` ; do j=`printf "%03d" ${i}` ; sed "s/001/$j/" /root/nfs.yml | sed "s/ReadWriteOnce/ReadWriteMany/" |  kubectl create -f - ; done
{% endif %}
