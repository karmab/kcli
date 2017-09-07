yum -y install wget docker git
systemctl enable docker
sed -i "s@# INSECURE_REGISTRY=.*@INSECURE_REGISTRY='--insecure-registry 172.30.0.0/16'@" /etc/sysconfig/docker
echo -e "DEVS=/dev/vdb\nVG=dockervg" > /etc/sysconfig/docker-storage-setup
docker-storage-setup
wget -O /root/oc.tar.gz https://github.com/openshift/origin/releases/download/v3.7.0-alpha.1/openshift-origin-client-tools-v3.7.0-alpha.1-fdbd3dc-linux-64bit.tar.gz
cd /root ; tar zxvf oc.tar.gz
mv /root/openshift-origin-client-tools-*/oc /usr/bin
rm -rf  /root/openshift*
