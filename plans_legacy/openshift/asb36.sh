sed -i '/OPTIONS=.*/c\OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"' /etc/sysconfig/docker
groupadd docker
usermod -aG docker fedora
systemctl start docker --ignore-dependencies
sleep 20
dnf -y install dnf-plugins-core
dnf -y copr enable @ansible-service-broker/ansible-service-broker
dnf -y install apb
chmod u+x /usr/bin/oc
wget https://raw.githubusercontent.com/openshift/ansible-service-broker/master/scripts/run_latest_build.sh
chmod +x run_latest_build.sh
export PUBLIC_IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
export ORIGIN_VERSION="v3.6.0"
sh run_latest_build.sh
