[ -d $HOME/.config ] || mkdir $HOME/.config
echo $COPR_BASE64 | base64 -d > $HOME/.config/copr
tar -C .. -Pczf /tmp/kcli.tar.gz --exclude=".*" kcli
mkdir -p $HOME/rpmbuild/{SOURCES,SRPMS}
mv /tmp/kcli.tar.gz $HOME/rpmbuild/SOURCES
export GIT_CUSTOM_VERSION=0.0.git.$(date "+%Y%m%d%H%M").$(git rev-parse --short HEAD)
export GIT_DIR_VCS=git+https://github.com/karmab/kcli#$(git rev-parse HEAD):
envsubst < kcli.spec > $HOME/rpmbuild/SOURCES/kcli.spec

rpmbuild -bs $HOME/rpmbuild/SOURCES/kcli.spec
copr-cli build --nowait kcli $HOME/rpmbuild/SRPMS/*src.rpm
