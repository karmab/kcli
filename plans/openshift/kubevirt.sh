VERSION="[[ kubevirt_version ]]"
yum -y install xorg-x11-xauth virt-viewer
if [ "$VERSION" == "latest" ] ; then
VERSION=`curl -s https://api.github.com/repos/kubevirt/kubevirt/releases/latest | jq -r .tag_name`
fi
oc project kube-system
grep -q vmx /proc/cpuinfo || oc create configmap -n kube-system kubevirt-config --from-literal debug.useEmulation=true
wget https://github.com/kubevirt/kubevirt/releases/download/${VERSION}/kubevirt.yaml
oc adm policy add-scc-to-user privileged -z kubevirt-privileged
oc adm policy add-scc-to-user privileged -z kubevirt-controller
oc adm policy add-scc-to-user privileged -z kubevirt-apiserver
oc create -f kubevirt.yaml --validate=false
wget https://github.com/kubevirt/kubevirt/releases/download/${VERSION}/virtctl-${VERSION}-linux-amd64
mv virtctl-${VERSION}-linux-amd64 /usr/bin/virtctl
chmod u+x /usr/bin/virtctl
docker pull karmab/kcli
echo alias kcli=\'docker run --security-opt label:disable -it --rm -v ~/.kube:/root/.kube -v ~/.ssh:/root/.ssh -v ~/.kcli:/root/.kcli -v \$PWD:/workdir karmab/kcli\' >> /root/.bashrc
ssh-keygen -t rsa -N '' -f /root/.ssh/id_rsa
oc login --insecure-skip-tls-verify=true  `hostname -I | cut -f1 -d' '`:8443 -u [[ admin_user  ]] -p [[ admin_password ]]
setfacl -m user:107:rwx /root/openshift.local.clusterup/openshift.local.pv/pv*
