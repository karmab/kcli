export HOME=.
export PATH=/usr/local/bin:$PATH
export DEB_BUILD_OPTIONS=nocheck debuild
export VERSION="99.0"
export MINOR="$(git rev-parse --short HEAD)"
sudo apt-get update
sudo apt-get -y install build-essential fakeroot python3-setuptools python3-all debhelper curl
find . -name *pyc -exec rm {} \;
curl -s https://github.com/karmab/kcli/commits/master | grep 'https://github.com/karmab/kcli/commits/master?' | sed 's@.*=\(.......\).*+.*@\1@' > kvirt/version/git > kvirt/version/git
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version $MINOR --depends python3-dateutil,python3-prettytable,python3-flask,python3-netaddr,python3-libvirt,python3-requests genisoimage bdist_deb
deb=$(realpath $(find . -name *.deb))
for id in 25 149 150 199 203 206 ; do
  curl -F "package[distro_version_id]=$id" -F "package[package_file]=@$deb" https://$PACKAGE_CLOUD_TOKEN:@packagecloud.io/api/v1/repos/karmab/kcli/packages.json
done
