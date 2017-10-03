
version="8.10-1"
build="00613039"
apt-get update
apt-get -y install wget ruby alien
export HOME=/root
gem install package_cloud
#wget -P /root ftp://rpmfind.net/linux/fedora-secondary/development/rawhide/Everything/i386/os/Packages/p/python-iptools-0.6.1-10.fc26.noarch.rpm
#wget -P /root ftp://195.220.108.108/linux/fedora/linux/development/rawhide/Everything/armhfp/os/Packages/p/python2-docker-pycreds-0.2.1-4.fc26.noarch.rpm
#wget -P /root https://copr-be.cloud.fedoraproject.org/results/karmab/kcli/fedora-25-x86_64/00550696-python-docker/python2-docker-2.2.1-1.fc25.noarch.rpm
wget -P /root https://copr-be.cloud.fedoraproject.org/results/karmab/kcli/fedora-25-x86_64/$build-kcli/kcli-$version.x86_64.rpm
cd /root
alien -d *rpm
package_cloud push karmab/kcli/ubuntu/zesty /root/*deb
package_cloud push karmab/kcli/ubuntu/xenial /root/*deb
package_cloud push karmab/kcli/ubuntu/yakkety /root/*deb
package_cloud push karmab/kcli/debian/jessie /root/*deb
package_cloud push karmab/kcli/debian/stretch /root/*deb
