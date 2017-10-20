#!/bin/bash

# This is the crappy script i use for version changes
# Usage release.sh ($NEW_VERSION)
# It does the following
# ask new version if not specified on command line
# check if there's a changelog
# change version in relevant files(setup.py, kvirt/config.py and extra/kcli.spec)
# commit and push code
# generate python package
# generate release with the corresponding changelog
# launch build of rpm and deb packages (using kcli product)

cd $HOME/CODE/git/KARIM/kcli
USER="karmab"
REPOSITORY="kcli"
OLDVERSION=`grep Version ~/kcli.spec | awk -F':' '{print $2}' | xargs`

if [ "$#" != "1" ] ; then
    echo "Current Version: $OLDVERSION Enter New One"
    read VERSION
else 
    VERSION=$1
fi

if [ "$VERSION" == "" ] ; then
    echo "wrong VERSION. Leaving..."
    exit 1
fi

grep -qF $VERSION changelog.md
if [ "$?" != "0" ] ; then
    echo "Missing changelog for Version $VERSION. Leaving..."
    exit 1
fi

# GRAB CHANGELOG
CHANGELOG=`sed -n "/## $VERSION.*/,/## $OLDVERSION.*/p" changelog.md | grep -v "## $OLDVERSION"`
echo -n $CHANGELOG

# SET NEW VERSIONS
sed -i s"/    version.*/    version='$VERSION',/" setup.py
sed "s/Version:.*/Version:        $VERSION/"  ~/kcli.spec
sed -i s"/__version__.*/__version__ = '$VERSION'/" kvirt/config.py

# PUSH CODE 
git commit -am "$VERSION RELEASE"
git push

# GENERATE PYTHON PACKAGE
python setup.py sdist upload

# GENERATE RELEASE
API_JSON=$(printf '{"tag_name": "v%s","target_commitish": "master","name": "v%s","body": "%s","draft": false,"prerelease": false}' $VERSION $VERSION $CHANGELOG)
curl --data "$API_JSON" https://api.github.com/repos/$USER/$REPOSITORY/releases?access_token=$RELEASETOKEN

# GENERATE RPM/DEB
kcli product copr
