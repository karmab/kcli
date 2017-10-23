#!/bin/bash

# This is the crappy script i use for version changes
# Usage release.sh ($NEW_VERSION)
# It does the following
# ask new version if not specified on command line
# check if there's a changelog for this version in the wiki
# change version in relevant files(wiki home, setup.py, kvirt/config.py and extra/kcli.spec)
# commit and push code
# generate python package
# generate release without the changelog :( and using RELEASETOKEN env variable
# launch build of rpm and deb packages (using kcli product)
# displays the changelog so it can be added manually

BASEDIR="$HOME/CODE/git/KARIM"
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

cd $BASEDIR/$REPOSITORY
ls $REPOSITORY.wiki/v$VERSION.md
if [ "$?" != "0" ] ; then
    echo "Missing changelog file in wiki for version $VERSION. Leaving..."
    exit 1
fi

# SET NEW VERSION
sed -i s"@tags/v.*@tags/$VERSION@" home.md
git commit -am "$VERSION RELEASE"
git push


cd $BASEDIR/$REPOSITORY
# SET NEW VERSIONS
sed -i s"/    version.*/    version='$VERSION',/" setup.py
sed -i "s/Version:.*/Version:        $VERSION/"  ~/kcli.spec
sed -i s"/__version__.*/__version__ = '$VERSION'/" kvirt/config.py

# PUSH CODE 
git commit -am "$VERSION RELEASE"
git push

# GENERATE PYTHON PACKAGE
python setup.py sdist upload

# GENERATE RELEASE
API_JSON=$(printf '{"tag_name": "v%s","target_commitish": "master","name": "v%s","body": "[release notes](https://github.com/karmab/kcli/blob/master/changelog/%s.md)","draft": false,"prerelease": false}' $VERSION $VERSION $VERSION)
curl --data "$API_JSON" https://api.github.com/repos/$USER/$REPOSITORY/releases?access_token=$RELEASETOKEN

# GENERATE RPM/DEB
kcli delete --yes copr
kcli product -c copr
