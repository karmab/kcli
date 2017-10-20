mkdir -p /root/.config
mv /root/copr /root/.config
dnf -y install wget rpm-build python2-devel copr-cli alien gcc gcc-c++ rpm-build jq libstdc++-devel ruby ruby-devel
export HOME=/root
export VERSION=`grep Version: /root/package.spec  | cut -d":" -f2 | xargs`
export RELEASE=`grep Release: /root/package.spec  | cut -d":" -f2 | xargs`
export SOURCE=`grep Source: /root/package.spec | sed "s/Source\\://" | sed "s/%{version}/$VERSION/" | xargs`
wget -P /root $SOURCE
export SHORT=${SOURCE##*/}
mkdir -p /root/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
mv /root/$SHORT /root/rpmbuild/SOURCES
rpmbuild -bs /root/package.spec
copr-cli build kcli /root/rpmbuild/SRPMS/kcli-$VERSION-$RELEASE.src.rpm
BUILD=00`copr-cli get-package --with-latest-build --name kcli karmab/kcli | jq -r '.latest_build.id'`
gem install package_cloud
wget -P /root https://copr-be.cloud.fedoraproject.org/results/karmab/kcli/fedora-25-x86_64/$BUILD-kcli/kcli-$VERSION-$RELEASE.x86_64.rpm
cd /root
alien -d *rpm
/usr/local/bin/package_cloud push karmab/kcli/ubuntu/zesty /root/*deb
/usr/local/bin/package_cloud push karmab/kcli/ubuntu/xenial /root/*deb
/usr/local/bin/package_cloud push karmab/kcli/ubuntu/yakkety /root/*deb
/usr/local/bin/package_cloud push karmab/kcli/debian/jessie /root/*deb
/usr/local/bin/package_cloud push karmab/kcli/debian/stretch /root/*deb
