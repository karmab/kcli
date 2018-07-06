VERSION="[[ kubevirt_version ]]"
yum -y install xorg-x11-xauth virt-viewer
# sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
# setenforce 0
oc project kube-system
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/kubevirt.yaml
oc adm policy add-scc-to-user privileged -z kubevirt-privileged
oc adm policy add-scc-to-user privileged -z kubevirt-controller
oc create -f kubevirt.yaml
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/virtctl-$VERSION-linux-amd64
mv virtctl-$VERSION-linux-amd64 /usr/bin/virtctl
chmod u+x /usr/bin/virtctl
docker pull karmab/kcli
echo alias kcli=\'docker run -it --rm -v ~/.kube:/root/.kube:Z  -v $SSH_AUTH_SOCK:/ssh-agent --env SSH_AUTH_SOCK=/ssh-agent -v ~/.kcli:/root/.kcli:Z karmab/kcli\' >> /root/.bashrc
ssh-keygen -t rsa -N '' -f /root/.ssh/id_rsa
oc login --insecure-skip-tls-verify=true  `hostname`:8443 -u developer -p developer
[% if openshift_version == '3.9' %] 
setfacl -m user:107:rwx /var/lib/origin/openshift.local.pv/pv*
[% else %]
setfacl -m user:107:rwx /root/openshift.local.clusterup/openshift.local.pv/pv*
[% endif %]
