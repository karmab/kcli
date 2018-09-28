VERSION="[[ kubevirt_version ]]"
KUBELET_ROOTFS=/var/lib/docker/devicemapper/mnt/$(docker inspect $(docker ps | grep kubelet | cut -d" " -f1) | grep DeviceName  | awk -F- '{print $4}' | sed 's/",//')/rootfs
mkdir -p /var/lib/kubelet/device-plugins $KUBELET_ROOTFS/var/lib/kubelet/device-plugins
mount -o bind $KUBELET_ROOTFS/var/lib/kubelet/device-plugins /var/lib/kubelet/device-plugins
yum -y install xorg-x11-xauth virt-viewer
oc project kube-system
[% if emulation %]
oc create configmap -n kube-system kubevirt-config --from-literal debug.useEmulation=true
[% endif %]
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/kubevirt.yaml
oc adm policy add-scc-to-user privileged -z kubevirt-privileged
oc adm policy add-scc-to-user privileged -z kubevirt-controller
oc adm policy add-scc-to-user privileged -z kubevirt-apiserver
oc create -f kubevirt.yaml --validate=false
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/virtctl-$VERSION-linux-amd64
mv virtctl-$VERSION-linux-amd64 /usr/bin/virtctl
chmod u+x /usr/bin/virtctl
docker pull karmab/kcli
echo alias kcli=\'docker run --security-opt label:disable -it --rm -v ~/.kube:/root/.kube -v ~/.ssh:/root/.ssh -v ~/.kcli:/root/.kcli -v \$PWD:/workdir karmab/kcli\' >> /root/.bashrc
ssh-keygen -t rsa -N '' -f /root/.ssh/id_rsa
oc login --insecure-skip-tls-verify=true  `hostname -I | cut -f1 -d' '`:8443 -u developer -p developer
setfacl -m user:107:rwx /root/openshift.local.pv/pv*
