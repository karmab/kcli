#!/bin/bash

export HOME=.
export PATH=/usr/local/bin:$PATH
export DEB_BUILD_OPTIONS=nocheck debuild

. venv/bin/activate

PACKAGES=$(cloudsmith list package karmab/kcli | grep 'python3-kcli.*99.0' | cut -d'|' -f4 | xargs | awk '{$NF=""; print $0}')
if [ "$(echo $PACKAGES | wc -w)" != "0" ] ; then
  for package in $PACKAGES ; do
    echo Deleting package $package
    cloudsmith delete $package -y
  done
fi

export VERSION="99.0.0.git."
export MINOR=$(date "+%Y%m%d%H%M").$(git rev-parse --short HEAD)
find kvirt -name *pyc -exec rm {} \;
GIT_VERSION="$(git ls-remote https://github.com/karmab/kcli | head -1 | cut -c1-7) $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git
sudo rm -rf kcli.egg-info
sudo sed -i "s/SafeConfigParser/ConfigParser/" venv/lib/python3.*/site-packages/stdeb/util.py
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version $MINOR --depends python3-dateutil,python3-prettytable,python3-libvirt,genisoimage,python3-distutils,git bdist_deb
deb=$(realpath $(find . -name *.deb))

# ugly fix for unknown compression for member 'control.tar.zst'
ar x $deb
unzstd control.tar.zst
unzstd data.tar.zst
xz --threads=0 --verbose control.tar
xz --threads=0 --verbose data.tar
rm -f $deb
ar cr $deb debian-binary control.tar.xz data.tar.xz

echo pushing $deb
cloudsmith push deb karmab/kcli/any-distro/any-version $deb
