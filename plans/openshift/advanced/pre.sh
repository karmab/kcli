yum -y install wget git net-tools bind-utils iptables-services bridge-utils bash-completion atomic-openshift-utils atomic-openshift-excluder atomic-openshift-docker-excluder docker
atomic-openshift-excluder unexclude
atomic-openshift-docker-excluder unexclude
systemctl enable docker
sed -i "s@# INSECURE_REGISTRY=.*@INSECURE_REGISTRY='--insecure-registry 172.30.0.0/16'@" /etc/sysconfig/docker
echo -e "DEVS=/dev/vdb\nVG=dockervg" > /etc/sysconfig/docker-storage-setup
docker-storage-setup
yum -y update
reboot
