export HOME=.
export PATH=/usr/local/bin:$PATH
export DEB_BUILD_OPTIONS=nocheck debuild
export VERSION="99.0"
export MINOR="$(git rev-parse --short HEAD)"
sudo apt-get update
sudo apt-get -y install build-essential fakeroot python3-setuptools python3-all debhelper curl genisoimage python3-stdeb
find . -name *pyc -exec rm {} \;
curl -s https://github.com/karmab/kcli/commits/master | grep 'https://github.com/karmab/kcli/commits/master?' | sed 's@.*=\(.......\).*+.*@\1@' > kvirt/version/git > kvirt/version/git
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version $MINOR --depends python3-dateutil,python3-prettytable,python3-flask,python3-netaddr,python3-libvirt,python3-requests,genisoimage,python3-distutils bdist_deb
deb=$(realpath $(find . -name *.deb))
pip3 install cloudsmith-cli
cloudsmith push deb karmab/kcli/any-distro/any-version $deb
