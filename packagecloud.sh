export HOME=.
export PATH=/usr/local/bin:$PATH
export DEB_BUILD_OPTIONS=nocheck debuild
export VERSION="99.0"
export MINOR="$(git rev-parse --short HEAD)"
sudo apt-get update
sudo apt-get -y install ruby-dev
sudo gem install rake package_cloud
find . -name *pyc -exec rm {} \;
python3 setup.py --command-packages=stdeb.command sdist_dsc --debian-version $MINOR --depends python3-dateutil,python3-prettytable,python3-flask,python3-netaddr,python3-libvirt,genisoimage bdist_deb
echo $PACKAGE_CLOUD_CREDS > .packagecloud
package_cloud push karmab/kcli/debian/jessie deb_dist/*deb
package_cloud push karmab/kcli/debian/stretch deb_dist/*deb
package_cloud push karmab/kcli/debian/buster deb_dist/*deb
package_cloud push karmab/kcli/ubuntu/cosmic deb_dist/*deb
package_cloud push karmab/kcli/ubuntu/disco deb_dist/*deb
package_cloud push karmab/kcli/ubuntu/eoan deb_dist/*deb
