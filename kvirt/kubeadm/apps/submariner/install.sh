set -euo pipefail
export DESTDIR=$PWD
curl -Ls https://get.submariner.io | bash
subctl deploy-broker --service-discovery
subctl join broker-info.subm --clusterid {{ cluster }} --disable-nat
