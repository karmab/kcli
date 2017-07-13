yum -y install wget docker
systemctl enable docker
sed -i "s@# INSECURE_REGISTRY=.*@INSECURE_REGISTRY='--insecure-registry 172.30.0.0/16'@" /etc/sysconfig/docker
echo -e "DEVS=/dev/vdb\nVG=dockervg" > /etc/sysconfig/docker-storage-setup
docker-storage-setup
wget -O /root/oc.tar.gz https://github.com/openshift/origin/releases/download/v3.6.0-alpha.2/openshift-origin-client-tools-v3.6.0-alpha.2-3c221d5-linux-64bit.tar.gz
cd /root ; tar zxvf oc.tar.gz
mv /root/openshift-origin-client-tools-v3.6.0-alpha.2-3c221d5-linux-64bit/oc /usr/bin
rm -rf  /root/openshift*
