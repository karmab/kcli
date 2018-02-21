sed -i '/OPTIONS=.*/c\OPTIONS="--selinux-enabled --insecure-registry 172.30.0.0/16"' /etc/sysconfig/docker
groupadd docker
usermod -aG docker fedora
systemctl start docker --ignore-dependencies
sleep 20
dnf -y install dnf-plugins-core libselinux-python
dnf -y copr enable @ansible-service-broker/ansible-service-broker-latest
dnf -y install apb
#wget https://s3.amazonaws.com/catasb/linux/amd64/oc
#mv oc /usr/bin
#wget https://apb-oc.s3.amazonaws.com/apb-oc/oc-linux-64bit.tar.gz
#tar zxvf oc-linux-64bit.tar.gz
#mv oc-linux-64bit/oc /usr/bin
#chmod u+x /usr/bin/oc
wget https://raw.githubusercontent.com/openshift/ansible-service-broker/master/scripts/run_latest_build.sh
export ORIGIN_VERSION="v[[ openshift_version ]]"
rm -rf /usr/share/rhel/secrets
[% if org is defined %]
export TEMPLATE_URL=file:///root/deploy-ansible-service-broker.template.yaml
[% endif %]
chmod +x run_latest_build.sh
export PUBLIC_IP=`ip a l  eth0 | grep 'inet ' | cut -d' ' -f6 | awk -F'/' '{ print $1}'`
sh run_latest_build.sh
oc adm policy add-cluster-role-to-user cluster-admin admin --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
oc adm policy add-cluster-role-to-user cluster-admin developer --config=/var/lib/origin/openshift.local.config/master/admin.kubeconfig
