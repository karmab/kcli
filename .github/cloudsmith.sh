export HOME=.
export PATH=/usr/local/bin:$PATH
export DEB_BUILD_OPTIONS=nocheck debuild

PACKAGES=$(cloudsmith list package karmab/kcli | grep 'python3-kcli.*99.0' | cut -d'|' -f4 | xargs | awk '{$NF=""; print $0}')
[ "$(echo $PACKAGES | wc -w)" == "0" ] && exit 0
for package in $PACKAGES ; do
 cloudsmith delete $package -y
done

export VERSION="99.0.0.git."
export MINOR=$(date "+%Y%m%d%H%M").$(git rev-parse --short HEAD)
find . -name *pyc -exec rm {} \;
GIT_VERSION="$(curl -s https://github.com/karmab/kcli/commits/master | grep 'https://github.com/karmab/kcli/commits/master?' | sed 's@.*=\(.......\).*+.*@\1@') $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version $MINOR --depends python3-dateutil,python3-prettytable,python3-flask,python3-libvirt,python3-requests,genisoimage,python3-distutils bdist_deb
deb=$(realpath $(find . -name *.deb))
cloudsmith push deb karmab/kcli/any-distro/any-version $deb
