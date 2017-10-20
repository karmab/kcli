
export VERSION=`grep Version: /root/package.spec  | cut -d":" -f2 | xargs`
build="00645037"
apt-get update
apt-get -y install wget ruby alien ruby-dev
export HOME=/root
gem install package_cloud
wget -P /root https://copr-be.cloud.fedoraproject.org/results/karmab/kcli/fedora-25-x86_64/$build-kcli/kcli-$VERSION.x86_64.rpm
cd /root
alien -d *rpm
package_cloud push karmab/kcli/ubuntu/zesty /root/*deb
package_cloud push karmab/kcli/ubuntu/xenial /root/*deb
package_cloud push karmab/kcli/ubuntu/yakkety /root/*deb
package_cloud push karmab/kcli/debian/jessie /root/*deb
package_cloud push karmab/kcli/debian/stretch /root/*deb
