yum -y install wget git net-tools bind-utils iptables-services bridge-utils bash-completion atomic-openshift-utils atomic-openshift-excluder atomic-openshift-docker-excluder
atomic-openshift-excluder unexclude
atomic-openshift-docker-excluder unexclude
[% if not crio %]
yum -y install docker
sed -i "s@# INSECURE_REGISTRY=.*@INSECURE_REGISTRY='--insecure-registry 172.30.0.0/16'@" /etc/sysconfig/docker
echo -e "DEVS=/dev/vdb\nVG=dockervg" > /etc/sysconfig/docker-storage-setup
docker-storage-setup
[% if not registry.startswith('redhat' %]
echo """ADD_REGISTRY='--add-registry [[ registry ]]'
INSECURE_REGISTRY='--insecure-registry [[ registry ]]'""" >> /etc/sysconfig/docker
[% endif %]
systemctl enable docker
systemctl start docker
[% endif %]

yum -y update
yum -y install NetworkManager
systemctl enable NetworkManager
systemctl start  NetworkManager
