export HOME=.
export PATH=/usr/local/bin:$PATH
export DEB_BUILD_OPTIONS=nocheck debuild

PACKAGES=$(cloudsmith list package karmab/kcli | grep 'python3-kcli.*99.0' | cut -d'|' -f4 | xargs | awk '{$NF=""; print $0}')
if [ "$(echo $PACKAGES | wc -w)" != "0" ] ; then
  for package in $PACKAGES ; do
    echo Deleting package $package
    cloudsmith delete $package -y
  done
fi

export VERSION="99.0.0.git."
export MINOR=$(date "+%Y%m%d%H%M").$(git rev-parse --short HEAD)
find . -name *pyc -exec rm {} \;
GIT_VERSION="$(curl -s https://github.com/karmab/kcli/commits/main | jq -r .payload.commitGroups[0].commits[0].oid | cut -c1-8) $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version $MINOR --depends python3-dateutil,python3-prettytable,python3-libvirt,genisoimage,python3-distutils,jq bdist_deb
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
