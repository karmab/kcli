VERSION="3.0.3"
yum -y install wget
wget -P /root http://releases.ansible.com/ansible-tower/setup/ansible-tower-setup-$VERSION.tar.gz
cd /root
tar xvzf ansible-tower-setup-$VERSION.tar.gz
cd ansible-tower-setup-$VERSION
rm -rf inventory
wget https://raw.githubusercontent.com/karmab/kcli/master/plans/tower/inventory
./setup.sh
