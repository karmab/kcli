VERSION="[[ kubevirt_version ]]"
yum -y install xorg-x11-xauth virt-viewer
oc project kube-system
[% if emulation %]
oc create configmap -n kube-system kubevirt-config --from-literal debug.allowEmulation=true
[% endif %]
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/kubevirt.yaml
oc adm policy add-scc-to-user privileged -z kubevirt-privileged
oc adm policy add-scc-to-user privileged -z kubevirt-controller
oc create -f kubevirt.yaml --validate=false
wget https://github.com/kubevirt/kubevirt/releases/download/$VERSION/virtctl-$VERSION-linux-amd64
mv virtctl-$VERSION-linux-amd64 /usr/bin/virtctl
chmod u+x /usr/bin/virtctl
docker pull karmab/kcli
echo alias kcli=\'docker run --security-opt label:disable -it --rm -v ~/.kube:/root/.kube:Z  -v \$SSH_AUTH_SOCK:/ssh-agent --env SSH_AUTH_SOCK=/ssh-agent -v ~/.kcli:/root/.kcli:Z karmab/kcli\' >> /root/.bashrc
ssh-keygen -t rsa -N '' -f /root/.ssh/id_rsa
oc login --insecure-skip-tls-verify=true  `hostname`:8443 -u developer -p developer
[% if openshift_version == '3.9' %] 
setfacl -m user:107:rwx /var/lib/origin/openshift.local.pv/pv*
[% else %]
setfacl -m user:107:rwx /root/openshift.local.clusterup/openshift.local.pv/pv*
[% endif %]
