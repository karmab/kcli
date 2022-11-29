VERSION="$(date +%y.%m)"
sed -i "s/99.*/$VERSION/" kcli.spec
[ -d $HOME/.config ] || mkdir $HOME/.config
echo $COPR_BASE64 | base64 -d > $HOME/.config/copr
mkdir /tmp/results
podman run -v $PWD:/workdir -v /tmp/results:/tmp/results quay.io/karmab/rpkg --path /workdir srpm --outdir /tmp/results --spec /workdir/kcli.spec
copr-cli build --nowait kcli /tmp/results/*src.rpm
