TMPDIR={{ tmpdir}}
CLUSTERDIR={{ clusterdir }}
CALICO_VERSION={{ 'projectcalico/calico'|github_version(calico_version) }}
cd $TMPDIR
curl -Lk https://github.com/projectcalico/calico/releases/download/$CALICO_VERSION/ocp.tgz | tar xvz --strip-components=1 -C $CLUSTERDIR/manifests
