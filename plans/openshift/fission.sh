oc new-project fission
helm install --namespace fission https://github.com/fission/fission/releases/download/v0.2.1/fission-core-v0.2.1.tgz
curl -Lo fission https://github.com/fission/fission/releases/download/v0.2.1/fission-cli-linux && chmod +x fission && sudo mv fission /usr/bin/
expose svc controller
expose svc router
